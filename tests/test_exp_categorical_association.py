from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from exp_categorical_association import CategoricalAssociationExperiment


def _build_mock_df() -> pd.DataFrame:
    rows = []
    for idx in range(12):
        positive = idx < 6
        rows.append(
            {
                'id_pacie': idx,
                'ana_dura': 'Buscada positivo' if positive else 'Buscada negativo',
                'alt_target': 'Sí' if positive else ('No' if idx < 10 else 'Missing'),
                'sexo': 'Mujer' if positive else 'Hombre',
                'fr_cance': 'Sí' if positive else 'No',
                'sin_tvp_': 'EP' if idx % 2 == 0 else 'TVP',
                'raza': 'Caucásica' if idx % 3 else 'Asiática',
                'edad': 40 + idx,
            }
        )
    return pd.DataFrame(rows)


def test_run_builds_categorical_association_outputs(tmp_path: Path) -> None:
    experiment = CategoricalAssociationExperiment()
    config = {
        'association_max_samples': 12,
        'association_max_columns': 5,
        'association_top_k': 4,
        'association_include_target': True,
        'association_target_column': 'alt_target',
        'association_target_valid_labels': ['Sí', 'No'],
        'output_dir': str(tmp_path),
    }

    experiment.run(_build_mock_df(), config)

    latex_output = experiment.export_latex()
    assert 'Strongest Pairwise Categorical Associations' in latex_output
    assert experiment.plotly_figure is not None

    matrix_path = tmp_path / 'categorical_association_matrix.csv'
    pairs_path = tmp_path / 'categorical_association_top_pairs.csv'
    assert matrix_path.exists()
    assert pairs_path.exists()

    matrix_df = pd.read_csv(matrix_path, index_col=0)
    pairs_df = pd.read_csv(pairs_path)
    assert 'alt_target' in matrix_df.columns
    assert {'variable_a', 'variable_b', 'cramers_v'}.issubset(pairs_df.columns)
    assert len(pairs_df) == 4
