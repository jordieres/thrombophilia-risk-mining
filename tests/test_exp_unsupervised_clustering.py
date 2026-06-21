from __future__ import annotations

import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_unsupervised_clustering import UnsupervisedClusteringExperiment


def _build_mock_df() -> pd.DataFrame:
    rows = []
    for idx in range(24):
        rows.append(
            {
                'id_pacie': idx,
                'feature_a': float(idx),
                'feature_b': float(idx % 3),
                'feature_c': float((idx // 3) % 4),
                'fr_cance': 'Sí' if idx % 2 == 0 else 'No',
                'ana_dura': 'Buscada positivo' if idx % 5 == 0 else 'No buscada',
                'all_missing': None,
            }
        )
    return pd.DataFrame(rows)


def test_run_supports_manhattan_metric_and_exports_coordinates(tmp_path: Path) -> None:
    experiment = UnsupervisedClusteringExperiment()
    color_rules_path = tmp_path / 'umap_colors.json'
    color_rules_path.write_text(
        json.dumps(
            {
                'default': 'other',
                'rules': [
                    {'color': 'cancer', 'var': 'fr_cance', 'eq': 'Sí'},
                    {'color': 'positive_study', 'all': [{'var': 'ana_dura', 'eq': 'Buscada positivo'}]},
                ],
            }
        ),
        encoding='utf-8',
    )
    config = {
        'clustering_max_samples': 20,
        'clustering_metric': 'manhattan',
        'clustering_n_clusters': 3,
        'clustering_n_neighbors': 5,
        'clustering_min_dist': 0.1,
        'clustering_color_rules_json': str(color_rules_path),
        'output_dir': str(tmp_path),
    }

    experiment.run(_build_mock_df(), config)

    latex_output = experiment.export_latex()
    assert 'Patient_Count' in latex_output
    assert 'Manhattan Space' in latex_output
    assert experiment.plotly_figure is not None

    export_path = tmp_path / 'umap_coordinates.csv'
    assert export_path.exists()
    export_df = pd.read_csv(export_path)
    assert {'id_pacie', 'umap_dimension_1', 'umap_dimension_2', 'cluster', 'color_group', 'fr_cance', 'ana_dura'}.issubset(export_df.columns)
    assert len(export_df) == 20
    assert {'cancer', 'other', 'positive_study'} & set(export_df['color_group'])
