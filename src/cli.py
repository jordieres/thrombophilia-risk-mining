import argparse
import sys
from data_processor import ClinicalDataProcessor
from exp_permutation_importance import PermutationImportanceExperiment
from exp_contrast_mining import ContrastPatternMiningExperiment
from exp_unsupervised_clustering import UnsupervisedClusteringExperiment
from exp_bayesian_networks import BayesianNetworkExperiment

def main():
    """Main CLI execution routing interface for managing running research blocks."""
    parser = argparse.ArgumentParser(description="Unified Execution CLI Layer for National Thrombophilia Analysis Suite")
    parser.add_argument('--data', type=str, required=True, help="Path to input database spreadsheet raw matrix")
    parser.add_argument('--experiment', type=str, required=True, choices=['permutation', 'contrast', 'clustering', 'bayesian', 'all'],
                        help="Specific modular machine learning experiment to compute")
    
    args = parser.parse_args()
    
    print(f"Executing systemic data pipeline over target: {args.data}")
    processor = ClinicalDataProcessor(args.data)
    processor.load_data()
    processed_df = processor.transform_pipeline()
    
    # Establish experimental registry allocation mapping
    experiment_registry = {
        'permutation': PermutationImportanceExperiment(),
        'contrast': ContrastPatternMiningExperiment(),
        'clustering': UnsupervisedClusteringExperiment(),
        'bayesian': BayesianNetworkExperiment()
    }
    
    target_experiments = []
    if args.experiment == 'all':
        target_experiments = list(experiment_registry.values())
    else:
        target_experiments = [experiment_registry[args.experiment]]
        
    for experiment in target_experiments:
        print(f"\nLaunching Analytical Module Target: {experiment.name}")
        experiment.run(processed_df)
        
        # Save output structures on the disk system
        html_output = f"output_chart_{experiment.name.lower().replace(' ', '_')}.html"
        experiment.save_interactive_plot(html_output)
        print(f"Interactive Plotly chart successfully written to {html_output}")
        
        print("\nGenerated LaTeX Structural Table (Booktabs Specification):")
        print(experiment.export_latex())

if __name__ == "__main__":
    main()
