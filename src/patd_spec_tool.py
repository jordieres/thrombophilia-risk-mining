"""One-off transformer for adapting patD.parquet to the Excel variable spec.

Column C rules can transform or filter rows, while column D controls how
missing values are backfilled for retained variables.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype


DEFAULT_ID_COLUMN = "id_pacie"
DEFAULT_TARGET_COLUMNS: tuple[str, ...] = ("ana_dura",)
HEADER_VARIABLE_NAME = "Nombre variable"
ANA_DIME_ALLOWED_VALUES = {"Positivo", "Negativo", "No practicado"}
YES_NO_ALLOWED_VALUES = {"Sí", "No"}
SEX_ALLOWED_VALUES = {"Hombre", "Mujer"}
RACE_ALLOWED_VALUES = {
    "Caucásica",
    "América Latina",
    "Negra",
    "Asiática",
    "Romaní",
    "Arábica",
    "Otras",
}

ENUM_RULES: dict[str, set[str]] = {
    "sexo": SEX_ALLOWED_VALUES,
    "raza": RACE_ALLOWED_VALUES,
    "sin_tvp_": {"EP", "EP+TVP", "TVP/EP", "TVP", "TVS", "Asintomático"},
    "ep_tac_r": {"Normal", "Trombosis", "Embolia Pulmonar"},
    "eptacven": YES_NO_ALLOWED_VALUES,
    "ep_t_reg": YES_NO_ALLOWED_VALUES,
    "ep_ecoca": YES_NO_ALLOWED_VALUES,
    "ep_eco_v": YES_NO_ALLOWED_VALUES,
    "var52": YES_NO_ALLOWED_VALUES,
    "epecoddv": YES_NO_ALLOWED_VALUES,
    "tvp_eco_": {"Normal", "Trombosis"},
    "tv_l_esu": YES_NO_ALLOWED_VALUES,
    "tvp_orig": {"Secundaria a catéter", "No secundaria a catéter"},
    "tv_l_ein": YES_NO_ALLOWED_VALUES,
    "tvp_prox": {
        "Proximal",
        "Distal",
        "Proximal (incluyendo la vena poplítea)",
        "Distal (excluyendo la vena poplítea)",
    },
    "tv_l_vpo": YES_NO_ALLOWED_VALUES,
    "tv_l_vme": YES_NO_ALLOWED_VALUES,
    "tv_l_ves": YES_NO_ALLOWED_VALUES,
    "tv_l_svc": YES_NO_ALLOWED_VALUES,
    "tv_l_vre": YES_NO_ALLOWED_VALUES,
    "tv_l_vrn": YES_NO_ALLOWED_VALUES,
    "tv_l_vca": YES_NO_ALLOWED_VALUES,
    "tv_l_yug": YES_NO_ALLOWED_VALUES,
    "tv_l_ova": YES_NO_ALLOWED_VALUES,
    "tv_l_sup": YES_NO_ALLOWED_VALUES,
    "tv_l_pul": YES_NO_ALLOWED_VALUES,
    "tv_l_ove": YES_NO_ALLOWED_VALUES,
    "ana_dime": ANA_DIME_ALLOWED_VALUES,
}

YES_NO_COLUMNS = {
    "ant_inf",
    "ant_isq",
    "ant_clau",
    "fum_act",
    "diabetes",
    "hip_art",
    "insf_car",
    "fibr_aur",
    "trat_est",
    "e_con_pp",
    "e_con_cu",
    "e_con_ec",
    "e_con_lu",
    "e_con_af",
    "e_con_be",
    "e_con_at",
    "e_con_va",
    "e_con_ar",
    "e_con_ea",
    "e_con_pr",
    "e_con_ro",
    "e_con_av",
    "e_con_sm",
    "var171",
    "fr_cance",
    "fr_cirug",
    "fr_inmov",
    "fr_tvp_a",
    "fr_antfa",
    "fr_tvs_a",
    "fr_viaje",
    "fr_estro",
    "fr_embar",
    "fr_varic",
    "fr_antec",
    "evn_defu",
    "evn_reci",
    "evn_rec2",
    "evn_rec3",
    "evn_rec4",
    "evn_hemo",
    "evn_hem2",
    "evn_hem3",
    "evn_hem4",
    "eisq_art",
    "eisq_inf",
    "eisq_ang",
    "eisq_cer",
    "eisq_ei",
    "eisq_ol",
}

for column_name in YES_NO_COLUMNS:
    ENUM_RULES[column_name] = YES_NO_ALLOWED_VALUES


@dataclass(frozen=True)
class ThresholdRule:
    """Structured numeric validation extracted from the Excel criteria text."""

    kind: str
    lower: float | None = None
    upper: float | None = None


@dataclass(frozen=True)
class SpecialColumnRule:
    """Column-specific transformation rules inferred from the Excel criteria text."""

    replace_map: dict[float, float] | None = None
    value_remap: tuple[str, str] | None = None
    allowed_min: float | None = None
    allowed_max: float | None = None
    min_inclusive: bool = True
    max_inclusive: bool = True


def load_variable_spec(spec_path: Path) -> pd.DataFrame:
    """Loads columns A-D from the Excel spec and returns the ordered variable list."""
    spec = pd.read_excel(
        spec_path,
        header=None,
        usecols=[0, 1, 2, 3],
        names=["variable", "label", "criteria", "missing_strategy"],
    )
    spec = spec.fillna("")
    spec["variable"] = spec["variable"].astype(str).str.strip()
    spec["criteria"] = spec["criteria"].astype(str).str.strip()
    spec["missing_strategy"] = spec["missing_strategy"].astype(str).str.strip()
    spec = spec[spec["variable"].ne("")]
    spec = spec[spec["variable"].ne(HEADER_VARIABLE_NAME)]
    return spec.reset_index(drop=True)


def replace_numeric_sentinels(df: pd.DataFrame) -> pd.DataFrame:
    """Replaces the int64 minimum sentinel used by some parquet exports with NaN."""
    cleaned = df.copy()
    sentinel = np.iinfo(np.int64).min
    numeric_columns = cleaned.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_columns:
        cleaned[numeric_columns] = cleaned[numeric_columns].replace(sentinel, np.nan)
    return cleaned


def normalize_selected_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Applies only the normalizations needed to make the selected patD subset analyzable."""
    normalized = replace_numeric_sentinels(df)
    if "sin_tvp_" in normalized.columns:
        normalized["sin_tvp_"] = normalized["sin_tvp_"].replace({"TVP/EP": "EP+TVP"})
    return normalized


