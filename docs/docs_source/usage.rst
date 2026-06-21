Usage
=====

CLI entry point
---------------

The project exposes a single CLI entry point implemented in ``src/cli.py``.

.. code-block:: bash

   poetry run python src/cli.py --data data/patD.parquet --experiment all

Configurable experiment budgets
-------------------------------

The CLI exposes knobs for experiments that may otherwise be expensive on large
clinical datasets.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment permutation \
     --permutation-max-samples 800 \
     --permutation-max-splits 2 \
     --permutation-repeats 1 \
     --permutation-estimators 10

Contrast mining on large datasets
---------------------------------

The contrast workflow includes explicit memory guards, bounded rule search, and
resumable checkpoints. On large datasets, prefer configuring the contrast run
with a modest sample budget, a strict support threshold, and a checkpoint
folder that can be reused with ``--resume`` after an interrupted run.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment contrast \
     --contrast-max-samples 300 \
     --contrast-min-support 0.05 \
     --contrast-min-confidence 0.40 \
     --contrast-max-feature-cardinality 12 \
     --contrast-max-features 48 \
     --contrast-max-rule-size 3 \
     --contrast-top-k-per-outcome 5 \
     --contrast-workers 2 \
     --checkpoint-dir out/checkpoints \
     --output-dir out \
     --resume

The contrast checkpoint directory stores four stages:

``01_prepared_sample.parquet``
   Stratified sample plus the selected low-cardinality columns.

``02_encoded_transactions.parquet``
   Sparse one-hot transactional matrix serialized as compact integer values.

``03_frequent_itemsets.parquet``
   Frequent itemsets mined with the configured support and maximum rule length.

``04_target_rules.parquet``
   Final outcome-targeted rules ready for LaTeX and Plotly export.

Metric-aware clustering
-----------------------

The clustering workflow accepts configurable distance spaces for both
agglomerative grouping and UMAP embedding. This is useful when Euclidean space
is too sensitive to scale, and a Manhattan or cosine geometry better matches
clinical trajectories. The experiment also exports a reusable
``umap_coordinates.csv`` file containing the patient identifier, UMAP
coordinates, cluster, and sampled source variables. An optional JSON ruleset
can recolor the plot using clinical labels, with ``other`` (or another
configured default) assigned to the remaining patients.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment clustering \
     --clustering-max-samples 20000 \
     --clustering-metric manhattan \
     --clustering-n-clusters 3 \
     --clustering-n-neighbors 15 \
     --clustering-min-dist 0.1 \
     --output-dir out

To recolor an existing UMAP projection without recomputing the embedding, use
``src/recolor_umap.py`` against the exported ``umap_coordinates.csv``:

.. code-block:: bash

   poetry run python src/recolor_umap.py      --umap-csv out/umap_cosine_alt/umap_coordinates.csv      --color-rules-json color_rules_v2.json      --output-html out/umap_cosine_alt/recolored_umap_v2.html

Categorical association heatmap
-------------------------------

The ``categorical_association`` experiment measures pairwise relationships
between categorical variables using Cramer's V, writes a full matrix export,
and highlights the strongest variable pairs for exploratory review. It is the
closest structured replacement for the categorical-correlation notebook work.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD_slim.parquet \
     --experiment categorical_association \
     --association-max-samples 5000 \
     --association-max-columns 20 \
     --association-top-k 20 \
     --output-dir out

The categorical association export includes three complementary outputs:

``tab:categorical_association``
   Ranked top variable pairs ordered by descending Cramer's V.

``categorical_association_matrix.csv``
   Full square matrix of pairwise Cramer's V scores across the selected
   categorical variables.

``categorical_association_top_pairs.csv``
   Flat table with the strongest non-diagonal variable pairs.

Open association-rule explorer
-------------------------------

The ``association_explorer`` experiment mines general association rules over
bounded categorical variables. Unlike ``contrast``, it is not restricted to a
single outcome column, so it can be used to inspect what relationships emerge
around any retained variable, including but not limited to ``ana_dura``.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD_slim.parquet \
     --experiment association_explorer \
     --association-rules-max-samples 5000 \
     --association-rules-min-support 0.01 \
     --association-rules-min-confidence 0.40 \
     --association-rules-min-lift 1.00 \
     --association-rules-max-feature-cardinality 12 \
     --association-rules-max-features 24 \
     --association-rules-max-rule-size 3 \
     --association-rules-top-k 30 \
     --association-rules-sort-metric leverage \
     --association-rules-filter-column ana_dura \
     --association-rules-filter-side either \
     --output-dir out

The main supervised workflows can now be repointed to an alternative target
column when the dataset supports it. For example, if you want to explore a
binary encoding derived from ``anadutip`` instead of ``ana_dura``, the
``permutation``, ``contrast``, ``bayesian``, ``score``, and
``score_screening`` experiments all accept explicit target-column runtime
parameters.

Bayesian conditional summaries
------------------------------

The ``bayesian`` experiment now builds a conditional probability table for any
selected target column grouped by a configurable categorical parent column.

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment bayesian      --bayesian-target-column ana_dura      --bayesian-group-column sexo      --output-dir out

