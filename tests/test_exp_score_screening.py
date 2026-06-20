from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_score_screening import ClinicalScoreScreeningExperiment


def _build_mock_df() -> pd.DataFrame:
    rows = []
    for idx in range(60):
        if idx < 20:
            target = 'Buscada positivo'
            age = 78 + idx
            hemo = 10.5
            ddimer = 1.4
            sex = 'Male'
            cance = 'Sí'
            inmov = 'Sí'
            prior = 2.0
        elif idx < 40:
            target = 'Buscada negativo'
            age = 30 + idx
            hemo = 13.8
            ddimer = 0.2
            sex = 'Female'
            cance = 'No'
            inmov = 'No'
            prior = 0.0
        elif idx < 50:
            target = None
            age = 82 + idx
            hemo = 10.2
            ddimer = 1.6
            sex = 'Male'
            cance = 'Sí'
            inmov = 'Sí'
            prior = 1.0
        else:
            target = 'No buscada'
            age = 35 + idx
            hemo = 14.0
            ddimer = 0.3
            sex = 'Female'
            cance = 'No'
            inmov = 'No'
            prior = 0.0
        rows.append(
            {
                'id_pacie': idx,
                'ana_dura': target,
                'edad': age,
                'ana_hemo': hemo,
                'ddvalmcg': ddimer,
                'sexo': sex,
                'fr_cance': cance,
                'fr_inmov': inmov,
                'fr_tvp_p': prior,
            }
        )
    return pd.DataFrame(rows)


def test_run_builds_screening_candidates_export(tmp_path: Path) -> None:
    experiment = ClinicalScoreScreeningExperiment()
    config = {
        'score_target_column': 'ana_dura',
        'score_positive_label': 'Buscada positivo',
        'score_negative_label': 'Buscada negativo',
        'screening_labels': ['Missing', 'No buscada'],
        'score_max_samples': 40,
        'score_feature_strategy': 'compare',
        'score_max_feature_cardinality': 4,
        'score_numeric_bins': 4,
        'score_cv_splits': 4,
        'score_top_features': 5,
        'score_min_sensitivity': 0.90,
        'output_dir': str(tmp_path),
    }

    experiment.run(_build_mock_df(), config)

    latex_output = experiment.export_latex()
    assert 'Training ROC Performance Used for Screening Candidates' in latex_output
    assert 'Counts of Positive Screening Flags' in latex_output
    assert experiment.plotly_figure is not None

    export_path = tmp_path / 'clinical_risk_score_screening_candidates.csv'
    assert export_path.exists()
    export_df = pd.read_csv(export_path)
    assert {
        'id_pacie',
        'ana_dura',
        'automatic_integer_score',
        'association_guided_integer_score',
        'logistic_benchmark_probability',
        'xgboost_benchmark_probability',
        'logistic_benchmark_predicted_positive_at_rule_out_threshold',
        'xgboost_benchmark_predicted_positive_at_rule_out_threshold',
    }.issubset(export_df.columns)
    assert set(export_df['ana_dura']) == {'Missing', 'No buscada'}
    assert len(export_df) == 20
