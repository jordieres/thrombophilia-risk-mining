Architecture
============

This page explains the runtime architecture of the thrombophilia risk mining
project and how data moves from the command line entry point to experiment-
specific output artifacts.

System Overview
---------------

The project is organized around a thin orchestration layer and a set of
independent analytical modules.

.. graphviz::

   digraph system_overview {
       rankdir=LR;
       node [shape=box, style="rounded,filled", fillcolor="#F8F8F8", color="#4C566A"];

       cli [label="CLI\nsrc/cli.py"];
       processor [label="ClinicalDataProcessor\nsrc/data_processor.py"];
       registry [label="Experiment Registry\nconfigured instances"];
       perm [label="PermutationImportanceExperiment"];
       contrast [label="ContrastPatternMiningExperiment"];
       cluster [label="UnsupervisedClusteringExperiment"];
       assoc [label="CategoricalAssociationExperiment"];
       rules [label="AssociationExplorerExperiment"];
       bayes [label="BayesianNetworkExperiment"];
       screen [label="ClinicalScoreScreeningExperiment"];
       outputs [label="Artifacts\nLaTeX + HTML"];

       cli -> processor [label="load + preprocess"];
       processor -> registry [label="cleaned DataFrame"];
       registry -> perm;
       registry -> contrast;
       registry -> cluster;
       registry -> assoc;
       registry -> rules;
       registry -> bayes;
       registry -> screen;
       perm -> outputs;
       contrast -> outputs;
       cluster -> outputs;
       assoc -> outputs;
       rules -> outputs;
       bayes -> outputs;
       screen -> outputs;
   }

Execution Flow
--------------

At runtime the CLI performs the same high-level sequence regardless of the
selected experiment.

.. graphviz::

   digraph execution_flow {
       rankdir=TB;
       node [shape=box, style="rounded,filled", fillcolor="#F8F8F8", color="#4C566A"];

       parse [label="Parse CLI arguments"];
       load [label="Load source dataset\nCSV / Excel / Parquet"];
       clean [label="Normalize sentinel values\nand harmonize categorical flags"];
       select [label="Instantiate configured\nexperiment objects"];
       run [label="Run selected experiment(s)"];
       export_html [label="Write Plotly HTML artifact"];
       export_tex [label="Print and store LaTeX table"];

       parse -> load -> clean -> select -> run -> export_html -> export_tex;
   }

Preprocessing Responsibilities
------------------------------

The shared preprocessing layer exists to keep experiment implementations focused
on analysis rather than file handling or dataset repair.

.. graphviz::

   digraph preprocessing {
       rankdir=LR;
       node [shape=box, style="rounded,filled", fillcolor="#F8F8F8", color="#4C566A"];

       source [label="Raw tabular dataset"];
       sentinel [label="Replace int64 sentinel\nwith NaN"];
       derived [label="Create derived categories\nhemoglobina_cat / plaquetas_cat"];
       history [label="Fill history flags\nwith 'No'"];
       ready [label="Processed DataFrame\nshared by all experiments"];

       source -> sentinel -> derived -> history -> ready;
   }

Experiment Roles
----------------

``PermutationImportanceExperiment``
   Trains a reduced XGBoost classifier without dominant demographic features and
   estimates feature relevance by permutation within validation folds.

``ContrastPatternMiningExperiment``
   Converts a sampled subset of low-cardinality categorical variables into
   transaction baskets and mines association rules linked to diagnostic outcome.

``UnsupervisedClusteringExperiment``
   Restricts the dataset to numeric variables, imputes missing values, scales
   them, and combines agglomerative clustering with a t-SNE visualization.

``CategoricalAssociationExperiment``
   Restricts the dataset to categorical variables and measures pairwise
   association strength using Cramer's V, exporting both a matrix and a ranked
   pair list.

``AssociationExplorerExperiment``
   Mines open association rules across selected low-cardinality categorical
   variables and supports filtering by whether a chosen column appears in the
   antecedent, consequent, or either side of the rule.

``BayesianNetworkExperiment``
   Builds a conditional probability summary by sex for the diagnostic target and
   exports it as both a LaTeX table and a grouped bar chart.

``ClinicalScoreScreeningExperiment``
   Fits the validated score on confirmed positive/negative studies and applies
   it to ``Missing`` or ``No buscada`` records to build a review-oriented
   candidate ranking.

Configuration Surfaces
----------------------

The architecture exposes three main configuration surfaces through the CLI:

* preprocessing input selection through ``--data``;
* experiment selection through ``--experiment``;
* runtime budgets for expensive modules through the permutation, contrast,
  clustering, categorical-association, and association-rule parameter groups.

Type-Checked Boundaries
-----------------------

The runtime boundaries documented above are also explicit in the static typing
model:

* the CLI accepts validated primitive arguments and builds typed experiment
  instances;
* the processor returns a :class:`pandas.DataFrame` shared across experiments;
* each experiment implements the :class:`experiment_base.BaseExperiment`
  contract and populates typed output attributes.