Filtering a target to explicit valid labels
-------------------------------------------

When the target column contains many ``Missing`` rows, you can now restrict the
analysis to an explicit set of valid labels before rule mining, categorical
association, or Bayesian summaries. This is especially useful for variables
such as ``var161`` that should be studied as ``Sí`` versus ``No`` only.

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment categorical_association      --association-target-column var161      --association-target-valid-labels Sí No      --association-max-samples 5000      --association-max-columns 20      --association-top-k 25      --output-dir out/var161_assoc

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment association_explorer      --association-rules-target-column var161      --association-rules-target-valid-labels Sí No      --association-rules-filter-column var161      --association-rules-filter-side either      --association-rules-max-samples 22000      --association-rules-min-support 0.01      --association-rules-min-confidence 0.40      --association-rules-min-lift 1.00      --association-rules-max-feature-cardinality 12      --association-rules-max-features 24      --association-rules-max-rule-size 3      --association-rules-top-k 50      --association-rules-sort-metric leverage      --output-dir out/var161_rules

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment contrast      --contrast-target-column var161      --contrast-target-valid-labels Sí No      --contrast-max-samples 22000      --contrast-min-support 0.02      --contrast-min-confidence 0.35      --contrast-max-feature-cardinality 22      --contrast-max-features 60      --contrast-max-rule-size 3      --contrast-top-k-per-outcome 15      --contrast-workers 2      --output-dir out/var161_contrast

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment bayesian      --bayesian-target-column var161      --bayesian-target-valid-labels Sí No      --bayesian-group-column sexo      --output-dir out/var161_bayesian

Retargeting the studies to an alternative binary variable
---------------------------------------------------------

If you derive a binary label from ``anadutip`` (for example,
``anadutip_binary`` with values such as ``Homocigoto`` and ``Heterocigoto``),
you can reuse the current pipeline by passing the target and class labels
through the CLI.

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment permutation      --permutation-target-column anadutip_binary      --permutation-positive-label "Homocigoto"      --permutation-negative-label "Heterocigoto"      --permutation-max-samples 800      --permutation-max-splits 2      --permutation-repeats 1      --permutation-estimators 10

.. code-block:: bash

   poetry run python src/cli.py      --data data/patD.parquet      --experiment contrast      --contrast-target-column anadutip_binary      --contrast-max-samples 300      --contrast-min-support 0.05      --contrast-min-confidence 0.40      --contrast-max-feature-cardinality 12      --contrast-max-features 48      --contrast-max-rule-size 3      --contrast-top-k-per-outcome 5      --contrast-workers 2      --output-dir out

The association-rule explorer export includes:

``tab:association_explorer``
   Ranked rule table ordered by the configured metric.

``association_explorer_top_rules.csv``
   Flat export of the displayed top rules with support, confidence, lift,
   leverage, and itemset sizes.

``out/checkpoints/association_explorer_*/``
   Prepared sample, encoded transactions, frequent itemsets, and the full rule
   table for resumable inspection.

Clinical integer score and ROC benchmarking
-------------------------------------------

The ``score`` experiment filters the cohort to the binary diagnostic criterion,
removes ``Missing`` and ``No buscada`` outcomes, and can now compare two
feature-selection strategies: an automatic low-cardinality discovery workflow
and an association-guided preset based on rule-mining findings (female sex,
younger age bands, no prior DVT, normal hemoglobin, negative D-dimer, no
malignancy, and no immobilization when those fields are available).

The operating threshold is no longer chosen by Youden optimization. Instead,
the score selects the most specific threshold that still satisfies the
pre-specified minimum sensitivity constraint, which is more appropriate for a
rule-out screening tool.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment score \
     --score-target-column ana_dura \
     --score-positive-label "Buscada positivo" \
     --score-negative-label "Buscada negativo" \
     --score-max-samples 2500 \
     --score-feature-strategy compare \
     --score-max-feature-cardinality 12 \
     --score-numeric-bins 4 \
     --score-cv-splits 4 \
     --score-min-sensitivity 0.90 \
     --score-benchmark-model both \
     --score-top-features 10 \
     --score-xgboost-estimators 80 \
     --output-dir out

The clinical score export includes four complementary outputs:

``tab:clinical_roc``
   Cross-validated ROC AUC plus the threshold selected under the minimum
   sensitivity rule.

``tab:clinical_score_distribution``
   Outcome-stratified integer-score distribution summary for interpretability.

``tab:clinical_score_components``
   Positive logistic components converted into bedside integer points for each
   strategy.

``clinical_risk_score_per_patient.csv``
   Patient-level export including the identifier, observed outcome, and one set
   of score/threshold/decision columns per enabled strategy.

Clinical score screening for missing or unrequested studies
-----------------------------------------------------------

