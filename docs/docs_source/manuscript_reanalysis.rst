Manuscript reanalysis: user and technical manual
====================================================

Purpose and scope
---------------------

This is the authoritative workflow for the recalculated thrombophilia paper.
It replaces the model-generating portion of the former
``src/manuscript_support.py`` audit. It does not consume historical AUCs, score
cards, prediction CSVs or validation summaries. The historical tools remain
available for exploration but have different cohort and preprocessing contracts.

The workflow addresses the fourteen comments extracted from the two supplied
Word documents and the additional inconsistencies identified by the September
2026 audit. The output includes replacement Methods/Results, a regenerated
supplement, individual comment replies, standalone figures and machine-readable
numerical evidence. All new user documentation, technical descriptions and
responses are in English. The original Word documents are preserved locally.

What has changed scientifically
-----------------------------------

* Every subtype analysis requires documented global testing. On 8 September
  2026, the study investigators clarified that FVL, prothrombin, APS, protein C,
  protein S and antithrombin are routine panel components: their missing results
  are interpreted as negative within that tested group. JAK2 is not routine and
  always requires explicit positive/negative results. No untested/unknown global
  study record is admitted by the missing-to-negative convention.
* Positive known-carrier status and previously known APS exclude patients from
  predictive analyses. They do not remove patients from registry descriptions.
* A source-code allowlist excludes test results and follow-up information from
  predictors. ``trat_est`` is correctly labelled **statin treatment**;
  ``fr_estro`` is recent hormone exposure.
* Fixed clinical categories replace sample quantiles. Numeric quality failures
  become missing observations rather than disappearing patients.
* The primary comparison uses a common complete-case population; an additional
  tree analysis includes incomplete records and a broader candidate set.
* Univariable categorical logistic likelihood-ratio screening and tuned L1
  regression replace the historical L2 model that was described as LASSO.
* Nested validation separates parameter/threshold selection from evaluation.
  The temporal cutoff is fixed to 2021 rather than selected by an outcome-aware
  search for a convenient year.
* The probability associated with a simplified point card is fitted from that
  card's actual point sums. It is not the full logistic model's probability.
* Every performance, confusion-matrix and resource number comes from the same
  stored predictions and the same population.

Input and installation
--------------------------

Use the original ``data/patD.parquet``. Do not supply ``patD_slim.parquet`` or a
``patD_var*.parquet`` prepared by the Excel tool: those files can have filtered
rows, removed cohort fields or historical absence-to-No replacements.

The minimum cohort schema is ``id_pacie``, ``ana_dura``, ``fecha_di``,
``ana_port`` and ``e_con_af``. Each requested outcome column must exist.
``id_pacie`` must be nonmissing and unique; duplicate patients cause failure.
The production raw snapshot contains one row per unique patient. Optional
predictor fields absent from the input are not manufactured.

A dedicated pinned analysis environment can be installed with:

.. code-block:: bash

   python -m venv .venv-manuscript
   .venv-manuscript/bin/python -m pip install -r requirements-manuscript.txt

The recorded run uses Python 3.12 and the versions saved in its manifest.
``requirements-manuscript.txt`` pins the tested scientific and reporting stack;
the project Poetry specification covers the broader exploratory toolkit.
Pandoc is an optional executable for DOCX conversion. It does not participate in
model fitting. Matplotlib writes standalone PNG/SVG figures without a browser.

Full production run
-----------------------

From the repository root:

.. code-block:: bash

   python src/manuscript_reanalysis.py \
     --data data/patD.parquet \
     --output-dir out/my_reanalysis

The command runs the composite, FVL, prothrombin, registry-coded APS, protein S,
protein C, antithrombin and JAK2 outcomes. It performs no patient subsampling.
Progress logs identify the outcome, analysis population, fold and final fit.
Runtime depends on hardware and the number of eligible patients; nested tuning
fits many models. JAK2 outputs remain descriptive even when all numerical
calculations complete successfully.

