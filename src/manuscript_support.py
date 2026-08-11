"""Manuscript-oriented audit utilities for the thrombophilia score study.

This module generates a reproducible response package for manuscript review:

* mutually exclusive cohort comparisons (``tested`` vs ``not tested``),
* outcome mapping and prevalence summaries,
* threshold-level confusion-matrix audits for each score strategy,
* calibration summaries and temporal validation diagnostics,
* a Markdown response that can be shared with coauthors.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, Sequence

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from data_processor import ClinicalDataProcessor
from exp_clinical_risk_score import ClinicalRiskScoreExperiment


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


def _calibration_table(y_true: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> pd.DataFrame:
    """Builds a binned calibration table for a vector of probabilities."""
    observed, predicted = calibration_curve(y_true, probabilities, n_bins=bins, strategy="quantile")
    frame = pd.DataFrame({"Predicted_Probability": predicted, "Observed_Frequency": observed})
    frame["Absolute_Error"] = (frame["Observed_Frequency"] - frame["Predicted_Probability"]).abs()
    return frame


def _clinical_utility_row(profile_df: pd.DataFrame) -> Dict[str, float]:
    """Converts the selected threshold row into tests-avoided and missed-diagnoses rates."""
    selected = profile_df.loc[profile_df["Selected_Threshold"]].iloc[0]
    total = int(selected["TP"] + selected["FP"] + selected["TN"] + selected["FN"])
    return {
        "Selected_Threshold": float(selected["Threshold"]),
        "Sensitivity": float(selected["Sensitivity"]),
        "Specificity": float(selected["Specificity"]),
        "PPV": float(selected["PPV"]),
        "NPV": float(selected["NPV"]),
        "Tests_Avoided_per_1000": 1000.0 * float(selected["Predicted_Negative_Count"]) / total,
        "Missed_True_Positives_per_1000": 1000.0 * float(selected["FN"]) / total,
    }


def _select_temporal_cutoff(years: pd.Series, y: np.ndarray) -> int:
    """Chooses the latest cutoff year that leaves both classes in development and validation."""
    unique_years = sorted(int(year) for year in years.dropna().unique())
    for cutoff in reversed(unique_years[:-1]):
        dev_mask = years <= cutoff
        val_mask = years > cutoff
        if dev_mask.sum() < 100 or val_mask.sum() < 100:
            continue
        if len(np.unique(y[dev_mask.to_numpy()])) < 2 or len(np.unique(y[val_mask.to_numpy()])) < 2:
            continue
        return cutoff
    raise ValueError("No valid temporal cutoff could be constructed with both classes represented.")


def run_temporal_validation(
    experiment: ClinicalRiskScoreExperiment,
    model_df: pd.DataFrame,
    target_col: str,
    identifier_col: str,
    positive_label: str,
    strategy_name: str,
    coefficient_direction: str,
    positive_if_score_at_most: bool,
    top_features: int,
    min_sensitivity: float,
    min_feature_prevalence: float,
) -> TemporalValidationResult:
    """Fits the score on earlier years and validates it on later years."""
    years = pd.to_datetime(model_df["fecha_di"], errors="coerce").dt.year
    y = np.where(model_df[target_col].astype("string") == positive_label, 1, 0)
    cutoff_year = _select_temporal_cutoff(years=years, y=y)
    dev_mask = years <= cutoff_year
    val_mask = years > cutoff_year

    development_df = model_df.loc[dev_mask].reset_index(drop=True)
    validation_df = model_df.loc[val_mask].reset_index(drop=True)
    y_dev = np.where(development_df[target_col].astype("string") == positive_label, 1, 0)
    y_val = np.where(validation_df[target_col].astype("string") == positive_label, 1, 0)

    feature_df = development_df.drop(columns=[target_col, identifier_col, "fecha_di"])
    pipeline = experiment._build_logistic_pipeline(feature_cols=feature_df.columns.tolist())
    pipeline.fit(feature_df, y_dev)

    points_table = experiment._build_points_table(
        pipeline=pipeline,
        top_features=top_features,
        model_label=strategy_name,
        coefficient_direction=coefficient_direction,
        X_reference=feature_df,
        min_feature_prevalence=min_feature_prevalence,
    )
    dev_scores = experiment._score_feature_frame_with_points(pipeline=pipeline, X=feature_df, points_table=points_table)
    dev_probabilities = pipeline.predict_proba(feature_df)[:, 1]
    dev_eval = experiment._build_evaluation(
        model_name=strategy_name,
        score_label="Integer point score",
        y_true=y_dev,
        scores=dev_scores,
        probabilities=dev_probabilities,
        min_sensitivity=min_sensitivity,
        positive_if_score_at_most=positive_if_score_at_most,
    )

    val_features = validation_df.drop(columns=[target_col, identifier_col, "fecha_di"])
    val_scores = experiment._score_feature_frame_with_points(pipeline=pipeline, X=val_features, points_table=points_table)
    val_probabilities = pipeline.predict_proba(val_features)[:, 1]
    selected_threshold = dev_eval.selected_threshold
    predicted_positive = val_scores <= selected_threshold if positive_if_score_at_most else val_scores >= selected_threshold
    tp = int(np.sum(predicted_positive & (y_val == 1)))
    fp = int(np.sum(predicted_positive & (y_val == 0)))
    tn = int(np.sum((~predicted_positive) & (y_val == 0)))
    fn = int(np.sum((~predicted_positive) & (y_val == 1)))
    sensitivity = tp / (tp + fn) if (tp + fn) else float("nan")
    specificity = tn / (tn + fp) if (tn + fp) else float("nan")
    ppv = tp / (tp + fp) if (tp + fp) else float("nan")
    npv = tn / (tn + fn) if (tn + fn) else float("nan")

    return TemporalValidationResult(
        strategy_name=strategy_name,
        cutoff_year=cutoff_year,
        development_n=int(len(development_df)),
        validation_n=int(len(validation_df)),
        auc=float(roc_auc_score(y_val, -val_scores if positive_if_score_at_most else val_scores)),
        brier_score=float(brier_score_loss(y_val, val_probabilities)),
        selected_threshold=float(selected_threshold),
        sensitivity=float(sensitivity),
        specificity=float(specificity),
        ppv=float(ppv),
        npv=float(npv),
        tp=tp,
        fp=fp,
        tn=tn,
        fn=fn,
    )


def _render_markdown_table(frame: pd.DataFrame, float_digits: int = 3) -> str:
    """Renders a dataframe as Markdown with stable float formatting."""
    if frame.empty:
        return "_No data available._"
    formatted = frame.copy()
    for column in formatted.columns:
        if pd.api.types.is_float_dtype(formatted[column]):
            formatted[column] = formatted[column].map(lambda value: "" if pd.isna(value) else f"{value:.{float_digits}f}")
    return formatted.to_markdown(index=False)


def generate_review_package(data_path: Path, output_dir: Path) -> Path:
    """Generates the manuscript response package and returns the Markdown path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    processor = ClinicalDataProcessor(str(data_path))
    data = processor.transform_pipeline()

    baseline_table = build_tested_vs_not_tested_table(data)
    prevalence_table = build_outcome_prevalence_table(data, OUTCOMES)
    baseline_table.to_csv(output_dir / "tested_vs_not_tested_baseline.csv", index=False)
    prevalence_table.to_csv(output_dir / "tested_outcome_prevalence.csv", index=False)

    review_sections: List[str] = [
        "# Response to Methodological Comments",
        "",
        "## 1. Target population and scope",
        "The repository data confirm that the predictive models operate within the subgroup that underwent thrombophilia testing, not the full VTE registry.",
        "",
        f"- Full registry rows: **{len(data):,}**.",
        f"- Patients with mutually exclusive `tested` status (`{SEARCHED_POSITIVE}` or `{SEARCHED_NEGATIVE}`): **{int(data['ana_dura'].astype('string').isin([SEARCHED_POSITIVE, SEARCHED_NEGATIVE]).sum()):,}**.",
        f"- Patients classified as `{NOT_SEARCHED}` after preprocessing normalization of missing study labels: **{int((data['ana_dura'].astype('string') == NOT_SEARCHED).sum()):,}**.",
        "- Consequently, all reported discrimination, calibration, and threshold metrics should be framed as the probability of a positive thrombophilia result among already selected patients, rather than the prevalence of thrombophilia among all VTE patients.",
        "",
        "### Tested vs not tested baseline comparison",
        _render_markdown_table(baseline_table, float_digits=3),
        "",
        "### Outcome prevalence among tested patients",
        _render_markdown_table(prevalence_table, float_digits=2),
        "",
        "## 2. Outcome-definition caveats",
        "- The preprocessing pipeline normalizes missing `ana_dura` values to `No buscada`, so the not-tested cohort combines explicitly unrequested and previously unlabeled thrombophilia-study rows. The repository still does not expose treatment-at-testing timestamps for heparin, VKAs, or DOACs.",
        "- The available dataset also does not document confirmatory repeat testing for antiphospholipid antibodies, so APS classification should be described as registry-defined rather than laboratory-adjudicated persistent APS.",
        "",
        "## 3. Confusion-matrix audit, calibration, and clinical utility",
    ]

    temporal_rows: List[Dict[str, object]] = []
    summary_rows: List[Dict[str, object]] = []
    calibration_frames: List[pd.DataFrame] = []

    for spec in OUTCOMES:
        if spec.column not in data.columns:
            continue
        subset = data[data[spec.column].astype("string").isin(["Sí", "No"])].copy().reset_index(drop=True)
        if subset.empty or "fecha_di" not in subset.columns:
            continue

        experiment = ClinicalRiskScoreExperiment()
        config = {
            "score_target_column": spec.column,
            "score_positive_label": "Sí",
            "score_negative_label": "No",
            "score_max_samples": len(subset),
            "score_feature_strategy": "compare",
            "score_max_feature_cardinality": 18,
            "score_numeric_bins": 6,
            "score_cv_splits": 5,
            "score_benchmark_model": "logistic",
            "score_top_features": 8,
            "score_min_sensitivity": 0.90,
            "score_xgboost_estimators": 40,
        }
        with TemporaryDirectory() as tmp_dir:
            config["output_dir"] = tmp_dir
            try:
                experiment.run(subset, config)
            except ValueError as exc:
                if "no eligible coefficients" not in str(exc).lower():
                    raise
                config["score_feature_strategy"] = "automatic"
                experiment.run(subset, config)

        profile_df = experiment.threshold_profiles_df.copy()
        profile_df.to_csv(output_dir / f"{spec.column}_threshold_audit.csv", index=False)
        review_sections.extend(
            [
                f"### {spec.label} (`{spec.column}`)",
                f"Tested binary cohort size: **{len(subset):,}**.",
                "",
                "Selected-threshold confusion matrices from the cross-validated score audit:",
                _render_markdown_table(profile_df.loc[profile_df["Selected_Threshold"]].reset_index(drop=True), float_digits=3),
                "",
            ]
        )

        for result in experiment.strategy_results:
            selected_profile = profile_df[(profile_df["Model"] == result.strategy_name) & (profile_df["Selected_Threshold"])].reset_index(drop=True)
            if selected_profile.empty:
                continue
            utility = _clinical_utility_row(selected_profile)
            summary_rows.append({"Outcome": spec.label, "Model": result.strategy_name, **utility})

        for evaluation in experiment.evaluations:
            calibration_df = _calibration_table(evaluation.y_true, evaluation.probabilities)
            calibration_df.insert(0, "Outcome", spec.label)
            calibration_df.insert(1, "Model", evaluation.model_name)
            calibration_frames.append(calibration_df)

        identifier_col = "id_pacie" if "id_pacie" in subset.columns else "sample_index"
        if identifier_col == "sample_index":
            subset = subset.copy()
            subset[identifier_col] = np.arange(len(subset))

        automatic_df = experiment._prepare_automatic_modeling_frame(
            data=subset,
            target_col=spec.column,
            positive_label="Sí",
            negative_label="No",
            max_samples=len(subset),
            max_feature_cardinality=18,
            numeric_bins=6,
        )
        automatic_df["fecha_di"] = subset.loc[automatic_df.index, "fecha_di"].to_numpy()
        temporal_rows.append(
            asdict(
                run_temporal_validation(
                    experiment=experiment,
                    model_df=automatic_df,
                    target_col=spec.column,
                    identifier_col=identifier_col,
                    positive_label="Sí",
                    strategy_name="Automatic Integer Score",
                    coefficient_direction="positive",
                    positive_if_score_at_most=False,
                    top_features=8,
                    min_sensitivity=0.90,
                    min_feature_prevalence=0.02,
                )
            )
        )

    utility_df = pd.DataFrame(summary_rows)
    temporal_df = pd.DataFrame(temporal_rows)
    calibration_df = pd.concat(calibration_frames, ignore_index=True) if calibration_frames else pd.DataFrame()

    utility_df.to_csv(output_dir / "score_clinical_utility_summary.csv", index=False)
    temporal_df.to_csv(output_dir / "temporal_validation_summary.csv", index=False)
    calibration_df.to_csv(output_dir / "calibration_summary.csv", index=False)

    if not utility_df.empty:
        review_sections.extend(
            [
                "### Threshold-derived clinical utility",
                "The table below translates high NPV operating points into more interpretable resource terms: how many tests might be avoided per 1,000 tested patients, and how many true positives would be missed.",
                "",
                _render_markdown_table(utility_df, float_digits=2),
                "",
            ]
        )

    if not temporal_df.empty:
        review_sections.extend(
            [
                "## 4. Temporal validation",
                "A temporal split was feasible because diagnosis dates are present in the repository (`fecha_di`, years 2001-2024). The holdout threshold was fixed from the development era and then applied unchanged to later years.",
                "",
                _render_markdown_table(temporal_df, float_digits=3),
                "",
                "No country or center variable was available in the local parquet inspected here, so leave-country or leave-center internal-external validation could not be reproduced from the current repository snapshot.",
                "",
            ]
        )

    if not calibration_df.empty:
        calibration_plot = px.line(
            calibration_df,
            x="Predicted_Probability",
            y="Observed_Frequency",
            color="Outcome",
            line_dash="Model",
            title="Cross-validated calibration by outcome and model",
            markers=True,
        )
        calibration_plot.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line={"dash": "dash", "color": "black"})
        calibration_html = output_dir / "calibration_overview.html"
        calibration_plot.write_html(str(calibration_html), include_plotlyjs="cdn")
        brier_summary = calibration_df.groupby(["Outcome", "Model"], as_index=False)["Absolute_Error"].mean().rename(columns={"Absolute_Error": "Mean_Absolute_Calibration_Error"})
        review_sections.extend(
            [
                "## 5. Calibration",
                "The current repository already mentioned calibration and Brier-style performance in Methods, but these results were not surfaced clearly. The generated calibration tables and plot now make that gap explicit.",
                "",
                _render_markdown_table(brier_summary, float_digits=3),
                "",
                f"Interactive calibration plot: `{calibration_html.name}`.",
                "",
            ]
        )

    review_sections.extend(
        [
            "## 6. Interpretation of simplified score cut-points",
            "- The present automatic score still derives several intervals from data-driven quantile binning. That makes narrow leukocyte, hemoglobin, D-dimer, or age bands possible even when their clinical meaning is weak.",
            "- For manuscript reporting, those cut-points should therefore be described as sample-derived screening heuristics requiring external validation, not as stable biological thresholds.",
            "",
            "## 7. Recommended wording changes for the manuscript",
            "1. Replace any wording that implies prediction in the whole VTE cohort with wording restricted to patients already selected for thrombophilia work-up.",
            "2. Define each outcome as a registry-coded post-thrombosis thrombophilia result and state explicitly which laboratory adjudications were unavailable.",
            "3. Prefer mutually exclusive baseline groups (`tested` vs `not tested`) and emphasize standardized differences instead of p-values.",
            "4. Report TP/FP/TN/FN, calibration, and the practical yield per 1,000 tested patients alongside NPV.",
        ]
    )

    report_path = output_dir / "coauthor_response_review.md"
    report_path.write_text("\n".join(review_sections), encoding="utf-8")
    return report_path


def main() -> None:
    """CLI entry point for building the manuscript review package."""
    parser = argparse.ArgumentParser(description="Generate manuscript-support audit outputs for thrombophilia models.")
    parser.add_argument("--data", type=Path, default=Path("data/patD.parquet"), help="Path to the main clinical dataset.")
    parser.add_argument("--output-dir", type=Path, default=Path("out"), help="Directory where audit outputs will be written.")
    args = parser.parse_args()
    report_path = generate_review_package(data_path=args.data, output_dir=args.output_dir)
    print(f"Manuscript review package written to {report_path}")


if __name__ == "__main__":
    main()
