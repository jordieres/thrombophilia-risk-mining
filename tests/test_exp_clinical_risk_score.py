from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_clinical_risk_score import ClinicalRiskScoreExperiment


def _build_mock_df() -> pd.DataFrame:
    rows = []
    for idx in range(40):
        positive = idx < 20
        rows.append(
            {
                'id_pacie': idx,
                'ana_dura': 'Buscada positivo' if positive else 'Buscada negativo',
                'edad': 72 + idx if positive else 38 + idx,
                'ana_hemo': 10.8 if positive else 13.4,
                'ddvalmcg': 1.4 if positive else 0.3,
                'sexo': 'Male' if positive else 'Female',
                'fr_cance': 'Sí' if positive else 'No',
                'fr_inmov': 'Sí' if positive else 'No',
                'fr_tvp_p': 2.0 if positive else 0.0,
                'fr_history': 'Yes' if positive else 'No',
                'event_date': f'2026-06-{(idx % 28) + 1:02d}',
            }
        )
    return pd.DataFrame(rows)


def test_run_builds_clinical_integer_score_outputs(tmp_path: Path) -> None:
    experiment = ClinicalRiskScoreExperiment()
    config = {
        'score_target_column': 'ana_dura',
        'score_positive_label': 'Buscada positivo',
        'score_negative_label': 'Buscada negativo',
        'score_max_samples': 40,
        'score_feature_strategy': 'compare',
        'score_max_feature_cardinality': 4,
        'score_numeric_bins': 4,
        'score_cv_splits': 4,
        'score_benchmark_model': 'logistic',
        'score_top_features': 5,
        'score_min_sensitivity': 0.90,
        'score_xgboost_estimators': 10,
        'output_dir': str(tmp_path),
    }

    experiment.run(_build_mock_df(), config)

    latex_output = experiment.export_latex()
    assert 'Association-Guided Integer Score' in latex_output
    assert 'Automatic Integer Score' in latex_output
    assert 'Threshold_Method' in latex_output
    assert experiment.plotly_figure is not None

    export_path = tmp_path / 'clinical_risk_score_per_patient.csv'
    assert export_path.exists()
    export_df = pd.read_csv(export_path)
    assert {
        'id_pacie',
        'ana_dura',
        'automatic_integer_score',
        'association_guided_integer_score',
        'association_guided_threshold_for_min_sensitivity',
    }.issubset(export_df.columns)
    assert len(export_df) == 40