The defaults are:

.. list-table:: Reproducibility parameters
   :header-rows: 1
   :widths: 30 20 50

   * - Argument
     - Default
     - Meaning
   * - ``--outcome-policy``
     - routine-panel
     - Six routine missing outcomes become negative within global testing; JAK2 stays explicit. Use explicit-results for the alternative analysis.
   * - ``--cutoff-year``
     - 2021
     - Development through 2021; later diagnoses are held out.
   * - ``--max-missing``
     - 0.40
     - Development-only missingness ceiling for primary candidates.
   * - ``--outer-splits`` / ``--inner-splits``
     - 5 / 5
     - Stratified validation and tuning folds.
   * - ``--min-sensitivity``
     - 0.90
     - Training operating-point target; not a held-out guarantee.
   * - ``--seed``
     - 42
     - Deterministic splitting and model seed.
   * - ``--threads``
     - 2
     - Per-XGBoost fit CPU threads.
   * - ``--bootstrap``
     - 200
     - Stratified resamples of fixed predictions for AUC intervals.
   * - ``--outcomes``
     - All eight
     - Explicit subset of registered outcome column names.
   * - ``--resume``
     - Off
     - Reuse matching completed outcome checkpoints.
   * - ``--no-reports``
     - Off
     - Generate numerical evidence only; reports can follow separately.
   * - ``--compact``
     - Off
     - Test-only first two parameter configurations; no sampling.

For an inexpensive integration exercise, use a separate directory:

.. code-block:: bash

   python src/manuscript_reanalysis.py \
     --outcomes andujak2 --compact \
     --outer-splits 2 --inner-splits 2 --bootstrap 0 \
     --output-dir /tmp/manuscript_smoke

This is a test run, not a replacement for the full manuscript analysis.

Resuming and regenerating reports
-------------------------------------

.. code-block:: bash

   python src/manuscript_reanalysis.py \
     --data data/patD.parquet \
     --output-dir out/my_reanalysis --resume

A completed outcome is reusable only if raw-data contents, numerical analysis
code and analysis configuration match its signature. Changed code or settings
require a new directory. An interrupted outcome without a completed checkpoint
is recalculated. Successful checkpoints are not silently overwritten without
``--resume``. The run manifest records ``running``, ``failed`` or ``complete``;
a failed run is not a completed evidence package.

Reports can be regenerated from finished numerical outputs:

.. code-block:: bash

   python src/manuscript_reporting.py out/my_reanalysis

The report command writes English Markdown, PNG/SVG figures and local DOCX if
Pandoc is available. It does not retrain models. When patient predictions are
absent from a Git clone, it reuses the already published aggregate figures;
missing predictions and missing figure files produce an explicit error for an
analysed outcome rather than silently dropping its plots. The numerical analysis signature and
report-generation source hash are separate provenance items.

The compatibility command ``python src/manuscript_support.py`` delegates to
this engine. A legacy request to write directly into ``out`` is routed into
``out/manuscript_reanalysis`` to avoid replacing unrelated historical files.
Use the dedicated command for resume, outcome selection and parameter control.

Cohort definitions and denominator hierarchy
------------------------------------------------

Registry description
~~~~~~~~~~~~~~~~~~~~~~~~

``ana_dura`` equal to ``Buscada positivo`` or ``Buscada negativo`` establishes
documented global testing. Explicit ``No buscada`` and unknown labels are
combined only for the descriptive not-tested/unknown comparison. Their separate
counts remain visible; unknown does not prove a test was never performed.

Tables 1 and 2 use the original registry, not the former numerically filtered
snapshot. Category percentages use **observed** values with separate missing
counts. Numeric summaries apply the declared quality bounds. Descriptive
p-values use Fisher for binary categories, chi-square for larger categorical
tables and Welch's test for continuous variables. Standardized differences are
reported per categorical level and continuous variable; p-values do not select
model predictors.

