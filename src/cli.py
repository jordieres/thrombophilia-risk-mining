"""Command-line interface for the thrombophilia risk mining toolkit.

The CLI orchestrates three major concerns:

* shared dataset loading and preprocessing,
* experiment-specific runtime configuration,
* export of LaTeX and interactive HTML artifacts.
"""

from __future__ import annotations

import argparse
from typing import Final

from data_processor import ClinicalDataProcessor
from exp_bayesian_networks import BayesianNetworkExperiment
from exp_contrast_mining import ContrastPatternMiningExperiment
from exp_permutation_importance import PermutationImportanceExperiment
from exp_unsupervised_clustering import UnsupervisedClusteringExperiment
from experiment_base import BaseExperiment

EXPERIMENT_CHOICES: Final[tuple[str, ...]] = (
    "permutation",
    "contrast",
    "clustering",
    "bayesian",
    "all",
)


def positive_int(value: str) -> int:
    """Parse an integer CLI argument that must be strictly positive.

    Args:
        value: Raw string passed by ``argparse``.

    Returns:
        Parsed positive integer.

    Raises:
        argparse.ArgumentTypeError: If the provided value is not positive.
    """
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("Expected a strictly positive integer.")
    return parsed


def positive_float(value: str) -> float:
    """Parse a float CLI argument that must be strictly positive.

    Args:
        value: Raw string passed by ``argparse``.

    Returns:
        Parsed positive float.

    Raises:
        argparse.ArgumentTypeError: If the provided value is not positive.
    """
    parsed = float(value)
    if parsed <= 0.0:
        raise argparse.ArgumentTypeError("Expected a strictly positive float.")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser.

    Returns:
        Fully configured argument parser for the project entry point.
    """
    parser = argparse.ArgumentParser(
        description="Unified execution CLI for the thrombophilia analysis suite."
    )
    parser.add_argument(
        "--data",
        type=str,
        required=True,
        help="Path to the input CSV, Excel, or Parquet dataset.",
    )
    parser.add_argument(
        "--experiment",
        type=str,
        required=True,
        choices=EXPERIMENT_CHOICES,
        help="Experiment to execute or 'all' to run the full suite.",
    )

    parser.add_argument(
        "--permutation-max-samples",
        type=positive_int,
        default=PermutationImportanceExperiment.DEFAULT_MAX_SAMPLES,
        help="Maximum number of rows used by permutation importance.",
    )
    parser.add_argument(
        "--permutation-max-splits",
        type=positive_int,
        default=PermutationImportanceExperiment.DEFAULT_MAX_SPLITS,
        help="Upper bound for stratified cross-validation folds.",
    )
    parser.add_argument(
        "--permutation-repeats",
        type=positive_int,
        default=PermutationImportanceExperiment.DEFAULT_N_REPEATS,
        help="Number of permutation repeats per validation fold.",
    )
    parser.add_argument(
        "--permutation-estimators",
        type=positive_int,
        default=PermutationImportanceExperiment.DEFAULT_N_ESTIMATORS,
        help="Number of trees in the XGBoost classifier.",
    )

    parser.add_argument(
        "--contrast-max-samples",
        type=positive_int,
        default=ContrastPatternMiningExperiment.DEFAULT_MAX_SAMPLES,
        help="Maximum number of rows sampled for contrast mining.",
    )
    parser.add_argument(
        "--contrast-min-support",
        type=positive_float,
        default=ContrastPatternMiningExperiment.DEFAULT_MIN_SUPPORT,
        help="Minimum support threshold used by FP-growth.",
    )
    parser.add_argument(
        "--contrast-max-features",
        type=positive_int,
        default=ContrastPatternMiningExperiment.DEFAULT_MAX_FEATURES,
        help="Maximum number of categorical features included in rule mining.",
    )
    parser.add_argument(
        "--contrast-max-cardinality",
        type=positive_int,
        default=ContrastPatternMiningExperiment.DEFAULT_MAX_CARDINALITY,
        help="Upper bound for categorical feature cardinality in contrast mining.",
    )

    parser.add_argument(
        "--clustering-max-samples",
        type=positive_int,
        default=UnsupervisedClusteringExperiment.DEFAULT_MAX_SAMPLES,
        help="Maximum number of rows passed to the clustering experiment.",
    )
    parser.add_argument(
        "--clustering-clusters",
        type=positive_int,
        default=UnsupervisedClusteringExperiment.DEFAULT_N_CLUSTERS,
        help="Requested number of agglomerative clusters.",
    )
    parser.add_argument(
        "--clustering-max-perplexity",
        type=positive_int,
        default=UnsupervisedClusteringExperiment.DEFAULT_MAX_PERPLEXITY,
        help="Upper bound for the t-SNE perplexity parameter.",
    )
    return parser


def build_experiment_registry(args: argparse.Namespace) -> dict[str, BaseExperiment]:
    """Instantiate the experiments requested by the CLI.

    Args:
        args: Parsed CLI arguments.

    Returns:
        Mapping from experiment key to configured experiment instance.
    """
    return {
        "permutation": PermutationImportanceExperiment(
            max_samples=args.permutation_max_samples,
            max_splits=args.permutation_max_splits,
            n_repeats=args.permutation_repeats,
            n_estimators=args.permutation_estimators,
        ),
        "contrast": ContrastPatternMiningExperiment(
            max_samples=args.contrast_max_samples,
            min_support=args.contrast_min_support,
            max_features=args.contrast_max_features,
            max_cardinality=args.contrast_max_cardinality,
        ),
        "clustering": UnsupervisedClusteringExperiment(
            max_samples=args.clustering_max_samples,
            n_clusters=args.clustering_clusters,
            max_perplexity=args.clustering_max_perplexity,
        ),
        "bayesian": BayesianNetworkExperiment(),
    }


def main() -> None:
    """Run the CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    print(f"Executing systemic data pipeline over target: {args.data}")
    processor = ClinicalDataProcessor(args.data)
    processor.load_data()
    processed_df = processor.transform_pipeline()

    experiment_registry = build_experiment_registry(args)
    target_experiments = (
        list(experiment_registry.values())
        if args.experiment == "all"
        else [experiment_registry[args.experiment]]
    )

    for experiment in target_experiments:
        print()
        print(f"Launching Analytical Module Target: {experiment.name}")
        experiment.run(processed_df)

        html_output = f"output_chart_{experiment.name.lower().replace(' ', '_')}.html"
        experiment.save_interactive_plot(html_output)
        print(f"Interactive Plotly chart successfully written to {html_output}")

        print()
        print("Generated LaTeX Structural Table (Booktabs Specification):")
        print(experiment.export_latex())


if __name__ == "__main__":
    main()
