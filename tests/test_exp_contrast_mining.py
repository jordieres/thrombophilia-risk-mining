from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_contrast_mining import ContrastPatternMiningExperiment


def _build_mock_df() -> pd.DataFrame:
    rows = []
    for idx in range(12):
        rows.append(
            {
                'id_pacie': idx,
                'ana_dura': 'Buscada positivo' if idx < 6 else 'Buscada negativo',
                'alt_target': 'Homocigoto' if idx < 6 else ('Heterocigoto' if idx < 10 else 'Missing'),
                'sexo': 'Female' if idx % 2 == 0 else 'Male',
                'fr_history': 'Yes' if idx < 6 else 'No',
                'lab_band': 'High' if idx < 6 else 'Low',
                'event_date': f'2026-06-{idx + 1:02d}',
            }
        )
    return pd.DataFrame(rows)


def test_prepare_feature_frame_excludes_high_cardinality_columns() -> None:
    experiment = ContrastPatternMiningExperiment()
    prepared_df, profile = experiment._prepare_feature_frame(
        _build_mock_df(),
        target_col='alt_target',
        max_feature_cardinality=3,
        max_features=10,
    )

    assert 'event_date' not in prepared_df.columns
    assert 'alt_target' in prepared_df.columns
    assert 'sexo' in prepared_df.columns
    assert profile['selected_feature_count'] == 4


def test_run_creates_checkpointed_rules_and_outputs(tmp_path: Path) -> None:
    experiment = ContrastPatternMiningExperiment()
    df = _build_mock_df()
    config = {
        'data': 'mock.parquet',
        'checkpoint_dir': str(tmp_path / 'checkpoints'),
        'contrast_max_samples': 12,
        'contrast_min_support': 0.2,
        'contrast_min_confidence': 0.6,
        'contrast_max_feature_cardinality': 3,
        'contrast_max_features': 4,
        'contrast_max_rule_size': 2,
        'contrast_top_k_per_outcome': 3,
        'contrast_workers': 2,
        'contrast_target_column': 'alt_target',
        'contrast_target_valid_labels': ['Homocigoto', 'Heterocigoto'],
        'resume': False,
    }

    experiment.run(df, config)

    checkpoint_dirs = list((tmp_path / 'checkpoints').glob('contrast_pattern_mining_*'))
    assert len(checkpoint_dirs) == 1

    checkpoint_dir = checkpoint_dirs[0]
    assert (checkpoint_dir / '01_prepared_sample.parquet').exists()
    assert (checkpoint_dir / '02_encoded_transactions.parquet').exists()
    assert (checkpoint_dir / '03_frequent_itemsets.parquet').exists()
    assert (checkpoint_dir / '04_target_rules.parquet').exists()
    assert 'Homocigoto' in experiment.export_latex()
    assert experiment.plotly_figure is not None

    resume_experiment = ContrastPatternMiningExperiment()
    resume_config = dict(config)
    resume_config['resume'] = True
    resume_experiment.run(df, resume_config)
    assert resume_experiment.plotly_figure is not None