Predictive eligibility
~~~~~~~~~~~~~~~~~~~~~~~~~~

A patient must have documented global testing and no explicit prior carrier or
known APS label. Unknown carrier status is retained as unknown, not described
as proven absence. The composite uses the original positive/negative global
labels and is unaffected by the subtype policy.

The default ``--outcome-policy routine-panel`` implements the investigators'
8 September 2026 clarification. FVL (var156), prothrombin (var157), APS (var161),
protein C (var154), protein S (var155) and antithrombin (var158) are interpreted
as routinely included when the global study is performed. Their null, blank or
literal ``Missing`` results become ``No`` **only** when ``ana_dura`` is explicitly
positive or negative. Other nonbinary labels are not converted. JAK2
(``andujak2``) never receives this replacement: missing remains missing and only
explicit positive/negative JAK2 results are eligible.

``outcome_labels`` returns a derived label series; it does not mutate the raw
registry. Outcome masking, training targets and integrity checks all use this
same policy. Prediction labels are checked against the declared interpretation,
not merely against the set of eligible IDs. Predictor missingness is an entirely
separate issue and retains the complete-case/native-missing strategies below.

The alternative ``--outcome-policy explicit-results`` excludes missing subtype
results for all subtypes. The preserved run in
``out/archive/manuscript_reanalysis_2026-09-07/`` uses that earlier interpretation. The
current principal run is ``out/manuscript_reanalysis_2026-09-08/``. Composite and
JAK2 eligibility are identical under both policies; the six routine outcomes
change. Re-running a different policy requires a new output directory.

The outcome table separates raw binary availability, original missing results,
missing-to-negative interpretations, remaining unavailable results, known-carrier
exclusions and predictive eligibility. ``interpreted_tested_n`` is the denominator
for policy-specific descriptive positivity before predictive exclusions;
``eligible_n`` is after exclusions. Model metrics use their own development or
holdout population, after any predictor completeness criteria.

The routine-panel rule is an explicit investigator-supplied interpretation of
registry coding. The extract does not independently adjudicate laboratory assay
completion or repeat-confirmed APS. Report the assumption and its provenance;
do not claim that every inferred negative was individually laboratory-verified.

Primary complete-case population
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Per outcome, candidates must vary and have no more than 40% missingness in the
eligible development records. This is an outcome-blind cohort-design decision
using the development covariate distribution, before internal cross-validation;
it is not supervised feature selection. Holdout covariates and outcomes do not
change that definition. Complete cases for **all retained candidates** form the
primary population, which is stricter than completeness for only the final
nonzero score components.

The same patient IDs are evaluated for the primary LASSO, integer score and
XGBoost models. Each outcome writes an included-versus-excluded baseline table.
The original registry is not globally reduced because one laboratory value is
invalid. Complete-case loss is instead visible at the relevant analytical step.

Sensitivity population
~~~~~~~~~~~~~~~~~~~~~~~~~~

The native-missing XGBoost analysis includes all eligible records with a valid
development/holdout date and all nonconstant allowlisted predictors. It can
include high-missingness variables such as recorded ethnicity. Differences from
the principal analysis reflect **both population and candidate-set changes**;
they are not a controlled comparison of imputation methods alone. Cases with an
unknown diagnosis date are counted and excluded from temporal assignment.

Feature contract
--------------------

``manuscript_cohort.CATEGORICAL`` and ``NUMERIC`` are the explicit allowlists.
Identifiers, global testing status, every thrombophilia outcome, prior carrier
status, known APS, quantitative D-dimer and follow-up fields are excluded as
predictors. Adding a new source-data column does not automatically add a model
feature. Index-event availability is based on the supplied dictionary; the
extract does not independently timestamp every predictor relative to the assay.

The fixed categories include:

