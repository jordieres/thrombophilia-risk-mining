# Technical reference: thrombophilia manuscript reanalysis

The authoritative technical and user specification is
[the manuscript reanalysis manual](docs_source/manuscript_reanalysis.rst), also
published as [HTML](manuscript_reanalysis.html). It documents the executed
statistical procedure, configuration, complete output schema, reproduction,
failure behaviour and scientific limitations in English.

## Architecture and trust boundaries

The supported paper workflow follows this sequence:

1. `manuscript_cohort.py` reads the raw registry, checks unique IDs, defines
   tested-only eligibility and explicit known-carrier exclusions, and applies
   an allowlist of fixed pretest clinical transformations.
2. `manuscript_reanalysis.py` produces descriptive tables, defines candidate
   availability in development, builds paired complete-case and native-missing
   populations, and orchestrates nested and temporal validation.
3. `manuscript_models.py` learns supervised screens, category vocabularies,
   L1/tree parameters, signed point cards, separate point calibration and
   training-only operating thresholds.
4. `manuscript_reporting.py` derives English responses, manuscript text,
   supplementary material and standalone figures from the new numerical files.
5. Outcome checks enforce cohort membership, unique held-out predictions,
   temporal separation, paired primary populations, finite risks and exact
   confusion/resource identities before writing a completion checkpoint.

No old performance CSV or historical score card feeds this chain. Results are
kept in a dedicated run directory with input/source/configuration hashes.
Report generation has its own source hash because changing prose does not
require refitting otherwise identical numerical models.

## Population and model contracts

The registry description retains every source patient. Unknown global study
status is distinguished from explicit not-tested status even when both appear
in the same descriptive comparison group. Subtype prediction requires a binary
registered result within globally tested patients; the available extract cannot
independently prove completion of every subtype assay.

Development diagnoses end in 2021. A fixed 40% development missingness ceiling
and nonconstant-variable requirement define the primary candidate set, without
using outcomes. Primary models use the same complete-case patients. A separate
XGBoost analysis retains incomplete observations and a broader allowlisted
candidate set; it is not an isolated imputation experiment. Holdout records do
not redefine candidate availability.

Univariable categorical logistic likelihood-ratio screening at p<0.10 precedes
L1 logistic fitting within training folds. Five inner folds tune C; five outer
folds estimate performance. XGBoost searches four documented configurations.
Signed points preserve coefficient direction, and their probability mapping
uses actual point sums rather than full-model probabilities. Operating thresholds
come from training predictions and are locked before validation; a held-out
sensitivity below 90% is an honest result, not an error to optimize away.

The manual provides every numeric boundary, the complete XGBoost grid, missing
semantics, uncertainty calculations and the interpretation of constant-card
fallbacks. Source/category identities are retained in point tables: `trat_est`
means statins and `fr_estro` means hormone exposure.

## Historical framework

The original `src/cli.py` still orchestrates the generic experiment classes.
Their general processor can fill missing histories with No and their generic
score route does not impose the paper's predictor/cohort contracts. These tools
are exploratory and must not replace the new validation outputs. Clustering
uses UMAP, and Bayesian conditional summaries describe associations rather than
causal effects. The old manuscript command now delegates to the safe workflow;
its former unsafe model-generation loop has been removed.

The Excel preparation utility remains available for reproducing historical
subsets, but its row filtering and imputation directives mean those subsets are
not interchangeable with the raw source for the new analysis.

## Verification and scientific limits

Run `python -m pytest tests -q` for regression tests and
`python -m sphinx -W --keep-going -b html docs/docs_source docs` for documentation.
See the developer guide for test-only integration settings and dependency pins.
The numerical outputs, code, generated reports and documentation must agree on
population, model identity, threshold selection and missing-data policy.

Successful execution does not establish assay timing, repeated laboratory
confirmation, causal explanations of sex differences, or external validity.
Those data are unavailable here. Complete-case attrition, sparse outcomes and
small temporal holdouts remain visible in the manuscript-ready results.