def parse_special_column_rule(criteria: str) -> SpecialColumnRule | None:
    """Parses special transformation and row-filtering rules from column C."""
    stripped_text = criteria.strip()
    text = stripped_text.casefold().replace(",", ".")
    if not text or "todo ok" in text:
        return None
    if remap_strategy := _parse_value_remap_strategy(stripped_text):
        return SpecialColumnRule(value_remap=remap_strategy)
    if "valor es 1" in text and "por encima de 35" in text:
        return SpecialColumnRule(replace_map={1.0: 0.0}, allowed_min=35.0, min_inclusive=True)
    if match := re.search(r"entre\s+(\d+(?:\.\d+)?)\s+y\s+(\d+(?:\.\d+)?)", text):
        return SpecialColumnRule(allowed_min=float(match.group(1)), allowed_max=float(match.group(2)))
    if match := re.search(r"que estén entre\s+(\d+(?:\.\d+)?)\s+y\s+(\d+(?:\.\d+)?)", text):
        return SpecialColumnRule(allowed_min=float(match.group(1)), allowed_max=float(match.group(2)))
    if match := re.search(r"hasta\s+(\d+(?:\.\d+)?)", text):
        return SpecialColumnRule(allowed_max=float(match.group(1)))
    if match := re.search(r"por encima de\s+(\d+(?:\.\d+)?)", text):
        return SpecialColumnRule(allowed_min=float(match.group(1)), min_inclusive=False)
    return None