.. list-table:: Numerical clinical categories
   :header-rows: 1
   :widths: 30 35 35

   * - Source
     - Accepted quality range
     - Categories
   * - Age, years
     - 0–120
     - <50; 50–69; >=70
   * - Weight, kg
     - 29–300
     - <50; 50–100; >100
   * - Systolic BP, mmHg
     - 35–300
     - <100; >=100
   * - Hemoglobin, g/dL
     - 4–20
     - <12; >=12
   * - Platelets, 10^9/L
     - 10–1500
     - <144; 144–400; >400
   * - Leukocytes, 10^9/L
     - 2–40
     - <4; 4–11; >11
   * - Neutrophils, 10^9/L
     - 0.4–30
     - <1.5; 1.5–8; >8
   * - C-reactive protein, mg/dL
     - 0–200
     - <0.5; >=0.5

These are declared analysis conventions, not diagnostic reference intervals
verified for every centre. The platelet boundary 144 follows the supplied
supplement; the older general processor used 140 in a different path. Small
floating-point edge offsets implement inclusive upper boundaries such as
400 exactly. Values outside quality bounds become missing. Numeric int64
minimum sentinels become missing too. The quality audit's ``original_missing``
counts raw nulls; ``transformed_missing`` also includes sentinels and rejected
measurements.

``female_under45`` requires known sex and valid age. Splanchnic thrombosis is
positive if any portal/mesenteric/splenic source is positive, negative only if
all three are explicitly negative, and otherwise unknown. Missing history stays
missing. D-dimer ``Not performed`` is a recorded category; an unknown field is
not recoded to it or interpreted as negative. Local categorical creatinine and
troponin results are retained as recorded. Height has no supplied categorical
specification for this analysis and is excluded rather than arbitrarily binned.

Supervised training and validation
--------------------------------------

LASSO and integer model
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The primary LASSO estimator requires complete cases. Within every training fold,
it tests each categorical candidate using the likelihood-ratio statistic of a
univariable categorical logistic model against intercept only. The equivalent
contingency-table G test avoids divergent coefficients under separation. Its
asymptotic p-value can still be unreliable in very sparse categories; screening
is exploratory and no post-selection inferential claim is made.

Candidates with p<0.10 are encoded with training-only categories, dropping the
first reference level. L1 logistic regression uses no class weighting and
``C`` in ``[0.01, 0.1, 1, 10]``. Inner-fold logistic AUC selects C; ties select the
first candidate. Explicit L1 configuration supports both the older penalty API
and the newer scikit-learn l1_ratio API. The full logistic model and its integer
simplification share that chosen regularization setting.

Nonzero coefficients (absolute magnitude >1e-6) are divided by the smallest
retained absolute coefficient and rounded to signed integer points. Positive
and negative points are possible. Reference and unselected categories contribute
zero. The exported card preserves source column, category, coefficient, label
and points; variable names alone never imply that a negative category means
presence of the condition. Very small retained coefficients can produce large
point scales; no undocumented score-size cap is introduced.

A nonnegative-slope logistic mapping is fitted from training **point sums** to
training outcomes using numerical standardization for stability. It yields
``expit(intercept + slope * total_points)``. It is separate from the full
logistic probability. If no predictors/coefficients survive, the card is
constant and the intercept-only fallback is retained rather than forcing a
spurious predictor into the model.

XGBoost and missingness
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The tree model learns a categorical vocabulary within training. One-hot output
is dense: observed zeros remain observed zeros. For an unknown or unseen source
category, its encoded block is set to NaN and XGBoost learns missing-value
branches. This avoids treating all absent sparse dummy entries as unmeasured.
The fixed-grid candidates are recorded in ``XGB_GRID`` and the manifest:

.. list-table:: XGBoost candidate configurations
   :header-rows: 1

   * - Trees
     - Depth
     - Rate
     - Subsample
     - Column sample
     - Alpha
     - Lambda
   * - 80
     - 2
     - 0.03
     - 0.8
     - 0.8
     - 0
     - 1
   * - 80
     - 3
     - 0.08
     - 0.8
     - 0.8
     - 0.1
     - 5
   * - 120
     - 2
     - 0.08
     - 1.0
     - 0.9
     - 0.5
     - 5
   * - 120
     - 3
     - 0.03
     - 0.9
     - 1.0
     - 0.1
     - 10

