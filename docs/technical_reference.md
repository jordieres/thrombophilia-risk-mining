# Thrombophilia Risk Mining Suite: Technical Reference Manual

This document provides a comprehensive technical overview of the architectural pipelines, behavioral contracts, and runtime execution sequences that govern the thrombophilia risk stratification software. The system is engineered around an object-oriented paradigm using strict typing and modular encapsulation to separate high-performance data ingestion from mathematical validation frameworks.

## Behavioral and Interaction Specifications

The operational lifecycle of the system is governed by a series of structured state transitions and execution workflows. The application transitions through deterministic stages starting from initial parameter parsing inside the command line interface to data-frame splitting and downstream algorithmic evaluation.

### Runtime Use Case Interactions

The core functional capabilities of the package are exposed to the clinical investigator through a single entry point managed by the Poetry environment. The primary use cases include multi-format dataset ingestion, demographic isolation using gradient boosted trees, sex-stratified contrast rule discovery, unsupervised phenotypic cluster mapping, and causal inference tracking through Bayesian networks. The execution engine enforces that all experimental sub-modules share a unified reporting interface, which automates the export of standalone HTML graphics and publication-ready LaTeX tables.

### Control Flow and Activity Sequences

When a command is submitted via the command-line driver, the software initializes an orchestration context that validates the underlying data integrity before allocating system resources. The ingestion layer determines the file extension on disk, parsing compressed binary tables via the PyArrow vectorization layer or fall-back spreadsheet structures into standardized pandas matrices. Once the dataframe is stored in memory, categorical variables are cleaned, missing historical records are defensively imputed as non-present, and laboratory features are categorized into discrete clinical bins to prevent information leakage.

Following this preprocessing stage, control is routed to the target experiment instances registered within the deployment matrix. Each active module executes its specialized mathematical routing independently inside a isolated memory subspace. The permutation importance pipeline manages its own internal stratified validation loop, the contrast miner isolates rule intersections using compressed frequent pattern trees, the clustering module reduces dimensional spaces via t-SNE algorithms, and the Bayesian module computes conditional probability distributions using maximum likelihood estimators.

### State Transitions and Inter-Process Communication

An individual experiment instance maintains an isolated lifecycle to prevent cross-contamination between parallel executions. Upon initialization, the object exists in an unconfigured state until the baseline command arguments are injected as a unified parameter dictionary. Once the configuration is established, the module transitions into an active execution state where input data streams are consumed. During this phase, internal state variables track modeling milestones, such as classifier convergence or rule-filtering completions. A successful pipeline evaluation transitions the module into an artifact building state, where formatting routines write the physical outputs onto the local storage layout before the object is safely decommissioned by the garbage collection layer.

## Structural and Modular Organization

The internal architecture of the suite follows a highly decoupled design pattern where individual clinical questions are isolated within standalone class definitions extending a core abstract class contract.

### Class Hierarchies and Type Contracts

The framework relies heavily on inheritance to enforce uniform behavior across all research modules. The abstract baseline class defines the structural layout, declaring explicit data fields for the resulting LaTeX strings, public Plotly figure handlers, and descriptive names. It exposes abstract execution contracts that mandate specific input matrices and configuration parameter maps, ensuring that any newly introduced clinical experiment remains
