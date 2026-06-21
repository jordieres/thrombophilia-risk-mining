from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_permutation_importance import PermutationImportanceExperiment


def test_run_supports_custom_target_and_labels() -> None:
    experiment = PermutationImportanceExperiment()
    df = pd.DataFrame(
        {
            'id_pacie': range(8),
            'sexo': ['Hombre', 'Mujer'] * 4,
            'edad': [40, 50, 41, 51, 42, 52, 43, 53],
            'marker': ['A', 'A', 'A', 'B', 'B', 'B', 'B', 'A'],
            'lab_value': [1.0, 1.2, 1.1, 2.0, 2.1, 1.9, 2.2, 1.3],
            'alt_target': ['Homocigoto', 'Heterocigoto', 'Homocigoto', 'Heterocigoto', 'Homocigoto', 'Heterocigoto', 'Homocigoto', 'Heterocigoto'],
        }
    )
    config = {
        'permutation_max_samples': 8,
        'permutation_max_splits': 2,
        'permutation_repeats': 1,
        'permutation_estimators': 5,
        'permutation_target_column': 'alt_target',
        'permutation_positive_label': 'Homocigoto',
        'permutation_negative_label': 'Heterocigoto',
    }

    experiment.run(df, config)

    assert 'alt_target' in experiment.export_latex()
    assert experiment.plotly_figure is not None
