# Comprehensive Data Mining and Machine Learning Workflows for Thrombophilia Risk Stratification

This repository houses an advanced, object-oriented framework engineered to deconstruct hypercoagulable risk factors utilizing a consolidated national database for thrombophilic disease. The central computational objective centers on identifying, explaining, and predicting the specific sets of clinical and demographic features that culminate in a confirmed diagnostic rule exclusion, formally designated as the searched negative class.

By combining unsupervised transactional pattern discovery with robust gradient-boosted tree architectures, this project isolates complex non-linear clinical markers. To address systemic over-screening in low-risk populations, the framework provides four distinct analytical modules driven by a unified command-line interface.

## Core Analytical Architecture

The source code is organized into decoupled, independent operational layers to ensure rigorous statistical isolation and code maintainability:

1. Permutation Importance Engine: An analytical module designed to isolate secondary laboratory variables by systematically stripping dominant sociodemographic signals (age and gender), forcing the underlying gradient boosting architecture to map subtle clinical interactions.
2. Contrast Pattern Miner: A pipeline built to mathematically formalize the descriptive discrepancies between positive and negative screening markers, isolating boundaries where baseline phenotypes transition into active hypercoagulable states.
3. Unsupervised Clustering Engine: A dimensional reduction and grouping pipeline operating via t-SNE and hierarchical clustering to surface latent phenotypic patient archetypes without prior exposure to target classes.
4. Probabilistic Bayesian Network: A graphical causal framework structured to model conditional dependencies and directional medical risk flows across discrete patient characteristics.

## Getting Started

### Installation Protocols

Begin by cloning the source repository and establishing a clean virtual execution environment to install the required dependency tree:

```bash
git clone [https://github.com/username/thrombophilia-risk-mining.git](https://github.com/username/thrombophilia-risk-mining.git)
cd thrombophilia-risk-mining
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Command Line Execution
The execution interface is governed by a unified command-line architecture. Users can trigger individual research experiments or run the entire suite sequentially using specific terminal arguments:

```bash
# Run the baseline processing and the permutation importance pipeline using a Parquet source
python src/cli.py --data data/dataset.parquet --experiment permutation

# Run the contrast pattern extraction framework over an Excel sheet
python src/cli.py --data data/dataset.xlsx --experiment contrast

# Execute all four analytical experiments sequentially using Parquet
python src/cli.py --data data/dataset.parquet --experiment all

```

## Output Artifacts
Every completed experiment generates two complementary output formats:

* Publication-Ready LaTeX Tables: Formatted structures utilizing the booktabs standard to summarize stable performance parameters.

* Interactive Plotly Visualizations: Dynamic standalone HTML charts providing deep analytical cross-examinations of clinical boundaries.


