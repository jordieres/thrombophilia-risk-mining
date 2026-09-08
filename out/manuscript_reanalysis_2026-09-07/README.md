# Authoritative manuscript reanalysis outputs

Start with `coauthor_responses.md` (all 14 Word comments),
`replacement_manuscript_sections.md` (replacement text and main tables), and
`recalculated_supplement.md` (supplement and final cards). DOCX copies are generated
when Pandoc is installed. Narrative documentation and replies are in English.

`run_manifest.json` records parameters, hashes, software versions, completion
status and outcome selection. Only a complete manifest is a finished numerical
run. `table5_primary_performance.csv` uses paired complete cases and nested CV;
`supplement_native_missing_performance.csv` is a separate sensitivity analysis.
`model_cohort_flow.csv` explains every modelling denominator. The sex and raw
subtype availability tables intentionally precede predictive known-carrier
exclusions; their denominators must not be used for model metrics.

Each outcome directory contains held-out `predictions.parquet`, `metrics.csv`,
`calibration.csv`, candidate/missingness/exclusion audits, the nested search log,
final development cards, locked models and automated numerical quality checks.
The patient prediction files contain registry identifiers and are local research
artifacts, not manuscript tables. Final model files are development-only fits;
do not substitute their in-sample predictions for validation estimates.

The original Word files and historical results were preserved. Top-level legacy
outputs outside this directory are not valid replacements for the new results.
Run instructions and technical contracts are in
`docs/docs_source/manuscript_reanalysis.rst`.
