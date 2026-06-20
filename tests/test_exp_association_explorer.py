from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_association_explorer import AssociationExplorerExperiment


def _build_mock_df() -> pd.DataFrame:
    rows = []
    for idx in range(18):
        positive = idx < 9
        rows.append(
            {
                'id_pacie': idx,
                'ana_dura': 'Buscada positivo' if positive else 'Buscada negativo',
                'sexo': 'Mujer' if idx % 2 == 0 else 'Hombre',
                'fr_cance': 'Sí' if positive else 'No',
                'fr_inmov': 'Sí' if idx % 3 == 0 else 'No',
                'sin_tvp_': 'EP' if positive else 'TVP',
                'event_date': f'2026-06-{idx + 1:02d}',
            }
        )
    return pd.DataFrame(rows)


def test_run_builds_filtered_association_rules_and_exports(tmp_path: Path) -> None:
    experiment = AssociationExplorerExperiment()
    config = {
        'data': 'mock.parquet',
        'checkpoint_dir': str(tmp_path / 'checkpoints'),
        'association_rules_max_samples': 18,
        'association_rules_min_support': 0.2,
        'association_rules_min_confidence': 0.6,
        'association_rules_min_lift': 1.0,
        'association_rules_max_feature_cardinality': 4,
        'association_rules_max_features': 6,
        'association_rules_max_rule_size': 3,
        'association_rules_top_k': 5,
        'association_rules_sort_metric': 'leverage',
        'association_rules_filter_column': 'ana_dura',
        'association_rules_filter_side': 'either',
        'output_dir': str(tmp_path),
        'resume': False,
    }

    experiment.run(_build_mock_df(), config)

    latex_output = experiment.export_latex()
    assert 'Open Association Rules Ranked by Configured Metric' in latex_output
    assert 'ana_dura' in latex_output
    assert experiment.plotly_figure is not None

    rules_path = tmp_path / 'association_explorer_top_rules.csv'
    assert rules_path.exists()
    rules_df = pd.read_csv(rules_path)
    assert {'antecedents', 'consequents', 'support', 'confidence', 'lift', 'leverage'}.issubset(rules_df.columns)
    assert len(rules_df) <= 5
    assert rules_df['antecedents'].str.contains('ana_dura:').any() or rules_df['consequents'].str.contains('ana_dura:').any()

    checkpoint_dirs = list((tmp_path / 'checkpoints').glob('association_explorer_*'))
    assert len(checkpoint_dirs) == 1
    checkpoint_dir = checkpoint_dirs[0]
    assert (checkpoint_dir / '04_association_rules.parquet').exists()