This is a declared finite configuration search, not an exhaustive Cartesian
search over every parameter combination. No early stopping is tuned on outer
validation data. The objective is binary logistic, the tree method is histogram,
and model selection maximizes inner AUC.

Nested operating-point evaluation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Five stratified outer folds evaluate the entire training procedure. Inside each
outer training set, five inner folds perform screening/encoding/fitting and
select hyperparameters. The chosen inner predictions determine the most
specific threshold meeting sensitivity >=0.90. The estimator is refitted on the
outer training set and that threshold is applied unchanged to outer validation.
Each eligible patient contributes one held-out prediction per analysis/model.
Folds are reduced only when minority counts cannot support the requested number;
this is recorded in the search audit.

Different training folds can produce different point scales. The pooled score
AUC therefore uses the calibrated probability of the actual card. The mean
within-fold raw-point AUC is exported separately as ``mean_fold_raw_auc``. The
operating threshold is mapped back to a point cutoff for each fitted card, and
an integrity check requires equivalent probability and integer decisions.
There is no single universal integer threshold for the pooled nested-CV cards.

The final card is fitted on all development complete cases using a fresh inner
search. Its inner predictions set its final threshold. The temporal test uses
that card, its vocabulary, calibration mapping and threshold unchanged. No
quantiles or feature cutoffs are learned from the temporal sample. A temporal
cohort with one outcome class has undefined AUC; the confusion matrix remains
reportable. Small samples do not cause an outcome-dependent change of year.

The composite-only guided comparison uses a prespecified subset of clinical
descriptors from the old manuscript on the same primary complete cases. It uses
the same positive-outcome/signed-point orientation as the automatic model. It
is not presented as cross-validated discovery of the full-cohort mined rules.

Metric definitions and uncertainty
--------------------------------------

``TP + FP + TN + FN = N`` and ``TP + FN = positive_n`` are enforced. Sensitivity,
specificity, PPV and NPV use the usual conditional denominators. An undefined
ratio is NaN in CSV and explicitly undefined/not estimable in narrative output;
it is not zero. Avoided tests are ``1000 * (TN + FN) / N``; missed positive
results are ``1000 * FN / N``. These quantify a hypothetical threshold decision,
not observed resource savings in a prospective implementation study.

Calibration uses ten fixed-width probability bins. ``mace`` is the unweighted
mean absolute calibration error across occupied bins; ``ece`` is weighted by
bin counts. Bin counts, mean predictions and observed frequencies are exported.
Brier and log loss use the actual model probability. Integer and logistic
calibration are distinct quantities even when similar numerically.

Sensitivity, specificity, PPV and NPV have Wilson 95% intervals. AUC intervals
use 200 stratified patient resamples of stored predictions by default. These
are conditional descriptive intervals and do not account for redoing selection
and fitting, or the full dependence between cross-validation predictions.
Do not label them as uncertainty from a complete nested bootstrap.

Association rules and descriptive Bayesian table
----------------------------------------------------

FP-Growth uses prespecified baseline descriptors in the eligible composite
cohort, joint support >=0.01, confidence >=0.80, lift >=1, and at most three
antecedents plus a negative-result consequent. No missing value activates a
negative clinical descriptor. All retained rules and their settings are saved.
Published example profiles are recomputed even if they fail these thresholds.
The ambiguous historical phrase “No DVT” is operationalized and labelled as
“No prior VTE”; no unobserved clinical distinction is invented.

The two-node ``Sex -> testing status`` Bayesian factorization is estimated by
maximum-likelihood conditional frequencies. Positive, negative and
not-tested/unknown status categories exhaust each sex group. This is a
reproducible descriptive conditional probability table, not causal inference
or structure learning on multiple variables.

