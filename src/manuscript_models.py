"""Leakage-controlled estimators, nested validation, and operating-point metrics.

All supervised screening, category vocabularies, hyperparameter selection,
point construction, point-to-probability calibration, and threshold selection
are fitted exclusively using the current training partition. Outer-fold and
temporal outcomes never select the operating threshold. Dense one-hot matrices
preserve observed zeros for XGBoost; actual unknown source categories become
NaN across that source's encoded block.
"""
from __future__ import annotations

from dataclasses import dataclass
import warnings
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from scipy.stats import chi2_contingency
from sklearn import __version__ as sklearn_version
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve, brier_score_loss, log_loss
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

LASSO_GRID = [{"C": c} for c in (.01, .1, 1., 10.)]
XGB_GRID = [
    dict(n_estimators=80, max_depth=2, learning_rate=.03, subsample=.8, colsample_bytree=.8, reg_alpha=0., reg_lambda=1.),
    dict(n_estimators=80, max_depth=3, learning_rate=.08, subsample=.8, colsample_bytree=.8, reg_alpha=.1, reg_lambda=5.),
    dict(n_estimators=120, max_depth=2, learning_rate=.08, subsample=1., colsample_bytree=.9, reg_alpha=.5, reg_lambda=5.),
    dict(n_estimators=120, max_depth=3, learning_rate=.03, subsample=.9, colsample_bytree=1., reg_alpha=.1, reg_lambda=10.),
]


def split_indices(y: np.ndarray, requested: int, seed: int):
    """Yield deterministic stratified folds; fail rather than validate a one-class cohort."""
    counts = np.bincount(np.asarray(y, dtype=int), minlength=2)
    k = min(requested, int(counts.min()))
    if k < 2:
        raise ValueError("At least two observations in each class are required for CV.")
    return list(StratifiedKFold(k, shuffle=True, random_state=seed).split(np.zeros(len(y)), y))


def univariable_screen(X: pd.DataFrame, y: np.ndarray, p_limit: float = .1) -> pd.DataFrame:
    """Likelihood-ratio screening for categorical univariable logistic models.

    The contingency-table G statistic is exactly the likelihood-ratio statistic
    comparing a saturated categorical logistic predictor with intercept only.
    This avoids unstable coefficient estimates under separation; asymptotic
    chi-square p-values remain exploratory for sparse categories. Missingness is
    not converted into an observed clinical level by this function.
    """
    rows = []
    for col in X:
        valid = X[col].notna().to_numpy()
        table = pd.crosstab(X.loc[valid, col].astype(str).to_numpy(), np.asarray(y)[valid])
        p = 1.
        if table.shape[0] > 1 and table.shape[1] == 2:
            p = float(chi2_contingency(table, correction=False, lambda_="log-likelihood").pvalue)
        rows.append(dict(variable=col, p_value=p, selected=p < p_limit, observed_n=int(valid.sum())))
    return pd.DataFrame(rows)


class CategoryEncoder:
    """Training-only category vocabulary with explicit dense missing-value semantics."""
    def __init__(self, native_missing: bool = False, drop_first: bool = False):
        self.native_missing = native_missing
        self.drop_first = drop_first

    @staticmethod
    def _frame(X: pd.DataFrame) -> pd.DataFrame:
        return X.astype("string").fillna("__UNKNOWN__").astype(str)

    def fit(self, X: pd.DataFrame):
        """Learn observed category levels from this training set only."""
        self.columns_ = list(X.columns)
        self.encoder_ = OneHotEncoder(handle_unknown="ignore", sparse_output=False,
                                      drop="first" if self.drop_first else None, dtype=np.float64)
        self.encoder_.fit(self._frame(X))
        return self

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        """Encode observations; source missingness is NaN only for native tree models."""
        frame = self._frame(X[self.columns_])
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Found unknown categories")
            result = self.encoder_.transform(frame)
        if self.native_missing:
            start = 0
            for col, categories in zip(self.columns_, self.encoder_.categories_):
                width = len(categories) - int(self.drop_first)
                unknown = X[col].isna().to_numpy() | ~frame[col].isin(categories).to_numpy()
                result[unknown, start:start + width] = np.nan
                start += width
        return result

    def components(self) -> list[tuple[str, str]]:
        """Return lossless (source variable, category) identities for score documentation."""
        return [(col, str(level)) for col, levels in zip(self.columns_, self.encoder_.categories_)
                for level in levels[int(self.drop_first):]]


