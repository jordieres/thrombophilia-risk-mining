"""Command-line interface for the thrombophilia risk mining toolkit.

The CLI orchestrates three major concerns:

* shared dataset loading and preprocessing,
* experiment-specific runtime configuration,
* export of LaTeX and interactive HTML artifacts.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import warnings
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import plotly.express as px

# Suppress deprecation and future warnings from third-party libraries globally.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

from data_processor import ClinicalDataProcessor


CLUSTERING_METRICS: List[str] = ["euclidean", "manhattan", "cosine", "chebyshev"]
SCORE_BENCHMARK_MODELS: List[str] = ["logistic", "xgboost", "both"]
SCORE_FEATURE_STRATEGIES: List[str] = ["automatic", "association", "compare"]


def _resolve_column_name(df: pd.DataFrame, requested_column: str) -> str:
    """Resolves a dataframe column name with a light case-insensitive fallback."""
    if requested_column in df.columns:
        return requested_column

    lowered_map: Dict[str, str] = {str(column).casefold(): str(column) for column in df.columns}
    resolved_column: str | None = lowered_map.get(requested_column.casefold())
    if resolved_column is None:
        available_columns: str = ", ".join(map(str, df.columns))
        raise ValueError(
            f"The requested EDAS column '{requested_column}' was not found. "
            f"Available columns: {available_columns}"
        )
    return resolved_column


def run_edas_analysis(data: pd.DataFrame, config: Dict[str, Any], output_dir: Path) -> None:
    """Generates descriptive EDAS artifacts for a selected numeric clinical variable."""
    requested_column: str = str(config.get("edas_column", "DimeroD"))
    analysis_mode: str = str(config.get("edas_analysis", "both"))
    histogram_bins: int = int(config.get("edas_bins", 10))
    range_min: float | None = config.get("edas_range_min")
    range_max: float | None = config.get("edas_range_max")

    column_name: str = _resolve_column_name(data, requested_column)
    series: pd.Series = pd.to_numeric(data[column_name], errors="coerce").dropna()
    if series.empty:
        raise ValueError(f"EDAS analysis found no numeric non-null values in column '{column_name}'.")

    if range_min is not None:
        range_min = float(range_min)
    if range_max is not None:
        range_max = float(range_max)
    if range_min is not None and range_max is not None and range_min >= range_max:
        raise ValueError("EDAS histogram range requires --edas-range-min to be smaller than --edas-range-max.")

    safe_column_stem: str = column_name.lower().replace(" ", "_")

    if analysis_mode in {"stats", "both"}:
        stats_df: pd.DataFrame = pd.DataFrame(
            [
                {
                    "column": column_name,
                    "count": int(series.count()),
                    "min": float(series.min()),
                    "q1": float(series.quantile(0.25)),
                    "median": float(series.median()),
                    "q3": float(series.quantile(0.75)),
                    "max": float(series.max()),
                }
            ]
        )
        stats_output: Path = output_dir / f"edas_{safe_column_stem}_stats.csv"
        stats_df.to_csv(stats_output, index=False)
        print("\nEDAS descriptive statistics:")
        print(stats_df.to_string(index=False))
        print(f"EDAS statistics saved to {stats_output}")

    if analysis_mode in {"histogram", "both"}:
        in_range_mask: pd.Series = pd.Series(True, index=series.index)
        if range_min is not None:
            in_range_mask &= series >= range_min
        if range_max is not None:
            in_range_mask &= series <= range_max

        filtered_series: pd.Series = series[in_range_mask]
        below_range_count: int = int((series < range_min).sum()) if range_min is not None else 0
        above_range_count: int = int((series > range_max).sum()) if range_max is not None else 0

        if filtered_series.empty:
            raise ValueError(
                "EDAS histogram range excluded all rows. Adjust --edas-range-min/--edas-range-max."
            )

        counts, bin_edges = np.histogram(filtered_series.to_numpy(), bins=histogram_bins)
        histogram_df: pd.DataFrame = pd.DataFrame(
            {
                "bin_start": bin_edges[:-1],
                "bin_end": bin_edges[1:],
                "count": counts,
            }
        )
        histogram_df["n_below_range"] = below_range_count
        histogram_df["n_above_range"] = above_range_count

        histogram_summary_df: pd.DataFrame = pd.DataFrame(
            [
                {
                    "column": column_name,
                    "range_min": range_min,
                    "range_max": range_max,
                    "n_total": int(series.count()),
                    "n_in_range": int(filtered_series.count()),
                    "n_below_range": below_range_count,
                    "n_above_range": above_range_count,
                }
            ]
        )
        histogram_output: Path = output_dir / f"edas_{safe_column_stem}_histogram.csv"
        histogram_summary_output: Path = output_dir / f"edas_{safe_column_stem}_histogram_summary.csv"
        histogram_df.to_csv(histogram_output, index=False)
        histogram_summary_df.to_csv(histogram_summary_output, index=False)

        figure = px.histogram(
            x=filtered_series,
            nbins=histogram_bins,
            title=f"EDAS Histogram for {column_name}",
            labels={"x": column_name, "y": "Count"},
        )
        if range_min is not None or range_max is not None:
            figure.update_xaxes(range=[range_min, range_max])
        html_output: Path = output_dir / f"edas_{safe_column_stem}_histogram.html"
        figure.write_html(str(html_output), include_plotlyjs="cdn")

        print("\nEDAS histogram range summary:")
        print(histogram_summary_df.to_string(index=False))
        print("\nEDAS histogram bins:")
        print(histogram_df.to_string(index=False))
        print(f"EDAS histogram bins saved to {histogram_output}")
        print(f"EDAS histogram summary saved to {histogram_summary_output}")
        print(f"EDAS histogram chart saved to {html_output}")


def build_experiment_registry(selected_experiment: str) -> Dict[str, Any]:
    """Builds only the experiment objects required for the current CLI request."""
    registry: Dict[str, Any] = {}

    if selected_experiment in {"permutation", "all"}:
        from exp_permutation_importance import PermutationImportanceExperiment

        registry["permutation"] = PermutationImportanceExperiment()

    if selected_experiment in {"contrast", "all"}:
        from exp_contrast_mining import ContrastPatternMiningExperiment

        registry["contrast"] = ContrastPatternMiningExperiment()

    if selected_experiment in {"clustering", "all"}:
        from exp_unsupervised_clustering import UnsupervisedClusteringExperiment

        registry["clustering"] = UnsupervisedClusteringExperiment()

    if selected_experiment in {"categorical_association", "all"}:
        from exp_categorical_association import CategoricalAssociationExperiment

        registry["categorical_association"] = CategoricalAssociationExperiment()

    if selected_experiment in {"association_explorer", "all"}:
        from exp_association_explorer import AssociationExplorerExperiment

        registry["association_explorer"] = AssociationExplorerExperiment()

    if selected_experiment in {"bayesian", "all"}:
        from exp_bayesian_networks import BayesianNetworkExperiment

        registry["bayesian"] = BayesianNetworkExperiment()

    if selected_experiment in {"score", "all"}:
        from exp_clinical_risk_score import ClinicalRiskScoreExperiment

        registry["score"] = ClinicalRiskScoreExperiment()

    if selected_experiment in {"score_screening", "all"}:
        from exp_score_screening import ClinicalScoreScreeningExperiment

        registry["score_screening"] = ClinicalScoreScreeningExperiment()

    return registry


def main() -> None:
    """Main CLI execution router managing running configurations and research loops."""
    parser = argparse.ArgumentParser(description="Unified Execution CLI Layer for National Thrombophilia Analysis Suite")
    parser.add_argument("--data", type=str, required=True, help="Path to input database matrix (Parquet or Excel)")
    parser.add_argument(
        "--experiment",
        type=str,
        required=True,
        choices=["permutation", "contrast", "clustering", "categorical_association", "association_explorer", "bayesian", "score", "score_screening", "edas", "all"],
    )

    # Execution optimization parameters.
    parser.add_argument("--permutation-max-samples", type=int, default=2000)
    parser.add_argument("--permutation-max-splits", type=int, default=2)
    parser.add_argument("--permutation-repeats", type=int, default=1)
    parser.add_argument("--permutation-estimators", type=int, default=10)
    parser.add_argument("--permutation-target-column", type=str, default="ana_dura")
    parser.add_argument("--permutation-positive-label", type=str, default="Buscada negativo")
    parser.add_argument("--permutation-negative-label", type=str, default="Buscada positivo")

    parser.add_argument("--contrast-max-samples", type=int, default=300)
    parser.add_argument("--contrast-target-column", type=str, default="ana_dura")
    parser.add_argument("--contrast-target-valid-labels", nargs="*", default=[])
    parser.add_argument("--contrast-min-support", type=float, default=0.05)
    parser.add_argument("--contrast-min-confidence", type=float, default=0.4)
    parser.add_argument("--contrast-max-feature-cardinality", type=int, default=12)
    parser.add_argument("--contrast-max-features", type=int, default=48)
    parser.add_argument("--contrast-max-rule-size", type=int, default=3)
    parser.add_argument("--contrast-top-k-per-outcome", type=int, default=5)
    parser.add_argument("--contrast-workers", type=int, default=2)

    parser.add_argument("--clustering-max-samples", type=int, default=1000)
    parser.add_argument(
        "--clustering-metric",
        type=str,
        default="manhattan",
        choices=CLUSTERING_METRICS,
        help="Distance metric used for hierarchical clustering and UMAP embedding.",
    )
    parser.add_argument("--clustering-n-clusters", type=int, default=3)
    parser.add_argument("--clustering-n-neighbors", type=int, default=15)
    parser.add_argument("--clustering-min-dist", type=float, default=0.1)
    parser.add_argument(
        "--clustering-color-rules-json",
        type=str,
        default=None,
        help="Optional JSON file with rule-based color labels for exported and plotted UMAP points.",
    )

    parser.add_argument("--association-max-samples", type=int, default=5000)
    parser.add_argument("--association-max-columns", type=int, default=20)
    parser.add_argument("--association-top-k", type=int, default=20)
    parser.add_argument("--association-include-target", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--association-target-column", type=str, default="ana_dura")
    parser.add_argument("--association-target-valid-labels", nargs="*", default=[])

    parser.add_argument("--association-rules-max-samples", type=int, default=5000)
    parser.add_argument("--association-rules-min-support", type=float, default=0.01)
    parser.add_argument("--association-rules-min-confidence", type=float, default=0.4)
    parser.add_argument("--association-rules-min-lift", type=float, default=1.0)
    parser.add_argument("--association-rules-max-feature-cardinality", type=int, default=12)
    parser.add_argument("--association-rules-max-features", type=int, default=24)
    parser.add_argument("--association-rules-max-rule-size", type=int, default=3)
    parser.add_argument("--association-rules-top-k", type=int, default=30)
    parser.add_argument("--association-rules-sort-metric", type=str, default="leverage", choices=["leverage", "lift", "confidence", "support"])
    parser.add_argument("--association-rules-filter-column", type=str, default=None)
    parser.add_argument("--association-rules-filter-side", type=str, default="either", choices=["either", "antecedent", "consequent"])
    parser.add_argument("--association-rules-target-column", type=str, default=None)
    parser.add_argument("--association-rules-target-valid-labels", nargs="*", default=[])

    parser.add_argument("--bayesian-target-column", type=str, default="ana_dura")
    parser.add_argument("--bayesian-group-column", type=str, default="sexo")
    parser.add_argument("--bayesian-target-valid-labels", nargs="*", default=[])

    parser.add_argument("--score-target-column", type=str, default="ana_dura")
    parser.add_argument("--score-positive-label", type=str, default="Buscada positivo")
    parser.add_argument("--score-negative-label", type=str, default="Buscada negativo")
    parser.add_argument("--score-max-samples", type=int, default=4000)
    parser.add_argument("--score-max-feature-cardinality", type=int, default=12)
    parser.add_argument("--score-feature-strategy", type=str, default="automatic", choices=SCORE_FEATURE_STRATEGIES)
    parser.add_argument("--score-cv-splits", type=int, default=5)
    parser.add_argument(
        "--score-benchmark-model",
        type=str,
        default="both",
        choices=SCORE_BENCHMARK_MODELS,
        help="Model family used to benchmark the clinical integer-score ROC performance.",
    )
    parser.add_argument("--score-top-features", type=int, default=12)
    parser.add_argument("--score-numeric-bins", type=int, default=4)
    parser.add_argument("--score-min-sensitivity", type=float, default=0.90)
    parser.add_argument("--score-min-feature-prevalence", type=float, default=0.02)
    parser.add_argument("--score-xgboost-estimators", type=int, default=80)
    parser.add_argument("--screening-labels", nargs="*", default=["Missing", "No buscada"])

    parser.add_argument("--edas-column", type=str, default="DimeroD")
    parser.add_argument(
        "--edas-analysis",
        type=str,
        default="both",
        choices=["histogram", "stats", "both"],
        help="EDAS output mode for the selected variable.",
    )
    parser.add_argument("--edas-bins", type=int, default=10, help="Number of bins used in the EDAS histogram.")
    parser.add_argument("--edas-range-min", type=float, default=None, help="Lower bound included in the EDAS histogram.")
    parser.add_argument("--edas-range-max", type=float, default=None, help="Upper bound included in the EDAS histogram.")

    parser.add_argument("--output-dir", type=str, default=".")
    parser.add_argument("--checkpoint-dir", type=str, default="out/checkpoints")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse completed checkpoints for resumable experiment execution",
    )

    args = parser.parse_args()
    config: Dict[str, Any] = vars(args)

    output_dir: Path = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    Path(args.checkpoint_dir).mkdir(parents=True, exist_ok=True)

    print(f"Executing systemic data pipeline over target: {args.data}")
    processor: ClinicalDataProcessor = ClinicalDataProcessor(args.data)
    processor.load_data()
    processed_df = processor.transform_pipeline()

    if args.experiment == "edas":
        run_edas_analysis(processed_df, config, output_dir)
        return

    experiment_registry: Dict[str, Any] = build_experiment_registry(args.experiment)

    if args.experiment == "all":
        target_experiments: List[Any] = list(experiment_registry.values())
    else:
        target_experiments = [experiment_registry[args.experiment]]

    for experiment in target_experiments:
        print(f"\nLaunching Analytical Module Target: {experiment.name}")
        experiment.run(processed_df, config)

        html_output = output_dir / f"output_chart_{experiment.name.lower().replace(' ', '_')}.html"
        experiment.save_interactive_plot(str(html_output))
        print(f"Interactive Plotly chart successfully written to {html_output}")

        print("\nGenerated LaTeX Structural Table (Booktabs Specification):")
        print(experiment.export_latex())


if __name__ == "__main__":
    main()
