"""Compatibility helpers and safe entry point for manuscript reanalysis.

The descriptive helper functions below retain their historical API for the
September audit script. Their historical percentages are not manuscript tables.
New model runs delegate to manuscript_reanalysis; the former unsafe model loop
has been removed. See docs/docs_source/manuscript_reanalysis.rst.

Historical helper scope:

This module generates a reproducible response package for manuscript review:

* mutually exclusive cohort comparisons (``tested`` vs ``not tested``),
* outcome mapping and prevalence summaries,
* threshold-level confusion-matrix audits for each score strategy,
* calibration summaries and temporal validation diagnostics,
* a Markdown response that can be shared with coauthors.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd



SEARCHED_POSITIVE = "Buscada positivo"
SEARCHED_NEGATIVE = "Buscada negativo"
NOT_SEARCHED = "No buscada"


@dataclass(frozen=True)
class OutcomeSpec:
    """Defines one manuscript outcome and its human-readable label."""

    column: str
    label: str


@dataclass(frozen=True)
class TemporalValidationResult:
    """Stores train/test metrics for one temporal holdout evaluation."""

    strategy_name: str
    cutoff_year: int
    development_n: int
    validation_n: int
    auc: float
    brier_score: float
    selected_threshold: float
    sensitivity: float
    specificity: float
    ppv: float
    npv: float
    tp: int
    fp: int
    tn: int
    fn: int


OUTCOMES: Sequence[OutcomeSpec] = (
    OutcomeSpec("var154", "Protein C deficiency"),
    OutcomeSpec("var155", "Protein S deficiency"),
    OutcomeSpec("var156", "Factor V Leiden"),
    OutcomeSpec("var157", "Prothrombin G20210A"),
    OutcomeSpec("var161", "Antiphospholipid syndrome"),
)


def _format_count_pct(count: int, total: int) -> str:
    """Formats a count with its within-group percentage."""
    if total <= 0:
        return f"{count}"
    return f"{count} ({(100.0 * count / total):.1f}%)"


def _safe_proportion(mask: pd.Series) -> float:
    """Returns a mean proportion while ignoring missing values."""
    if mask.empty:
        return float("nan")
    return float(mask.mean())


def _binary_series(series: pd.Series, truthy_values: Iterable[str]) -> pd.Series:
    """Maps a heterogeneous categorical series to a binary proportion scale."""
    normalized = series.astype("string").str.strip().str.casefold()
    truthy = {value.casefold() for value in truthy_values}
    return normalized.isin(truthy)


def _standardized_mean_difference_numeric(a: pd.Series, b: pd.Series) -> float:
    """Computes the standardized mean difference for numeric variables."""
    a_num = pd.to_numeric(a, errors="coerce").dropna()
    b_num = pd.to_numeric(b, errors="coerce").dropna()
    if a_num.empty or b_num.empty:
        return float("nan")
    pooled_sd = np.sqrt((a_num.var(ddof=1) + b_num.var(ddof=1)) / 2.0)
    if pooled_sd == 0 or np.isnan(pooled_sd):
        return 0.0
    return float((a_num.mean() - b_num.mean()) / pooled_sd)


def _standardized_mean_difference_binary(a: pd.Series, b: pd.Series, truthy_values: Iterable[str]) -> float:
    """Computes the standardized mean difference for a binary/categorical flag."""
    a_bin = _binary_series(a, truthy_values)
    b_bin = _binary_series(b, truthy_values)
    p1 = _safe_proportion(a_bin)
    p0 = _safe_proportion(b_bin)
    pooled = (p1 * (1 - p1) + p0 * (1 - p0)) / 2.0
    if pooled <= 0 or np.isnan(pooled):
        return 0.0
    return float((p1 - p0) / np.sqrt(pooled))


def build_tested_vs_not_tested_table(data: pd.DataFrame) -> pd.DataFrame:
    """Builds a mutually exclusive baseline comparison using standardized differences."""
    tested_mask = data["ana_dura"].astype("string").isin([SEARCHED_POSITIVE, SEARCHED_NEGATIVE])
    not_tested_mask = data["ana_dura"].astype("string") == NOT_SEARCHED
    tested = data.loc[tested_mask].copy()
    not_tested = data.loc[not_tested_mask].copy()

    rows: List[Dict[str, object]] = [
        {
            "Variable": "N",
            "Tested": len(tested),
            "Not_Tested": len(not_tested),
            "Standardized_Difference": float("nan"),
        },
        {
            "Variable": "Age, mean (SD)",
            "Tested": f"{pd.to_numeric(tested['edad'], errors='coerce').mean():.1f} ({pd.to_numeric(tested['edad'], errors='coerce').std():.1f})",
            "Not_Tested": f"{pd.to_numeric(not_tested['edad'], errors='coerce').mean():.1f} ({pd.to_numeric(not_tested['edad'], errors='coerce').std():.1f})",
            "Standardized_Difference": _standardized_mean_difference_numeric(tested["edad"], not_tested["edad"]),
        },
        {
            "Variable": "Female sex",
            "Tested": _format_count_pct(int(_binary_series(tested["sexo"], ["Mujer", "Female"]).sum()), len(tested)),
            "Not_Tested": _format_count_pct(int(_binary_series(not_tested["sexo"], ["Mujer", "Female"]).sum()), len(not_tested)),
            "Standardized_Difference": _standardized_mean_difference_binary(tested["sexo"], not_tested["sexo"], ["Mujer", "Female"]),
        },
    ]

    binary_specs = [
        ("fr_cance", "Active cancer", ["Sí", "Si", "Yes"]),
        ("fr_inmov", "Immobilization", ["Sí", "Si", "Yes"]),
        ("fr_tvp_a", "Prior VTE", ["Sí", "Si", "Yes"]),
        ("e_con_lu", "Known lupus", ["Sí", "Si", "Yes"]),
        ("e_con_af", "Known APS", ["Sí", "Si", "Yes"]),
    ]
    for column, label, truthy_values in binary_specs:
        if column not in data.columns:
            continue
        rows.append(
            {
                "Variable": label,
                "Tested": _format_count_pct(int(_binary_series(tested[column], truthy_values).sum()), len(tested)),
                "Not_Tested": _format_count_pct(int(_binary_series(not_tested[column], truthy_values).sum()), len(not_tested)),
                "Standardized_Difference": _standardized_mean_difference_binary(
                    tested[column], not_tested[column], truthy_values
                ),
            }
        )

    numeric_specs = [
        ("ana_hemo", "Hemoglobin, mean (SD)"),
        ("ana_leuc", "Leukocytes, mean (SD)"),
        ("ddvalmcg", "D-dimer, mean (SD)"),
    ]
    for column, label in numeric_specs:
        if column not in data.columns:
            continue
        tested_num = pd.to_numeric(tested[column], errors="coerce")
        not_tested_num = pd.to_numeric(not_tested[column], errors="coerce")
        rows.append(
            {
                "Variable": label,
                "Tested": f"{tested_num.mean():.2f} ({tested_num.std():.2f})",
                "Not_Tested": f"{not_tested_num.mean():.2f} ({not_tested_num.std():.2f})",
                "Standardized_Difference": _standardized_mean_difference_numeric(tested[column], not_tested[column]),
            }
        )

    return pd.DataFrame(rows)


def build_outcome_prevalence_table(data: pd.DataFrame, outcomes: Sequence[OutcomeSpec]) -> pd.DataFrame:
    """Summarizes outcome prevalence among tested patients only."""
    tested_mask = data["ana_dura"].astype("string").isin([SEARCHED_POSITIVE, SEARCHED_NEGATIVE])
    tested = data.loc[tested_mask].copy()
    rows: List[Dict[str, object]] = []
    for spec in outcomes:
        if spec.column not in tested.columns:
            continue
        binary = tested[tested[spec.column].astype("string").isin(["Sí", "No"])].copy()
        if binary.empty:
            continue
        positive_n = int((binary[spec.column].astype("string") == "Sí").sum())
        rows.append(
            {
                "Outcome": spec.label,
                "Column": spec.column,
                "Tested_N": len(binary),
                "Positive_N": positive_n,
                "Positive_%": 100.0 * positive_n / len(binary),
            }
        )
    return pd.DataFrame(rows).sort_values("Outcome").reset_index(drop=True)



def generate_review_package(data_path: Path, output_dir: Path) -> Path:
    """Delegate to the supported tested-only, pre-test reanalysis pipeline.

    A legacy ``--output-dir out`` request is routed into a dedicated child
    directory so existing historical artifacts cannot be silently overwritten.
    Use manuscript_reanalysis.py directly for outcome selection and resume.
    """
    from manuscript_reanalysis import run_reanalysis
    destination = output_dir / "manuscript_reanalysis" if output_dir.name == "out" else output_dir
    return run_reanalysis(data_path, destination)


def main() -> None:
    """Keep the old executable name while using the corrected analysis engine."""
    parser = argparse.ArgumentParser(description="Compatibility entry point for the corrected manuscript pipeline")
    parser.add_argument("--data", type=Path, default=Path("data/patD.parquet"))
    parser.add_argument("--output-dir", type=Path, default=Path("out/manuscript_reanalysis_2026-09-08"))
    args = parser.parse_args()
    print(generate_review_package(args.data, args.output_dir))


if __name__ == "__main__":
    main()