class LassoPointModel:
    """Univariable-screened L1 logistic model and signed integer simplification.

    Points preserve coefficient signs and are scaled by the smallest retained
    nonzero absolute coefficient. A nonnegative-slope logistic mapping of the
    actual point sum provides a separate score probability, fitted on training
    data only. This is not the full logistic model's probability.
    """
    def __init__(self, C: float = 1., seed: int = 42, p_limit: float = .1):
        self.C, self.seed, self.p_limit = C, seed, p_limit

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """Screen variables and fit L1 coefficients, point weights and score calibration."""
        if X.isna().any().any():
            raise ValueError("LassoPointModel requires the declared complete-case cohort.")
        self.screen_ = univariable_screen(X, y, self.p_limit)
        self.columns_ = self.screen_.loc[self.screen_.selected, "variable"].tolist()
        self.prevalence_ = float(np.mean(y))
        self.model_ = None
        self.points_ = pd.DataFrame(columns=["variable", "category", "coefficient", "points"])
        self.offset_, self.slope_ = float(logit(np.clip(self.prevalence_, 1e-8, 1-1e-8))), 0.
        if not self.columns_:
            return self
        self.encoder_ = CategoryEncoder(drop_first=True).fit(X[self.columns_])
        matrix = self.encoder_.transform(X[self.columns_])
        if not matrix.shape[1]:
            return self
        # No class weighting: preserve empirical prevalence for probability estimation.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning, message=".*penalty.*")
            l1_options = {"l1_ratio": 1.} if tuple(map(int, sklearn_version.split(".")[:2])) >= (1, 8) else {"penalty": "l1"}
            self.model_ = LogisticRegression(**l1_options, C=self.C, solver="liblinear",
                                              max_iter=4000, tol=1e-7, random_state=self.seed).fit(matrix, y)
        coefficients = self.model_.coef_[0]
        retained = np.abs(coefficients) > 1e-6
        self.weights_ = np.zeros_like(coefficients)
        if retained.any():
            scale = np.min(np.abs(coefficients[retained]))
            self.weights_[retained] = np.rint(coefficients[retained] / scale)
            self.points_ = pd.DataFrame([
                dict(variable=col, category=level, coefficient=float(coef), points=int(weight))
                for (col, level), coef, weight in zip(self.encoder_.components(), coefficients, self.weights_)
                if weight != 0])
        score = matrix @ self.weights_
        # Standardize only within the training set to make extreme point scales numerically safe.
        self.score_center_ = float(np.mean(score))
        self.score_scale_ = max(float(np.std(score)), 1.)
        z = (score - self.score_center_) / self.score_scale_
        def objective(beta):
            eta = beta[0] + beta[1] * z
            loss = np.mean(np.logaddexp(0, eta) - y * eta)
            residual = expit(eta) - y
            return loss, np.array([residual.mean(), np.mean(residual*z)])
        fit = minimize(objective, [self.offset_, 0.], jac=True, method="L-BFGS-B", bounds=[(None,None),(0,None)])
        if not fit.success:
            raise RuntimeError(f"Point calibration failed: {fit.message}")
        self.slope_ = float(fit.x[1] / self.score_scale_)
        self.offset_ = float(fit.x[0] - self.slope_ * self.score_center_)
        return self

    def point_scores(self, X: pd.DataFrame) -> np.ndarray:
        """Sum the signed points; an intercept-only fallback has zero points."""
        if self.model_ is None:
            return np.zeros(len(X))
        return self.encoder_.transform(X[self.columns_]) @ self.weights_

    def probabilities(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Return distinct logistic and calibrated integer-score probabilities."""
        logistic = (np.full(len(X), self.prevalence_) if self.model_ is None else
                    self.model_.predict_proba(self.encoder_.transform(X[self.columns_]))[:,1])
        return {"Logistic LASSO": logistic,
                "Automatic integer score": expit(self.offset_ + self.slope_ * self.point_scores(X))}

    def integer_cutoff(self, probability_threshold: float) -> float:
        """Translate a fixed calibrated-probability threshold to a signed point cutoff."""
        if self.slope_ <= 1e-12:
            return -np.inf if expit(self.offset_) >= probability_threshold else np.inf
        if probability_threshold <= 0:
            return -np.inf
        if probability_threshold >= 1:
            return np.inf
        return float(np.ceil((logit(probability_threshold) - self.offset_) / self.slope_ - 1e-10))


class NativeXGBModel:
    """Tuned tree benchmark preserving observed zeros and true missing blocks."""
    def __init__(self, seed: int = 42, threads: int = 2, **params):
        self.params, self.seed, self.threads = params, seed, threads

    def fit(self, X: pd.DataFrame, y: np.ndarray):
        """Fit a training vocabulary and a histogram-based binary XGBoost model."""
        self.encoder_ = CategoryEncoder(native_missing=True).fit(X)
        self.model_ = XGBClassifier(**self.params, objective="binary:logistic", eval_metric="logloss",
                                    tree_method="hist", random_state=self.seed, n_jobs=self.threads,
                                    missing=np.nan).fit(self.encoder_.transform(X), y)
        return self

    def probabilities(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Predict probability of the positive registered outcome."""
        return {"XGBoost": self.model_.predict_proba(self.encoder_.transform(X))[:,1]}


def select_threshold(y: np.ndarray, probability: np.ndarray, sensitivity: float = .9) -> float:
    """Select the most specific training-only ROC point satisfying target sensitivity."""
    if not np.isfinite(probability).all():
        raise ValueError("Threshold selection requires finite predictions.")
    fpr, tpr, threshold = roc_curve(y, probability, drop_intermediate=False)
    eligible = np.flatnonzero((tpr >= sensitivity) & np.isfinite(threshold))
    if not len(eligible):
        raise ValueError("No finite threshold meets the sensitivity target.")
    best = eligible[np.argmin(fpr[eligible])]
    return float(threshold[best])


@dataclass
class TunedFit:
    """A final training fit with inner-CV predictions, thresholds and a search audit."""
    estimator: object
    thresholds: dict[str, float]
    inner_predictions: dict[str, np.ndarray]
    search: pd.DataFrame
    parameters: dict
    inner_splits: int


def fit_tuned(X: pd.DataFrame, y: np.ndarray, kind: str, seed: int = 42,
              inner_splits: int = 5, min_sensitivity: float = .9,
              threads: int = 2, compact: bool = False) -> TunedFit:
    """Search on inner folds and refit without using any external validation labels.

    C is selected using logistic AUC; the same selected C supplies the integer
    score. XGBoost parameters are selected by AUC. Ties favor the first declared
    (simpler) candidate. The selected inner predictions set operating thresholds.
    """
    grid = LASSO_GRID if kind == "lasso" else XGB_GRID
    if compact:
        grid = grid[:2]
    splits = split_indices(y, inner_splits, seed)
    rows, predictions = [], []
    def new(params):
        return LassoPointModel(seed=seed, **params) if kind == "lasso" else NativeXGBModel(seed=seed, threads=threads, **params)
    for candidate, params in enumerate(grid):
        values = {}
        for train, val in splits:
            model = new(params).fit(X.iloc[train], y[train])
            for name, p in model.probabilities(X.iloc[val]).items():
                values.setdefault(name, np.zeros(len(y)))[val] = p
        name = "Logistic LASSO" if kind == "lasso" else "XGBoost"
        auc = float(roc_auc_score(y, values[name]))
        rows.append(dict(candidate=candidate, auc=auc, **params))
        predictions.append(values)
    best = int(np.argmax([r["auc"] for r in rows]))
    values = predictions[best]
    thresholds = {name: select_threshold(y, p, min_sensitivity) for name,p in values.items()}
    return TunedFit(new(grid[best]).fit(X,y), thresholds, values,
                    pd.DataFrame(rows).assign(selected=lambda d:d.candidate.eq(best)), grid[best], len(splits))


def nested_predictions(X: pd.DataFrame, y: np.ndarray, ids: np.ndarray, kind: str,
                       seed: int = 42, outer_splits: int = 5, inner_splits: int = 5,
                       min_sensitivity: float = .9, threads: int = 2, compact: bool = False,
                       progress=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate exactly one held-out prediction per eligible patient and model."""
    rows, searches = [], []
    for fold,(train,val) in enumerate(split_indices(y,outer_splits,seed),1):
        if progress:
            progress(f"{kind}: outer fold {fold}/{outer_splits}")
        fit = fit_tuned(X.iloc[train],y[train],kind,seed+fold,inner_splits,min_sensitivity,threads,compact)
        searches.append(fit.search.assign(outer_fold=fold,inner_splits=fit.inner_splits))
        for name,p in fit.estimator.probabilities(X.iloc[val]).items():
            threshold = fit.thresholds[name]
            raw_score = fit.estimator.point_scores(X.iloc[val]) if name == "Automatic integer score" else p
            cutoff = fit.estimator.integer_cutoff(threshold) if name == "Automatic integer score" else np.nan
            rows.append(pd.DataFrame(dict(id_pacie=ids[val],fold=fold,y_true=y[val],model=name,
                                          probability=p,raw_score=raw_score,threshold=threshold,
                                          integer_cutoff=cutoff,predicted_positive=p>=threshold)))
    return pd.concat(rows,ignore_index=True),pd.concat(searches,ignore_index=True)


def ratio(a: float, b: float) -> float:
    """Return NaN for undefined conditional probabilities instead of false zeroes."""
    return float(a/b) if b else float("nan")


def wilson(a: int, b: int) -> tuple[float,float]:
    """Two-sided 95% Wilson interval for a binomial proportion."""
    if b == 0:
        return np.nan,np.nan
    z=1.959963984540054; p=a/b; den=1+z*z/b
    center=(p+z*z/(2*b))/den; radius=z*np.sqrt(p*(1-p)/b+z*z/(4*b*b))/den
    return center-radius,center+radius


def metric_row(frame: pd.DataFrame, bootstrap: int = 200, seed: int = 42) -> dict:
    """Derive every operating metric from one set of held-out binary predictions.

    AUC intervals use a stratified patient bootstrap of fixed predictions. They
    are conditional descriptive intervals, not a resampling of model fitting.
    Pooled calibrated probabilities permit comparison across fold-specific point
    scales; mean within-fold raw-score AUC is also provided for integer scores.
    """
    y=frame.y_true.to_numpy(dtype=int); pred=frame.predicted_positive.to_numpy(dtype=bool)
    p=frame.probability.to_numpy(dtype=float)
    tp=int(np.sum((y==1)&pred)); fn=int(np.sum((y==1)&~pred))
    tn=int(np.sum((y==0)&~pred)); fp=int(np.sum((y==0)&pred)); n=len(y)
    both=len(np.unique(y))==2
    auc=float(roc_auc_score(y,p)) if both else np.nan
    row=dict(n=n,positive_n=int(y.sum()),tp=tp,fp=fp,tn=tn,fn=fn,auc=auc,
             brier=float(brier_score_loss(y,p)),log_loss=float(log_loss(y,p,labels=[0,1])),
             tests_avoided_per_1000=1000*ratio(tn+fn,n),missed_positive_per_1000=1000*ratio(fn,n))
    for name,a,b in [('sensitivity',tp,tp+fn),('specificity',tn,tn+fp),('ppv',tp,tp+fp),('npv',tn,tn+fn)]:
        row[name]=ratio(a,b);row[name+'_lower'],row[name+'_upper']=wilson(a,b)
    row['false_negative_rate']=ratio(fn,tp+fn);row['false_positive_rate']=ratio(fp,tn+fp)
    row['lr_positive']=ratio(row['sensitivity'],row['false_positive_rate'])
    row['lr_negative']=ratio(row['false_negative_rate'],row['specificity'])
    boot=[]
    if both and bootstrap:
        rng=np.random.default_rng(seed);pos=np.flatnonzero(y);neg=np.flatnonzero(y==0)
        for _ in range(bootstrap):
            ix=np.r_[rng.choice(pos,len(pos)),rng.choice(neg,len(neg))]
            boot.append(roc_auc_score(y[ix],p[ix]))
    row['auc_lower'],row['auc_upper']=np.quantile(boot,[.025,.975]) if boot else (np.nan,np.nan)
    within=[roc_auc_score(g.y_true,g.raw_score) for _,g in frame.groupby('fold') if g.y_true.nunique()==2]
    row['mean_fold_raw_auc']=float(np.mean(within)) if within else np.nan
    return row


def calibration_bins(frame: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Fixed-width held-out calibration bins, with counts and both error summaries."""
    d=frame.copy();d['bin']=np.minimum((d.probability*bins).astype(int),bins-1)
    result=d.groupby('bin',observed=True).agg(n=('y_true','size'),predicted=('probability','mean'),observed=('y_true','mean')).reset_index()
    result['absolute_error']=(result.predicted-result.observed).abs()
    return result
