"""Mixed-type chained imputation and continuous prediction models.

Numeric: Bayesian ridge parameter draws plus predictive mean matching (PMM).
Categorical: bootstrap ridge multinomial logistic fits plus probability draws.
Imputation uses predictors only, in training and at deployment. Prediction
pooling is an ensemble, not Rubin pooling of selected LASSO coefficients.
"""
from __future__ import annotations
import warnings
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.linear_model import BayesianRidge, LogisticRegression
from sklearn.preprocessing import OneHotEncoder, SplineTransformer, StandardScaler
from sklearn.exceptions import ConvergenceWarning
from xgboost import XGBClassifier
from manuscript_cohort import NUMERIC, prepare_features


def continuous_features(raw):
    """Reuse pretest allowlist and quality bounds; retain numeric values."""
    x, audit = prepare_features(raw)
    x = x.drop(columns=['female_under45'], errors='ignore')
    for col, (lo, hi, *_) in NUMERIC.items():
        if col in raw:
            v = pd.to_numeric(raw[col], errors='coerce')
            x[col] = v.where(v.between(lo, hi)).astype(float)
            audit.loc[audit.variable.eq(col), 'rule'] = f'Continuous; valid [{lo}, {hi}]; invalid -> missing'
    return x, audit


class MixedMICE:
    """One FCS chain; frozen conditional models transform new patients.

    Conditional predictor selection uses training-only absolute correlations
    between initial encodings, never outcome significance. Categorical inputs
    enter conditional regressions as dummies. All observed values are preserved.
    Constant/unavailable training variables are excluded, never patients.
    """
    def __init__(self, seed=42, iterations=5, neighbors=12, donors=5):
        self.seed, self.iterations, self.neighbors, self.donors = seed, iterations, neighbors, donors

    def encode(self, x):
        a = np.full((len(x), len(self.columns_)), np.nan)
        for j, col in enumerate(self.columns_):
            if col in self.levels_:
                a[:, j] = pd.Categorical(x[col], categories=self.levels_[col]).codes.astype(float)
                a[a[:, j] < 0, j] = np.nan
            else:
                a[:, j] = x[col].to_numpy(dtype=float, na_value=np.nan)
        return a

    def initial(self, a, rng):
        a = a.copy()
        for j, values in enumerate(self.observed_):
            missing = np.isnan(a[:, j])
            a[missing, j] = rng.choice(values, missing.sum())
        return a

    def design(self, a, predictors):
        blocks = []
        for j in predictors:
            col = self.columns_[j]
            if col in self.levels_:
                blocks.append((a[:, j, None] == np.arange(1, len(self.levels_[col]))).astype(float))
            else:
                blocks.append(((a[:, j]-self.center_[j])/self.scale_[j])[:, None])
        return np.column_stack(blocks) if blocks else np.ones((len(a), 1))

    def draw(self, model, design, rng):
        kind, fit, aux = model
        if kind == 'categorical':
            p = fit.predict_proba(design)
            ix = (rng.random(len(p))[:, None] > p.cumsum(axis=1)).sum(axis=1).clip(max=p.shape[1]-1)
            return fit.classes_[ix]
        if kind == 'constant':
            return np.full(len(design), aux)
        coef, donor_predictions, donor_values = aux
        predicted = design @ coef + fit.intercept_
        _, ix = cKDTree(donor_predictions[:, None]).query(predicted[:, None], k=min(self.donors, len(donor_values)))
        if ix.ndim == 1:
            return donor_values[ix]
        return donor_values[ix[np.arange(len(ix)), rng.integers(ix.shape[1], size=len(ix))]]

    def fit_transform(self, x):
        self.columns_ = [c for c in x if x[c].nunique() > 1]
        if not self.columns_:
            raise ValueError('No varying observed training predictors')
        self.levels_ = {c: sorted(x[c].dropna().astype(str).unique()) for c in self.columns_ if c not in NUMERIC}
        original = self.encode(x)
        self.observed_ = [original[np.isfinite(original[:, j]), j] for j in range(original.shape[1])]
        self.center_ = np.array([v.mean() for v in self.observed_])
        self.scale_ = np.array([max(v.std(), 1e-8) for v in self.observed_])
        rng = np.random.default_rng(self.seed)
        a = self.initial(original, rng)
        corr = np.nan_to_num(np.abs(np.corrcoef(a, rowvar=False))) if a.shape[1] > 1 else np.ones((1, 1))
        self.predictors_ = {j: [int(k) for k in np.argsort(-corr[j]) if k != j][:self.neighbors] for j in range(a.shape[1])}
        self.sequence_, self.diagnostics_ = [], []
        for iteration in range(self.iterations):
            for j, col in enumerate(self.columns_):
                missing = np.isnan(original[:, j]); observed = ~missing
                d = self.design(a, self.predictors_[j]); target = original[observed, j]
                if col in self.levels_:
                    boot = rng.integers(len(target), size=len(target))
                    if len(np.unique(target[boot])) == 1:
                        model = ('constant', None, target[boot][0])
                    else:
                        fit = LogisticRegression(C=1., solver='lbfgs', max_iter=500, random_state=self.seed)
                        with warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter('always', ConvergenceWarning)
                            fit.fit(d[observed][boot], target[boot])
                        if any(issubclass(w.category, ConvergenceWarning) for w in caught):
                            raise RuntimeError(f'Categorical imputation failed to converge: {col}')
                        model = ('categorical', fit, None)
                else:
                    fit = BayesianRidge().fit(d[observed], target)
                    coef = rng.multivariate_normal(fit.coef_, fit.sigma_, check_valid='raise')
                    model = ('numeric', fit, (coef, fit.predict(d[observed]), target.copy()))
                if missing.any():
                    a[missing, j] = self.draw(model, d[missing], rng)
                    self.diagnostics_.append(dict(iteration=iteration+1, variable=col,
                        missing_n=int(missing.sum()), imputed_mean=float(a[missing, j].mean()),
                        imputed_sd=float(a[missing, j].std())))
                self.sequence_.append((j, model))
        return self.decode(a, x.index)

    def decode(self, a, index):
        result = pd.DataFrame(index=index)
        for j, col in enumerate(self.columns_):
            result[col] = np.array(self.levels_[col])[a[:, j].astype(int)] if col in self.levels_ else a[:, j]
        return result

    def transform(self, x):
        rng = np.random.default_rng(self.seed + 1000003)
        original = self.encode(x); a = self.initial(original, rng)
        for j, model in self.sequence_:
            missing = np.isnan(original[:, j])
            if missing.any():
                d = self.design(a, self.predictors_[j])
                a[missing, j] = self.draw(model, d[missing], rng)
        return self.decode(a, x.index)


