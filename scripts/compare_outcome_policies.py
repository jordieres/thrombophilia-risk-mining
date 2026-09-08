"""Compare completed explicit-results and routine-panel aggregate evidence.

This is a descriptive contrast of different outcome definitions and populations,
not an estimate of a treatment effect or a paired model-improvement test. It
reads aggregate CSVs only. Composite and JAK2 rows must reproduce exactly because
the changed interpretation does not apply to either outcome.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from manuscript_reporting import table


def compare(previous: Path, current: Path) -> Path:
    """Write a source-hashed comparison into the current completed run directory."""
    manifests = [json.loads((p / 'run_manifest.json').read_text()) for p in (previous, current)]
    if any(m.get('status') != 'complete' for m in manifests):
        raise ValueError('Both numerical runs must be complete.')
    if manifests[0]['config'].get('outcome_policy', 'explicit-results') != 'explicit-results':
        raise ValueError('Previous run must use explicit results.')
    if manifests[1]['config'].get('outcome_policy') != 'routine-panel':
        raise ValueError('Current run must use the routine-panel interpretation.')
    if manifests[0]['data_sha256'] != manifests[1]['data_sha256']:
        raise ValueError('Source registry hashes differ.')
    settings = [{k: v for k, v in m['config'].items() if k != 'outcome_policy'} for m in manifests]
    if settings[0] != settings[1]:
        raise ValueError('Modelling settings differ beyond the outcome policy.')
    keys = ['outcome', 'label', 'analysis', 'validation', 'model']
    values = ['n', 'positive_n', 'auc', 'sensitivity', 'specificity', 'npv', 'tp', 'fp', 'tn', 'fn']
    old, new = [pd.read_csv(p / 'all_model_metrics.csv') for p in (previous, current)]
    for outcome in ['ana_dura', 'andujak2']:
        a = old.loc[old.outcome.eq(outcome)].sort_values(keys).reset_index(drop=True)
        b = new.loc[new.outcome.eq(outcome)].sort_values(keys).reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b, check_exact=True)
    merged = old[keys + values].merge(new[keys + values], on=keys,
                                    suffixes=('_explicit', '_routine'), validate='one_to_one')
    if len(merged) != len(old) or len(merged) != len(new):
        raise ValueError('Model/validation row sets differ.')
    merged.to_csv(current / 'outcome_policy_comparison.csv', index=False)
    primary = merged.query("analysis == 'primary_complete_case' and validation == 'nested_cv' and model == 'XGBoost'")
    display = primary[['label', 'n_explicit', 'n_routine', 'positive_n_explicit', 'positive_n_routine', 'auc_explicit', 'auc_routine']]
    sources = {}
    for name, directory in [('explicit_results', previous), ('routine_panel', current)]:
        sources[name] = {file: hashlib.sha256((directory / file).read_bytes()).hexdigest()
                         for file in ['all_model_metrics.csv', 'model_cohort_flow.csv', 'supplement_outcome_denominators.csv']}
    (current / 'outcome_policy_comparison_provenance.json').write_text(json.dumps({
        'source_data_sha256': manifests[1]['data_sha256'],
        'run_signatures': [m['signature'] for m in manifests], 'sources': sources,
        'unchanged_composite_and_jak2_metrics': True,
        'comparison_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    (current / 'outcome_policy_comparison.md').write_text(
        '# Effect of the investigator-confirmed outcome interpretation\n\n'
        'The principal analysis uses the routine-panel policy confirmed on 8 September 2026. '
        'The 7 September explicit-results run remains an alternative analysis. Both runs use '
        'the same source registry and modelling settings. Composite and JAK2 aggregate model '
        'metrics were verified to be exactly unchanged across every analysis and validation.\n\n'
        'For the six routine subtypes, missing outcomes become negative only among globally '
        'tested patients. This changes eligibility, class prevalence, complete-case populations '
        'and fitted models. Differences are descriptive and must not be presented as an isolated '
        'improvement in algorithm performance. Missing predictors retain their separate handling.\n\n'
        'The total eligible positive count is unchanged for each routine subtype. The candidate '
        'availability rule is reapplied to the expanded development population and can retain '
        'a different candidate set. Complete-case '
        'membership can therefore change in both directions, and fewer positive cases may '
        'remain in the primary comparison despite the larger eligible population. This is '
        'documented in each run’s model_cohort_flow.csv and candidate_availability.csv.\n\n'
        'The table shows primary complete-case XGBoost nested-validation results. The CSV gives '
        'all models and both nested and temporal validation; suffixes identify the outcome policy.\n\n'
        + table(display, digits=4) + '\n\n'
        'The associated provenance JSON records both run signatures and hashes of the aggregate '
        'source tables. No patient records are needed to reproduce this comparison.\n')
    return current / 'outcome_policy_comparison.md'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous', type=Path, default=Path('out/manuscript_reanalysis_2026-09-07'))
    parser.add_argument('--current', type=Path, default=Path('out/manuscript_reanalysis_2026-09-08'))
    args = parser.parse_args()
    print(compare(args.previous, args.current))
