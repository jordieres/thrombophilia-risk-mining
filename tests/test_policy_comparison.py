"""Ensure policy comparisons preserve provenance and reject changed controls."""
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

spec = importlib.util.spec_from_file_location('policy_comparison', Path(__file__).resolve().parents[1] / 'scripts' / 'compare_outcome_policies.py')
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)


def fixture_runs(tmp_path):
    previous, current = tmp_path / 'previous', tmp_path / 'current'
    for directory, policy in [(previous, 'explicit-results'), (current, 'routine-panel')]:
        directory.mkdir()
        (directory / 'run_manifest.json').write_text(json.dumps({
            'status': 'complete', 'data_sha256': 'same-registry', 'signature': policy,
            'config': {'outcome_policy': policy, 'seed': 42},
        }))
        rows = []
        for outcome in ['ana_dura', 'andujak2', 'var156']:
            rows.append(dict(outcome=outcome, label=outcome, analysis='primary_complete_case',
                validation='nested_cv', model='XGBoost', n=100, positive_n=20,
                auc=.7, sensitivity=.9, specificity=.5, npv=.95, tp=18, fp=40, tn=40, fn=2))
        pd.DataFrame(rows).to_csv(directory / 'all_model_metrics.csv', index=False)
        for name in ['model_cohort_flow.csv', 'supplement_outcome_denominators.csv']:
            (directory / name).write_text('outcome,n\nana_dura,100\n')
    return previous, current


def test_comparison_exports_only_aggregate_evidence(tmp_path):
    previous, current = fixture_runs(tmp_path)
    result = comparison.compare(previous, current)
    assert result.is_file()
    provenance = json.loads((current / 'outcome_policy_comparison_provenance.json').read_text())
    assert provenance['unchanged_composite_and_jak2_metrics'] is True
    assert len(provenance['sources']['routine_panel']['all_model_metrics.csv']) == 64
    assert len(pd.read_csv(current / 'outcome_policy_comparison.csv')) == 3


def test_comparison_rejects_changed_jak2_metrics(tmp_path):
    previous, current = fixture_runs(tmp_path)
    metrics = pd.read_csv(current / 'all_model_metrics.csv')
    metrics.loc[metrics.outcome.eq('andujak2'), 'auc'] = .8
    metrics.to_csv(current / 'all_model_metrics.csv', index=False)
    with pytest.raises(AssertionError):
        comparison.compare(previous, current)
    assert not (current / 'outcome_policy_comparison.csv').exists()