def parse_threshold_rule(criteria: str) -> ThresholdRule | None:
    """Parses simple numeric thresholds from the free-text criteria column."""
    text = criteria.casefold().replace(",", ".")

    if match := re.search(r"entre\s+(\d+(?:\.\d+)?)\s+y\s+(\d+(?:\.\d+)?)", text):
        return ThresholdRule(kind="between", lower=float(match.group(1)), upper=float(match.group(2)))
    if match := re.search(r"por debajo de\s+(\d+(?:\.\d+)?)", text):
        return ThresholdRule(kind="lt", upper=float(match.group(1)))
    if match := re.search(r"<\s*(\d+(?:\.\d+)?)", text):
        return ThresholdRule(kind="lt", upper=float(match.group(1)))
    if match := re.search(r"hasta\s+(\d+(?:\.\d+)?)", text):
        return ThresholdRule(kind="le", upper=float(match.group(1)))
    if match := re.search(r"normal\s*>\s*(\d+(?:\.\d+)?)", text):
        return ThresholdRule(kind="gt", lower=float(match.group(1)))
    if match := re.search(r"por encima de\s+(\d+(?:\.\d+)?)", text):
        return ThresholdRule(kind="gt", lower=float(match.group(1)))
    return None


def _is_missing_strategy(strategy: str) -> bool:
    return strategy.casefold() in {"missing", "miss", "na", "n/a"}


def _parse_value_remap_strategy(strategy: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"\s*(.+?)\s*=>\s*(.+?)\s*", strategy)
    if match is None:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _normalize_strategy_fill_value(fill_value: str, series: pd.Series) -> Any:
    normalized = fill_value.strip()
    if _is_missing_strategy(normalized):
        return np.nan if is_numeric_dtype(series) else "Missing"
    if normalized.casefold() == "no":
        return "No"
    return normalized