Output catalogue
--------------------

.. list-table:: Main result files
   :header-rows: 1
   :widths: 45 55

   * - File
     - Contents and intended use
   * - ``coauthor_responses.md/.docx``
     - All 13 article comments plus one supplementary comment.
   * - ``replacement_manuscript_sections.md/.docx``
     - Replacement Methods, Results, interpretation and main tables.
   * - ``recalculated_supplement.md/.docx``
     - Definitions, missingness, performance, calibration and final cards.
   * - ``run_manifest.json``
     - Numerical signature/settings, policy, versions/status, and separate public/local/optional artifact hashes.
   * - ``report_manifest.json``
     - Report source hash and generated document/figure identities.
   * - ``registry_flow.json``
     - Full registry and mutually exclusive global testing groups.
   * - ``supplement_outcome_denominators.csv``
     - Raw binary availability, interpreted negatives, remaining missing results and carrier exclusions.
   * - ``model_cohort_flow.csv``
     - Eligible, development, complete-case and temporal counts by outcome.
   * - ``table1_baseline.csv`` / ``table2_positive_negative.csv``
     - Tidy descriptive comparisons with explicit observed denominators.
   * - ``table5_primary_performance.csv``
     - Paired complete-case nested-CV comparisons, not the raw tested N.
   * - ``supplement_native_missing_performance.csv``
     - Additional incomplete-data tree estimates.
   * - ``supplement_temporal_validation.csv``
     - All locked temporal evaluations, with population labels.
   * - ``supplement_calibration.csv``
     - Held-out calibration bins and counts.
   * - ``sex_testing_yield.csv`` / ``sex_effect_sizes.csv``
     - Sex-specific rates, effect sizes and uncertainty.
   * - ``testing_pattern_bayesian_cpd.csv``
     - Explicit descriptive two-node conditional probabilities.
   * - ``table3_recalculated_profiles.csv``
     - Recomputed old example profiles with separate support definitions.
   * - ``supplement_negative_association_rules.csv``
     - All rules meeting the declared new search specification.
   * - ``figures/``
     - Standalone PNG/SVG cohort, ROC, calibration and distribution figures.

Each full local research outcome directory contains ``predictions.parquet``, ``metrics.csv``,
``calibration.csv``, ``candidate_availability.csv``, ``missingness.csv``,
``included_vs_excluded.csv``, ``development_vs_temporal.csv``,
``nested_hyperparameter_search.csv``, ``final_models.json``, final search/point/
screen CSVs, serialized development models and ``quality_checks.json``.

``predictions.parquet`` contains local registry IDs for auditability. It and
patient-level CSVs are excluded from Git. Fitted model binaries are also local.
Only aggregate CSV/JSON, English narrative Markdown and aggregate PNG/SVG figures
are versioned. DOCX/PDF copies are optional local exports. Notebook sources are
versioned with outputs cleared; executed copies are preserved under ignored
``out/archive/notebook_executed_copies/``. Generated Sphinx caches are not tracked.

Version-2 manifests separate ``outputs_sha256`` (public aggregate artifacts),
``local_artifacts`` (patient/model/operational files) and ``optional_exports``
(Word/PDF). A public clone can verify every public checksum without local data
or optional exports. The historical 7 September manifest was migrated to this
inventory schema without changing numerical results; hashes of deleted optional
Word files remain in the optional inventory, not as required public files.

Run ``python scripts/check_repository_artifacts.py`` after staging changes and
before publishing. It checks the Git index and working files for local-only
outputs, individual CSV headers, executed notebook outputs, build caches,
incomplete public runs and broken public manifest references. It never prints
patient values. It does not inspect or rewrite Git history: removing a file from
the current tree does not remove it from previous commits.

