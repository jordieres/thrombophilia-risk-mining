from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pandas as pd


def test_recolor_umap_reuses_exported_coordinates(tmp_path: Path) -> None:
    umap_csv = tmp_path / 'umap_coordinates.csv'
    pd.DataFrame(
        {
            'id_pacie': [1, 2, 3],
            'umap_dimension_1': [0.1, 0.2, 0.3],
            'umap_dimension_2': [1.1, 1.2, 1.3],
            'cluster': ['0', '1', '1'],
            'ana_dura': ['Buscada positivo', 'Buscada negativo', 'No buscada'],
        }
    ).to_csv(umap_csv, index=False)

    rules_path = tmp_path / 'color_rules.json'
    rules_path.write_text(
        json.dumps(
            {
                'default': 'other',
                'rules': [
                    {'color': 'positive', 'var': 'ana_dura', 'eq': 'Buscada positivo'},
                    {'color': 'negative', 'var': 'ana_dura', 'eq': 'Buscada negativo'},
                ],
            }
        ),
        encoding='utf-8',
    )

    output_html = tmp_path / 'recolored_umap.html'
    subprocess.run(
        [
            sys.executable,
            'src/recolor_umap.py',
            '--umap-csv',
            str(umap_csv),
            '--color-rules-json',
            str(rules_path),
            '--output-html',
            str(output_html),
        ],
        check=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert output_html.exists()
    recolored_csv = tmp_path / 'recolored_umap_with_colors.csv'
    assert recolored_csv.exists()
    recolored_df = pd.read_csv(recolored_csv)
    assert recolored_df['color_group'].tolist() == ['positive', 'negative', 'other']
