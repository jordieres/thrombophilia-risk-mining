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
from typing import Dict, Any, List

# Suppress deprecation and future warnings from third-party libraries globally
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)

from data_processor import ClinicalDataProcessor


def build_experiment_registry(selected_experiment: str) -> Dict[str, Any]:
    """Builds only the experiment objects required for the current CLI request."""
    registry: Dict[str, Any] = {}

    if selected_experiment in {'permutation', 'all'}:
        from exp_permutation_importance import PermutationImportanceExperiment

        registry['permutation'] = PermutationImportanceExperiment()

    if selected_experiment in {'contrast', 'all'}:
        from exp_contrast_mining import ContrastPatternMiningExperiment

        registry['contrast'] = ContrastPatternMiningExperiment()

    if selected_experiment in {'clustering', 'all'}:
        from exp_unsupervised_clustering import UnsupervisedClusteringExperiment

        registry['clustering'] = UnsupervisedClusteringExperiment()

    if selected_experiment in {'bayesian', 'all'}:
        from exp_bayesian_networks import BayesianNetworkExperiment

        registry['bayesian'] = BayesianNetworkExperiment()

    return registry


def main() -> None:
    """Main CLI execution router managing running configurations and research loops."""
    parser = argparse.ArgumentParser(description="Unified Execution CLI Layer for National Thrombophilia Analysis Suite")
    parser.add_argument('--data', type=str, required=True, help="Path to input database matrix (Parquet or Excel)")
    parser.add_argument('--experiment', type=str, required=True, choices=['permutation', 'contrast', 'clustering', 'bayesian', 'all'])

    # Execution optimization parameters
    parser.add_argument('--permutation-max-samples', type=int, default=2000)
    parser.add_argument('--permutation-max-splits', type=int, default=2)
    parser.add_argument('--permutation-repeats', type=int, default=1)
    parser.add_argument('--permutation-estimators', type=int, default=10)
    parser.add_argument('--contrast-max-samples', type=int, default=300)
    parser.add_argument('--contrast-min-support', type=float, default=0.05)
    parser.add_argument('--contrast-min-confidence', type=float, default=0.4)
    parser.add_argument('--contrast-max-feature-cardinality', type=int, default=12)
    parser.add_argument('--contrast-max-features', type=int, default=48)
    parser.add_argument('--contrast-max-rule-size', type=int, default=3)
    parser.add_argument('--contrast-top-k-per-outcome', type=int, default=5)
    parser.add_argument('--contrast-workers', type=int, default=2)
    parser.add_argument('--clustering-max-samples', type=int, default=1000)
    parser.add_argument('--output-dir', type=str, default='.')
    parser.add_argument('--checkpoint-dir', type=str, default='out/checkpoints')
    parser.add_argument('--resume', action='store_true', help="Reuse completed checkpoints for resumable experiment execution")

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

    target_experiments: List[Any] = []
    if args.experiment == 'all':
        target_experiments = list(experiment_registry.values())
    else:
        target_experiments = [experiment_registry[args.experiment]]

    for experiment in target_experiments:
        print(f"\nLaunching Analytical Module Target: {experiment.name}")
        experiment.run(processed_df, config)

        html_output: str = str(output_dir / f"output_chart_{experiment.name.lower().replace(' ', '_')}.html")
        experiment.save_interactive_plot(html_output)
        print(f"Interactive Plotly chart successfully written to {html_output}")

        print("\nGenerated LaTeX Structural Table (Booktabs Specification):")
        print(experiment.export_latex())


if __name__ == "__main__":
    main()
