from __future__ import annotations

from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from patd_spec_tool import transform_patd_dataset


def test_transform_patd_dataset_selects_spec_columns_and_reports_features(tmp_path: Path) -> None:
    input_path = tmp_path / "patD.parquet"
    spec_path = tmp_path / "spec.xlsx"
    output_path = tmp_path / "subset.parquet"
    report_path = tmp_path / "report.json"

    sentinel = np.iinfo(np.int64).min
    source_df = pd.DataFrame(
        {
            "id_pacie": [1, 2],
            "sexo": ["Hombre", "Mujer"],
            "edad": [45, 52],
            "raza": ["Caucásica", "Negra"],
            "talla": [170, sentinel],
            "ana_dime": ["Positivo", None],
            "ana_dura": ["Buscada positivo", "Buscada negativo"],
            "extra_column": ["ignore", "ignore"],
        }
    )
    source_df.to_parquet(input_path, index=False)

    spec_df = pd.DataFrame(
        [
            ["Nombre variable", "Etiqueta", "", "si missing, considerar"],
            ["sexo", "Sexo", "Puede ser varón o mujer", "missing"],
            ["edad", "Edad", "La edad en el momento del diagnóstico de la trombosis", "missing"],
            ["raza", "Raza", "Raza o etnia, se divide en caucásica, América Latina, Negra, Asiática, Romaní, Arábica u otras.", "missing"],
            ["talla", "Talla", "Talla en cm en el momento del diagnóstico de la trombosis", "missing"],
            ["ana_dime", "Dimero D", 'No practicado => missing', "missing"],
        ]
    )
    spec_df.to_excel(spec_path, header=False, index=False)

    report = transform_patd_dataset(
        input_path=input_path,
        spec_path=spec_path,
        output_path=output_path,
        report_path=report_path,
    )

    transformed_df = pd.read_parquet(output_path)
    assert transformed_df.columns.tolist() == ["id_pacie", "ana_dura", "sexo", "edad", "raza", "talla", "ana_dime"]
    assert transformed_df.loc[1, "ana_dime"] == "Missing"
    assert pd.isna(transformed_df.loc[1, "talla"])

    assert report["id_column"] == "id_pacie"
    assert report["target_columns"] == ["ana_dura"]
    assert "id_pacie" not in report["feature_columns"]
    assert "ana_dura" not in report["feature_columns"]
    assert report["feature_columns"] == ["sexo", "edad", "raza", "talla", "ana_dime"]
    assert report["hard_failures"] == []


def test_transform_patd_dataset_fails_for_invalid_enum_values(tmp_path: Path) -> None:
    input_path = tmp_path / "patD.parquet"
    spec_path = tmp_path / "spec.xlsx"
    output_path = tmp_path / "subset.parquet"
    report_path = tmp_path / "report.json"

    pd.DataFrame(
        {
            "id_pacie": [1],
            "sexo": ["Otro"],
        }
    ).to_parquet(input_path, index=False)

    pd.DataFrame(
        [
            ["Nombre variable", "Etiqueta", "", "si missing, considerar"],
            ["sexo", "Sexo", "Puede ser varón o mujer", "missing"],
        ]
    ).to_excel(spec_path, header=False, index=False)

    try:
        transform_patd_dataset(
            input_path=input_path,
            spec_path=spec_path,
            output_path=output_path,
            report_path=report_path,
        )
    except ValueError as exc:
        assert "sexo: invalid categorical values ['Otro']" in str(exc)
    else:
        raise AssertionError("Expected validation failure for invalid categorical values.")


def test_transform_patd_dataset_applies_column_c_filters_and_column_d_defaults(tmp_path: Path) -> None:
    input_path = tmp_path / "patD.parquet"
    spec_path = tmp_path / "spec.xlsx"
    output_path = tmp_path / "subset.parquet"
    report_path = tmp_path / "report.json"

    pd.DataFrame(
        {
            "id_pacie": [1, 2, 3, 4],
            "peso": [70, 20, None, 85],
            "tension_": [120, 1, None, 34],
            "ant_inf": [None, None, "Sí", None],
            "ana_dura": ["Buscada positivo", "Buscada negativo", "Missing", "No buscada"],
        }
    ).to_parquet(input_path, index=False)

    pd.DataFrame(
        [
            ["Nombre variable", "Etiqueta", "Valores normales", "si missing, considerar"],
            ["peso", "Peso", "entre 29 y 300", "missing"],
            [
                "tension_",
                "Tensión arterial sistólica (mmHg)",
                "Si el valor es 1, hay que considerarlo 0 (paciente fallecido, pero el sistema no deja poner 0). Hay algunos valores raros (5, 9…). Vamos a incluir sólo los que estén por encima de 35, pero debería ser una variable categórica (normal entre 100-140)",
                "missing",
            ],
            ["ant_inf", "¿Antecedente de infarto de miocardio o angina?", "", "No"],
        ]
    ).to_excel(spec_path, header=False, index=False)

    report = transform_patd_dataset(
        input_path=input_path,
        spec_path=spec_path,
        output_path=output_path,
        report_path=report_path,
    )

    transformed_df = pd.read_parquet(output_path)
    assert transformed_df["id_pacie"].tolist() == [1, 3]
    assert transformed_df["tension_"].tolist()[0] == 120
    assert pd.isna(transformed_df["tension_"].tolist()[1])
    assert transformed_df.loc[0, "ant_inf"] == "No"
    assert transformed_df.loc[1, "ant_inf"] == "Sí"
    assert pd.isna(transformed_df.loc[1, "peso"])

    assert report["criteria_audit"]["peso"]["dropped_row_count"] == 1
    assert report["criteria_audit"]["tension_"]["replacements_applied"] == 1
    assert report["criteria_audit"]["__overall__"]["discarded_row_count"] == 2
    assert report["missing_audit"]["ant_inf"]["filled_count"] == 1


def test_transform_patd_dataset_remaps_no_practicado_from_column_c(tmp_path: Path) -> None:
    input_path = tmp_path / "patD.parquet"
    spec_path = tmp_path / "spec.xlsx"
    output_path = tmp_path / "subset.parquet"
    report_path = tmp_path / "report.json"

    pd.DataFrame(
        {
            "id_pacie": [1, 2, 3],
            "ana_dime": ["No practicado", "Positivo", None],
            "ana_dura": ["Buscada positivo", "Buscada negativo", "Missing"],
        }
    ).to_parquet(input_path, index=False)

    pd.DataFrame(
        [
            ["Nombre variable", "Etiqueta", "Valores normales", "si missing, considerar"],
            ["ana_dime", "Categórica Dímero D", "No practicado => missing", "missing"],
        ]
    ).to_excel(spec_path, header=False, index=False)

    report = transform_patd_dataset(
        input_path=input_path,
        spec_path=spec_path,
        output_path=output_path,
        report_path=report_path,
    )

    transformed_df = pd.read_parquet(output_path)
    assert transformed_df["ana_dime"].tolist() == ["Missing", "Positivo", "Missing"]
    assert report["criteria_audit"]["ana_dime"]["value_remapped_count"] == 1
    assert report["missing_audit"]["ana_dime"]["filled_count"] == 1
