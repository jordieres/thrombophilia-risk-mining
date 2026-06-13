"""Command-line interface for the thrombophilia risk mining toolkit.

The CLI orchestrates three major concerns:

* shared dataset loading and preprocessing,
* experiment-specific runtime configuration,
* export of LaTeX and interactive HTML artifacts.
"""

# Suppress deprecation and future warnings from third-party libraries globally
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=SyntaxWarning)


from __future__ import annotations
import argparse
import sys
from typing import Dict, Any, List
from data_processor import ClinicalDataProcessor
from exp_permutation_importance import PermutationImportanceExperiment
from exp_contrast_mining import ContrastPatternMiningExperiment
from exp_unsupervised_clustering import UnsupervisedClusteringExperiment
from exp_bayesian_networks import BayesianNetworkExperiment

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
    parser.add_argument('--clustering-max-samples', type=int, default=1000)

    args = parser.parse_args()
    config: Dict[str, Any] = vars(args)

    print(f"Executing systemic data pipeline over target: {args.data}")
    processor: ClinicalDataProcessor = ClinicalDataProcessor(args.data)
    processor.load_data()
    processed_df = processor.transform_pipeline()

    experiment_registry: Dict[str, Any] = {
        'permutation': PermutationImportanceExperiment(),
        'contrast': ContrastPatternMiningExperiment(),
        'clustering': UnsupervisedClusteringExperiment(),
        'bayesian': BayesianNetworkExperiment()
    }

    target_experiments: List[Any] = []
    if args.experiment == 'all':
        target_experiments = list(experiment_registry.values())
    else:
        target_experiments = [experiment_registry[args.experiment]]

    for experiment in target_experiments:
        print(f"\nLaunching Analytical Module Target: {experiment.name}")
        experiment.run(processed_df, config)

        html_output: str = f"output_chart_{experiment.name.lower().replace(' ', '_')}.html"
        experiment.save_interactive_plot(html_output)
        print(f"Interactive Plotly chart successfully written to {html_output}")

        print("\nGenerated LaTeX Structural Table (Booktabs Specification):")
        print(experiment.export_latex())

if __name__ == "__main__":
    main()
