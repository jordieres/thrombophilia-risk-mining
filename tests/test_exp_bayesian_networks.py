from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_bayesian_networks import BayesianNetworkExperiment


def test_run_supports_custom_target_and_group_columns() -> None:
    experiment = BayesianNetworkExperiment()
    df = pd.DataFrame(
        {
            'sexo': ['Male', 'Female', 'Female', 'Male'],
            'hospital': ['A', 'A', 'B', 'B'],
            'alt_target': ['Homocigoto', 'Heterocigoto', 'Missing', 'Heterocigoto'],
        }
    )
    config = {
        'bayesian_target_column': 'alt_target',
        'bayesian_group_column': 'hospital',
        'bayesian_target_valid_labels': ['Homocigoto', 'Heterocigoto'],
    }

    experiment.run(df, config)

    latex_output = experiment.export_latex()
    assert 'alt_target' in latex_output
    assert 'hospital' in latex_output
    assert experiment.plotly_figure is not None