The ``score_screening`` experiment trains the clinical score on the confirmed
binary subset and then applies the resulting point cards to records labelled as
``Missing`` or ``No buscada`` in ``ana_dura``. It also exports probability-based
screening outputs from the same logistic and XGBoost benchmark families used in
``score``, which is helpful when the bedside integer score is too blunt for
prioritizing manual review. This is intended for review prioritization rather
than definitive diagnosis.

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD_slim.parquet \
     --experiment score_screening \
     --score-target-column ana_dura \
     --score-positive-label "Buscada positivo" \
     --score-negative-label "Buscada negativo" \
     --screening-labels Missing "No buscada" \
     --score-feature-strategy compare \
     --score-benchmark-model both \
     --score-max-samples 4000 \
     --score-max-feature-cardinality 12 \
     --score-numeric-bins 4 \
     --score-cv-splits 5 \
     --score-min-sensitivity 0.90 \
     --score-min-feature-prevalence 0.02 \
     --score-top-features 12 \
     --score-xgboost-estimators 80 \
     --output-dir out

The screening export includes:

``tab:clinical_screening_roc``
   Training ROC metrics used to derive the screening thresholds.

``tab:clinical_screening_summary``
   Counts of flagged candidates among the requested screening labels.

``clinical_risk_score_screening_candidates.csv``
   Patient-level candidate list with integer scores, benchmark probabilities,
   thresholds, and predicted positive flags for review.

Multi-line shell commands
-------------------------

When writing a Bash command across multiple lines, every continued line must be
escaped with ``\``. Without that escape character, Bash treats the next line as
an entirely new command.

Correct multi-line example
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   poetry run python src/cli.py \
     --data data/patD.parquet \
     --experiment all \
     --permutation-max-samples 2000 \
     --permutation-max-splits 2 \
     --permutation-repeats 1 \
     --permutation-estimators 10 \
     --contrast-max-samples 300 \
     --contrast-min-support 0.05 \
     --contrast-min-confidence 0.40 \
     --clustering-max-samples 1000 \
     --score-max-samples 2500

Incorrect multi-line example
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   poetry run python src/cli.py --data data/patD.parquet --experiment all
   --permutation-max-samples 2000
   --permutation-max-splits 2

In the incorrect example, the first line runs the CLI and the following lines
are interpreted by the shell as independent commands, which leads to
``command not found`` messages.

Available configuration groups
------------------------------

``permutation``
   Controls sampling, fold count, permutation repeats, and XGBoost tree count.

``contrast``
   Controls sampling, support/confidence thresholds, low-cardinality feature
   selection, maximum rule size, worker count, and checkpoint reuse.

``clustering``
   Controls the sampled cohort size, distance metric, cluster count, UMAP
   neighbor count, and embedding compactness.

``score``
   Controls the binary diagnostic labels, cohort sample cap, allowed
   categorical cardinality, numeric bin count, cross-validation folds,
   minimum sensitivity requirement, benchmark model family, coefficient
   reporting depth, and XGBoost tree count.

Artifact locations
------------------

Use ``--output-dir`` to redirect interactive HTML charts away from the project
root, and ``--checkpoint-dir`` to persist resumable intermediate state for
long-running experiments.

One-off patD preparation
------------------------

The repository includes a dedicated one-off utility for adapting
``data/patD.parquet`` to an Excel-driven variable specification. This helper is
independent from the main experiment CLI and is intended for controlled dataset
curation before downstream analysis.

Behavior summary:

* reads the Excel file and uses column A as the authoritative ordered variable
  list,
* preserves ``id_pacie`` only as a reference column and excludes it from the
  reported feature list,
* keeps only those selected variables in the generated parquet,
* replaces numeric sentinel values with ``NaN`` when present,
* normalizes missing ``ana_dime`` values to ``No practicado``,
* emits a JSON validation report with categorical and threshold-oriented checks
  derived from column C.

.. code-block:: bash

   python -m src.patd_spec_tool \
     --spec-xlsx "/tmp/varibeles explained.xlsx" \
     --output-parquet out/patD_spec_subset.parquet \
     --report-json out/patD_spec_subset_validation.json

To produce a cohort-specific parquet in one step, keep the target column and
then filter the transformed rows to the allowed labels:

.. code-block:: bash

   python -m src.patd_spec_tool \
     --input-parquet data/patD.parquet \
     --spec-xlsx "/tmp/varibeles explained.xlsx" \
     --target-columns var161 \
     --filter-column var161 \
     --filter-allowed-values Sí No \
     --output-parquet data/patD_var161.parquet \
     --report-json out/patD_var161_validation.json

Runtime summary:

* ``Input rows``: records loaded from the source parquet.
* ``Rows after Excel criteria``: rows remaining after column-C validation and
  row-discard rules.
* ``Rows after value filter``: rows remaining after ``--filter-column`` and
  ``--filter-allowed-values`` when those options are used.
* ``Output rows``: final rows written to the output parquet.

Generated artifacts:

``out/patD_spec_subset.parquet``
   Curated subset containing ``id_pacie`` plus only the Excel-selected
   variables.

``out/patD_spec_subset_validation.json``
   Validation trace with source and output row counts, feature list, allowed
   categorical values, observed values, and any detected issues. When a value
   filter is requested, the report also records ``row_filter_audit`` with the
   retained labels and discarded-row count.

VS Code debugging
-----------------

A preconfigured ``.vscode/launch.json`` file is included so the CLI can be
launched under ``debugpy`` with promptable dataset and sampling parameters.