def apply_column_c_rules(df: pd.DataFrame, spec: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Applies column-C transformations and row filters, returning the filtered frame plus audit metadata."""
    transformed = df.copy()
    criteria_audit: dict[str, Any] = {}
    global_keep_mask = pd.Series(True, index=transformed.index)

    for spec_row in spec.itertuples(index=False):
        column_name = str(spec_row.variable)
        criteria = str(spec_row.criteria)
        rule = parse_special_column_rule(criteria)
        if rule is None or column_name not in transformed.columns:
            continue

        value_remapped_count = 0
        if rule.value_remap is not None:
            source_value, target_value = rule.value_remap
            replacement = _normalize_strategy_fill_value(target_value, transformed[column_name])
            source_mask = transformed[column_name].astype("string").str.strip().eq(source_value)
            value_remapped_count = int(source_mask.sum())
            if value_remapped_count:
                transformed[column_name] = transformed[column_name].astype("object")
                transformed.loc[source_mask, column_name] = replacement

        numeric_series = pd.to_numeric(transformed[column_name], errors="coerce")
        series_for_filter = numeric_series.copy()
        replacements_applied = 0
        if rule.replace_map:
            for source_value, target_value in rule.replace_map.items():
                replacement_mask = series_for_filter == source_value
                replacements_applied += int(replacement_mask.sum())
                series_for_filter = series_for_filter.mask(replacement_mask, target_value)
            transformed[column_name] = transformed[column_name].where(numeric_series.isna(), series_for_filter)

        keep_mask = pd.Series(True, index=transformed.index)
        if rule.allowed_min is not None or rule.allowed_max is not None:
            keep_mask = series_for_filter.isna()
            if rule.allowed_min is not None:
                if rule.min_inclusive:
                    keep_mask |= series_for_filter >= rule.allowed_min
                else:
                    keep_mask |= series_for_filter > rule.allowed_min
            if rule.allowed_max is not None:
                if rule.max_inclusive:
                    keep_mask &= (series_for_filter <= rule.allowed_max) | series_for_filter.isna()
                else:
                    keep_mask &= (series_for_filter < rule.allowed_max) | series_for_filter.isna()

        dropped_rows = int((global_keep_mask & ~keep_mask).sum())
        global_keep_mask &= keep_mask
        criteria_audit[column_name] = {
            "criteria": criteria,
            "replacements_applied": replacements_applied,
            "value_remapped_count": value_remapped_count,
            "dropped_row_count": dropped_rows,
            "allowed_min": rule.allowed_min,
            "allowed_max": rule.allowed_max,
            "min_inclusive": rule.min_inclusive,
            "max_inclusive": rule.max_inclusive,
        }
        if rule.value_remap is not None:
            criteria_audit[column_name]["remap_source"] = rule.value_remap[0]
            criteria_audit[column_name]["remap_target"] = rule.value_remap[1]

    filtered = transformed.loc[global_keep_mask].reset_index(drop=True)
    criteria_audit["__overall__"] = {
        "input_row_count": int(len(df)),
        "output_row_count": int(len(filtered)),
        "discarded_row_count": int(len(df) - len(filtered)),
    }
    return filtered, criteria_audit


def apply_missing_strategies(df: pd.DataFrame, spec: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Applies column-D missing-value directives from the Excel spec."""
    transformed = df.copy()
    missing_audit: dict[str, Any] = {}

    for spec_row in spec.itertuples(index=False):
        column_name = str(spec_row.variable)
        strategy = str(spec_row.missing_strategy).strip()
        if not strategy or column_name not in transformed.columns:
            continue

        remapped_count = 0
        remap_strategy = _parse_value_remap_strategy(strategy)
        if remap_strategy is not None:
            source_value, target_value = remap_strategy
            replacement = _normalize_strategy_fill_value(target_value, transformed[column_name])
            source_mask = transformed[column_name].astype("string").str.strip().eq(source_value)
            remapped_count = int(source_mask.sum())
            if remapped_count:
                transformed[column_name] = transformed[column_name].astype("object")
                transformed.loc[source_mask, column_name] = replacement

        original_nulls = int(transformed[column_name].isna().sum())
        applied_fill_value: str | None = None
        filled_count = 0

        if strategy.casefold() == "no":
            transformed[column_name] = transformed[column_name].astype("object").where(
                transformed[column_name].notna(),
                "No",
            )
            applied_fill_value = "No"
        elif _is_missing_strategy(strategy):
            if is_numeric_dtype(transformed[column_name]):
                transformed[column_name] = transformed[column_name].astype("Float64")
                applied_fill_value = "NA"
            else:
                transformed[column_name] = transformed[column_name].astype("object").where(
                    transformed[column_name].notna(),
                    "Missing",
                )
                applied_fill_value = "Missing"
        elif remap_strategy is None:
            missing_audit[column_name] = {"strategy": strategy, "filled_count": 0, "warning": "unhandled_strategy"}
            continue

        if applied_fill_value is not None:
            filled_count = int(original_nulls - transformed[column_name].isna().sum())

        missing_audit[column_name] = {
            "strategy": strategy,
            "remapped_count": remapped_count,
            "filled_count": filled_count,
            "remaining_null_count": int(transformed[column_name].isna().sum()),
        }
        if applied_fill_value is not None:
            missing_audit[column_name]["applied_fill_value"] = applied_fill_value
        if remap_strategy is not None:
            missing_audit[column_name]["remap_source"] = remap_strategy[0]
            missing_audit[column_name]["remap_target"] = remap_strategy[1]

    return transformed, missing_audit


def build_validation_report(
    df: pd.DataFrame,
    spec: pd.DataFrame,
    id_column: str,
    target_columns: list[str],
    source_path: Path,
    output_path: Path,
    criteria_audit: dict[str, Any],
    missing_audit: dict[str, Any],
) -> dict[str, Any]:
    """Builds a detailed validation report for the transformed dataset."""
    report: dict[str, Any] = {
        "source_path": str(source_path),
        "output_path": str(output_path),
        "row_count": int(len(df)),
        "column_count": int(df.shape[1]),
        "id_column": id_column,
        "target_columns": target_columns,
        "feature_columns": [column for column in df.columns if column not in {id_column, *target_columns}],
        "hard_failures": [],
        "warnings": [],
        "criteria_audit": criteria_audit,
        "missing_audit": missing_audit,
        "columns": {},
    }

    for spec_row in spec.itertuples(index=False):
        column_name = str(spec_row.variable)
        series = df[column_name]
        column_report: dict[str, Any] = {
            "dtype": str(series.dtype),
            "non_null_count": int(series.notna().sum()),
            "null_count": int(series.isna().sum()),
            "criteria": str(spec_row.criteria),
            "missing_strategy": str(spec_row.missing_strategy),
        }

        allowed_values = ENUM_RULES.get(column_name)
        if allowed_values is not None:
            effective_allowed_values = set(allowed_values)
            missing_strategy = str(spec_row.missing_strategy).strip()
            if strategy := missing_strategy.casefold():
                if strategy == "no":
                    effective_allowed_values.add("No")
                elif _is_missing_strategy(missing_strategy):
                    effective_allowed_values.add("Missing")
            observed_values = sorted({str(value) for value in series.dropna().unique()})
            invalid_values = sorted(value for value in observed_values if value not in effective_allowed_values)
            column_report["allowed_values"] = sorted(effective_allowed_values)
            column_report["observed_values"] = observed_values
            column_report["invalid_values"] = invalid_values
            if invalid_values:
                report["hard_failures"].append(
                    f"{column_name}: invalid categorical values {invalid_values}"
                )

        threshold_rule = parse_threshold_rule(str(spec_row.criteria))
        if threshold_rule is not None and is_numeric_dtype(series):
            numeric_series = pd.to_numeric(series, errors="coerce").dropna()
            threshold_report: dict[str, Any] = {
                "kind": threshold_rule.kind,
                "non_null_numeric_count": int(numeric_series.shape[0]),
            }
            if not numeric_series.empty:
                threshold_report["min"] = float(numeric_series.min())
                threshold_report["max"] = float(numeric_series.max())

            if threshold_rule.kind == "between":
                assert threshold_rule.lower is not None
                assert threshold_rule.upper is not None
                threshold_report["lower"] = threshold_rule.lower
                threshold_report["upper"] = threshold_rule.upper
                threshold_report["below_count"] = int((numeric_series < threshold_rule.lower).sum())
                threshold_report["within_count"] = int(
                    ((numeric_series >= threshold_rule.lower) & (numeric_series <= threshold_rule.upper)).sum()
                )
                threshold_report["above_count"] = int((numeric_series > threshold_rule.upper).sum())
            elif threshold_rule.kind in {"le", "lt"}:
                assert threshold_rule.upper is not None
                threshold_report["upper"] = threshold_rule.upper
                comparator = numeric_series < threshold_rule.upper if threshold_rule.kind == "lt" else numeric_series <= threshold_rule.upper
                threshold_report["within_count"] = int(comparator.sum())
                threshold_report["above_count"] = int((~comparator).sum())
            elif threshold_rule.kind == "gt":
                assert threshold_rule.lower is not None
                threshold_report["lower"] = threshold_rule.lower
                threshold_report["within_count"] = int((numeric_series > threshold_rule.lower).sum())
                threshold_report["below_count"] = int((numeric_series <= threshold_rule.lower).sum())

            column_report["threshold_validation"] = threshold_report

        report["columns"][column_name] = column_report

    if id_column not in df.columns:
        report["hard_failures"].append(f"Missing id/reference column '{id_column}' in transformed dataset.")

    return report


def transform_patd_dataset(
    input_path: Path,
    spec_path: Path,
    output_path: Path,
    report_path: Path,
    id_column: str = DEFAULT_ID_COLUMN,
    target_columns: tuple[str, ...] = DEFAULT_TARGET_COLUMNS,
    fail_on_validation_issues: bool = True,
) -> dict[str, Any]:
    """Transforms patD using the Excel spec, writes the subset parquet and validation report."""
    spec = load_variable_spec(spec_path)
    source_df = pd.read_parquet(input_path)

    retained_target_columns = [column for column in target_columns if column and column in source_df.columns]
    required_columns = [id_column, *retained_target_columns, *spec["variable"].tolist()]
    required_columns = list(dict.fromkeys(required_columns))
    missing_columns = [column for column in required_columns if column not in source_df.columns]
    if missing_columns:
        raise ValueError(f"Input dataset is missing required columns: {missing_columns}")

    transformed_df = normalize_selected_columns(source_df.loc[:, required_columns])
    transformed_df, criteria_audit = apply_column_c_rules(transformed_df, spec)
    transformed_df, missing_audit = apply_missing_strategies(transformed_df, spec)
    transformed_df.to_parquet(output_path, index=False)

    report = build_validation_report(
        df=transformed_df,
        spec=spec,
        id_column=id_column,
        target_columns=retained_target_columns,
        source_path=input_path,
        output_path=output_path,
        criteria_audit=criteria_audit,
        missing_audit=missing_audit,
    )
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    if fail_on_validation_issues and report["hard_failures"]:
        failures = "\n".join(report["hard_failures"])
        raise ValueError(f"Validation failed for the transformed dataset:\n{failures}")

    return report


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds the CLI parser for the one-off patD transformer."""
    parser = argparse.ArgumentParser(
        description=(
            "Create a modeling-ready patD subset using the Excel variable list "
            "while preserving the patient id only as a reference column."
        )
    )
    parser.add_argument("--input-parquet", default="data/patD.parquet", help="Source patD parquet path.")
    parser.add_argument(
        "--spec-xlsx",
        required=True,
        help="Excel file with variables in column A, criteria in column C, and missing-value directives in column D.",
    )
    parser.add_argument(
        "--output-parquet",
        default="out/patD_spec_subset.parquet",
        help="Output parquet path containing id_pacie plus only the selected variables.",
    )
    parser.add_argument(
        "--report-json",
        default="out/patD_spec_subset_validation.json",
        help="Validation report path in JSON format.",
    )
    parser.add_argument(
        "--id-column",
        default=DEFAULT_ID_COLUMN,
        help="Reference identifier column to preserve without including it in feature lists.",
    )
    parser.add_argument(
        "--target-columns",
        nargs="*",
        default=list(DEFAULT_TARGET_COLUMNS),
        help="Target columns to preserve even if they are not listed in the Excel variable spec.",
    )
    parser.add_argument(
        "--allow-validation-issues",
        action="store_true",
        help="Write outputs even if categorical validation finds values outside the expected sets.",
    )
    return parser


def main() -> None:
    """Command-line entrypoint for the one-off patD adaptation tool."""
    parser = build_arg_parser()
    args = parser.parse_args()

    output_path = Path(args.output_parquet)
    report_path = Path(args.report_json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = transform_patd_dataset(
        input_path=Path(args.input_parquet),
        spec_path=Path(args.spec_xlsx),
        output_path=output_path,
        report_path=report_path,
        id_column=args.id_column,
        target_columns=tuple(args.target_columns),
        fail_on_validation_issues=not args.allow_validation_issues,
    )

    print(f"Subset written to {output_path}")
    print(f"Validation report written to {report_path}")
    print(f"Rows: {report['row_count']}")
    print(f"Feature columns (excluding {report['id_column']}): {len(report['feature_columns'])}")
    if report["hard_failures"]:
        print(f"Validation issues detected: {len(report['hard_failures'])}")
    else:
        print("Validation checks passed.")


if __name__ == "__main__":
    main()
