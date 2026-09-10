"""Scientific contracts for the continuous MI pipeline."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from manuscript_mi_models import MixedMICE, ContinuousDesign, continuous_features, decision_curve


def example(n=100):
    rng = np.random.default_rng(3)
    x = pd.DataFrame({'edad': rng.uniform(20, 80, n), 'peso': rng.uniform(45, 100, n),
                      'sexo': rng.choice(['Male', 'Female'], n), 'fr_cance': rng.choice(['Yes', 'No'], n)})
    x.loc[::4, 'peso'] = np.nan
    x.loc[::5, 'fr_cance'] = None
    return x


def test_mice_preserves_observed_values_and_domains_and_is_stochastic():
    x = example()
    imputer = MixedMICE(seed=5, iterations=2, neighbors=3)
    filled = imputer.fit_transform(x)
    assert not filled.isna().any().any()
    for col in x:
        observed = x[col].notna()
        assert np.array_equal(x.loc[observed, col], filled.loc[observed, col])
        assert set(filled[col]).issubset(set(x[col].dropna()))
    alternate = MixedMICE(seed=7, iterations=2, neighbors=3).fit_transform(x)
    assert not filled.equals(alternate)


def test_validation_transform_does_not_fit_or_change_training_state(monkeypatch):
    x = example()
    model = MixedMICE(iterations=2); model.fit_transform(x.iloc[:80])
    columns = model.columns_.copy(); levels = model.levels_.copy()
    from sklearn.linear_model import LogisticRegression, BayesianRidge
    def forbidden(*args, **kwargs):
        raise AssertionError('Validation attempted to fit a conditional model')
    monkeypatch.setattr(LogisticRegression, 'fit', forbidden)
    monkeypatch.setattr(BayesianRidge, 'fit', forbidden)
    val = x.iloc[80:].copy(); val.loc[val.index[0], 'sexo'] = 'Unseen'
    a = model.transform(val); b = model.transform(val)
    pd.testing.assert_frame_equal(a, b)
    assert model.columns_ == columns and model.levels_ == levels
    assert not a.isna().any().any()


def test_continuous_features_do_not_bin_or_admit_outcomes():
    raw = pd.DataFrame({'edad': [49., 49.7, 50., 200.], 'ana_hemo': [12.1, 12.2, 12.3, 30.],
                        'sexo': ['Mujer']*4, 'var156': ['Sí']*4, 'evn_reci': ['Sí']*4})
    x, _ = continuous_features(raw)
    assert x.edad.iloc[:3].tolist() == [49., 49.7, 50.]
    assert x.ana_hemo.iloc[:3].tolist() == [12.1, 12.2, 12.3]
    assert pd.isna(x.edad.iloc[3]) and pd.isna(x.ana_hemo.iloc[3])
    assert not {'var156', 'evn_reci', 'female_under45'} & set(x)


def test_splines_and_tree_use_continuous_values_with_frozen_knots():
    x = example().dropna(); design = ContinuousDesign(True).fit(x)
    assert 'edad' in design.spline_
    matrix = design.transform(x)
    assert matrix.shape[1] == len(design.names_) == len(design.sources_)
    tree = ContinuousDesign(False).fit(x)
    np.testing.assert_array_equal(tree.transform(x)[:, 0], x.edad)
    before = design.spline_['edad'].bsplines_[0].t.copy()
    design.transform(x.assign(edad=119.))
    np.testing.assert_array_equal(before, design.spline_['edad'].bsplines_[0].t)


def test_dca_exact_net_benefit_and_comparators():
    r = decision_curve([1, 1, 0, 0], [.8, .2, .6, .1], [.5]).iloc[0]
    assert r.net_benefit == 0 and r.test_all_net_benefit == 0
    r = decision_curve([1, 1, 0, 0], [.8, .7, .2, .1], [.5]).iloc[0]
    assert r.net_benefit == .5 and r.net_tests_avoided_per_1000 == 500
    for t in [0, 1, -1]:
        with pytest.raises(ValueError):
            decision_curve([1, 0], [.8, .1], [t])