Legacy former top-level outputs are under ``out/archive/legacy_top_level/``;
``path_map.json`` preserves their original locations for the initial audit.
Executed notebooks and legacy interactive figures stay local. No historical
output is used to fit the new models. A final model bundle stores the
estimator, its columns, thresholds and outcome. Use only trusted model bundles;
serialization is for this local reproducibility workflow. Final fitted models
are not a substitute for held-out validation predictions.

Integrity checks and failure behaviour
------------------------------------------

Production checks fail on duplicate predictions, predictions outside the
eligible cohort, nonfinite/out-of-range probabilities, temporal mixing,
unpaired primary populations, mismatched confusion counts or inconsistent
integer/probability threshold decisions. Outcome completion markers are written
only after these checks pass. Unsupported/empty outcome lists, invalid bounds,
missing cohort columns and inadequate class counts fail explicitly.

Regression tests cover the routine-panel exception, JAK2 missing preservation,
predictor unknown-to-No prevention, assay-control eligibility,
source-field leakage, exact clinical boundaries, dense missing encoding,
training-only threshold use and metric identities. A real-data compact
integration run exercises the full output path; the full production execution
has its own numerical checks. Neither successful tests nor a completed run
remove the scientific limitations described above.

Implementation map
----------------------

``src/manuscript_cohort.py``
   Raw schema validation, predictor allowlist, fixed transformations, cohort
   masks, known-carrier policy and missingness export.

``src/manuscript_artifacts.py``
   Public/local/optional inventory separation and public checksum verification.

``scripts/check_repository_artifacts.py``
   Git-index publication checks for local-only outputs and public manifests.

``src/manuscript_models.py``
   Category encoders, univariable screening, LASSO/point and tree estimators,
   nested tuning, score calibration, thresholds, metrics and calibration bins.

``src/manuscript_reanalysis.py``
   CLI, descriptive analyses, association rules, population construction,
   cross-validation/temporal orchestration, checkpoints and integrity checks.

``src/manuscript_reporting.py``
   CSV/JSON-driven English responses, manuscript/supplement text and figures.

``src/manuscript_support.py``
   Safe compatibility entry point plus descriptive historical helper APIs used
   by the preserved initial audit. The former unsafe model loop is removed.

``tests/test_manuscript_reanalysis.py``
   Regression tests protecting the statistical and data contracts.

Technical sources
---------------------

The distinction between inner model selection and outer performance evaluation
follows the official `scikit-learn nested-CV example
<https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html>`_.
The dense-zero versus sparse-missing distinction is documented in the official
`XGBoost FAQ <https://xgboost.readthedocs.io/en/release_2.0.0/faq.html>`_.
These sources explain implementation semantics; they do not supply clinical
results or justify assay eligibility that is absent from this registry extract.

Comparing outcome policies
--------------------------

The preserved 7 September run uses explicit results. The principal 8 September
run applies the investigator-confirmed routine-panel interpretation. After both
numerical runs finish, generate their aggregate comparison with::

   python scripts/compare_outcome_policies.py

This writes ``outcome_policy_comparison.csv``, an English Markdown explanation
and source-hash provenance into the principal output directory. It requires
matching registry hashes and modelling settings, and verifies that every
composite and JAK2 aggregate metric remains exactly unchanged. Routine subtype
comparisons describe different label definitions and patient populations; they
do not isolate an algorithm improvement. Regenerate the reports afterwards so
the public artifact inventory includes these comparison files.

Archived evidence and checkpoints
---------------------------------

The initial audit and explicit-results alternative are retained under
``out/archive/manuscript_audit_2026-09-07/`` and
``out/archive/manuscript_reanalysis_2026-09-07/``. The policy-comparison command
uses the archived alternative by default. Public manifest checks cover both
current and archived runs. Numerical results and run signatures are unchanged.

Historical association and contrast checkpoints are in
``out/archive/checkpoints/``. Use that path explicitly with the original
exploratory settings and ``--resume`` when needed. New exploratory runs retain
``out/checkpoints/`` as their on-demand default. Current manuscript outcome
``completed.json`` files stay in place for the supported manuscript resume flow.
