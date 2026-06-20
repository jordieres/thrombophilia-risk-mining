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

# Suppress deprecation and future warnings from third-party libraries globally.
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

from data_processor import ClinicalDataProcessor


CLUSTERING_METRICS: List[str] = ["euclidean", "manhattan", "cosine", "chebyshev"]
SCORE_BENCHMARK_MODELS: List[str] = ["logistic", "xgboost", "both"]
SCORE_FEATURE_STRATEGIES: List[str] = ["automatic", "association", "compare"]


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

    if selected_experiment in {"bayesian", "all"}:
        from exp_bayesian_networks import BayesianNetworkExperiment

        registry["bayesian"] = BayesianNetworkExperiment()

    if selected_experiment in {"score", "all"}:
        from exp_clinical_risk_score import ClinicalRiskScoreExperiment

        registry["score"] = ClinicalRiskScoreExperiment()

    return registry


def main() -> None:
    """Main CLI execution router managing running configurations and research loops."""
    parser = argparse.ArgumentParser(description="Unified Execution CLI Layer for National Thrombophilia Analysis Suite")
    parser.add_argument("--data", type=str, required=True, help="Path to input database matrix (Parquet or Excel)")
    parser.add_argument(
        "--experiment",
        type=str,
        required=True,
        choices=["permutation", "contrast", "clustering", "bayesian", "score", "all"],
    )

    # Execution optimization parameters.
    parser.add_argument("--permutation-max-samples", type=int, default=2000)
    parser.add_argument("--permutation-max-splits", type=int, default=2)
    parser.add_argument("--permutation-repeats", type=int, default=1)
    parser.add_argument("--permutation-estimators", type=int, default=10)

    parser.add_argument("--contrast-max-samples", type=int, default=300)
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
    parser.add_argument("--score-xgboost-estimators", type=int, default=80)

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
