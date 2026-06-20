from __future__ import annotations

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
                'all_missing': None,
            }
        )
    return pd.DataFrame(rows)


def test_run_supports_manhattan_metric() -> None:
    experiment = UnsupervisedClusteringExperiment()
    config = {
        'clustering_max_samples': 20,
        'clustering_metric': 'manhattan',
        'clustering_n_clusters': 3,
        'clustering_n_neighbors': 5,
        'clustering_min_dist': 0.1,
    }

    experiment.run(_build_mock_df(), config)

    latex_output = experiment.export_latex()
    assert 'Patient_Count' in latex_output
    assert 'Manhattan Space' in latex_output
    assert experiment.plotly_figure is not None