class ContinuousDesign:
    """Training-only spline knots, dummy levels and scaling for L1 logistic."""
    def __init__(self, splines):
        self.splines = splines

    def fit(self, x):
        self.numeric_ = [c for c in x if c in NUMERIC]
        self.categorical_ = [c for c in x if c not in NUMERIC]
        self.enc_ = None
        if self.categorical_:
            self.enc_ = OneHotEncoder(handle_unknown='ignore', sparse_output=False, drop='first').fit(x[self.categorical_])
        self.spline_ = {}; self.names_, self.sources_ = [], []
        for c in self.numeric_:
            knots = np.unique(np.quantile(x[c], [.05, .35, .65, .95]))
            if self.splines and len(knots) >= 3:
                self.spline_[c] = SplineTransformer(degree=3, knots=knots[:, None], include_bias=False,
                    extrapolation='linear').fit(x[[c]])
                width = self.spline_[c].n_features_out_
            else:
                width = 1
            self.names_ += [f'{c}:spline_{k}' if c in self.spline_ else c for k in range(width)]
            self.sources_ += [c]*width
        if self.enc_ is not None:
            self.names_ += list(self.enc_.get_feature_names_out(self.categorical_))
            self.sources_ += [c for c, levels in zip(self.categorical_, self.enc_.categories_) for _ in levels[1:]]
        self.scaler_ = StandardScaler().fit(self.raw(x)) if self.splines else None
        return self

    def raw(self, x):
        blocks = [self.spline_[c].transform(x[[c]]) if c in self.spline_ else x[[c]].to_numpy(dtype=float) for c in self.numeric_]
        if self.enc_ is not None:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', message='Found unknown categories')
                blocks.append(self.enc_.transform(x[self.categorical_]))
        return np.column_stack(blocks)

    def transform(self, x):
        a = self.raw(x)
        return self.scaler_.transform(a) if self.scaler_ is not None else a


def fit_classifier(kind, params, x, y, seed, threads=1):
    """No significance screening or class weighting; nonconvergence is an error."""
    if kind == 'lasso':
        from sklearn import __version__
        options = {'l1_ratio': 1.} if tuple(map(int, __version__.split('.')[:2])) >= (1, 8) else {'penalty': 'l1'}
        model = LogisticRegression(**options, solver='liblinear', max_iter=5000, tol=1e-6,
                                   random_state=seed, **params)
    else:
        model = XGBClassifier(**params, objective='binary:logistic', eval_metric='logloss',
                              tree_method='hist', random_state=seed, n_jobs=threads)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always', ConvergenceWarning)
        model.fit(x, y)
    if any(issubclass(w.category, ConvergenceWarning) for w in caught):
        raise RuntimeError(f'{kind} failed to converge')
    return model


def decision_curve(y, probability, thresholds):
    """Net benefit of testing at p>=threshold vs testing all or testing none."""
    y = np.asarray(y, dtype=int); probability = np.asarray(probability, dtype=float)
    thresholds = np.asarray(thresholds, dtype=float)
    if not len(y) or len(y) != len(probability) or not np.isfinite(probability).all() or not np.isin(y, [0, 1]).all() or not ((probability >= 0) & (probability <= 1)).all():
        raise ValueError('Invalid outcomes/probabilities')
    if not ((thresholds > 0) & (thresholds < 1)).all():
        raise ValueError('Decision thresholds must be strictly between zero and one')
    rows = []
    for t in thresholds:
        decision = probability >= t; odds = t/(1-t)
        tp = int((decision & (y == 1)).sum()); fp = int((decision & (y == 0)).sum())
        nb = (tp-fp*odds)/len(y); all_nb = y.mean() - (1-y.mean())*odds
        rows.append(dict(threshold=t, n=len(y), tp=tp, fp=fp, net_benefit=nb,
            test_all_net_benefit=all_nb, test_none_net_benefit=0.,
            net_tests_avoided_per_1000=(nb-all_nb)/odds*1000))
    return pd.DataFrame(rows)
