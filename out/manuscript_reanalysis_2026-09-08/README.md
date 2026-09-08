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

Each local research outcome directory contains held-out `predictions.parquet`, `metrics.csv`,
`calibration.csv`, candidate/missingness/exclusion audits, the nested search log,
final development cards, locked models and automated numerical quality checks.
Patient prediction files contain registry identifiers and stay local, outside
Git. Fitted model binaries also stay local. Word/PDF documents are optional
local exports; Markdown, aggregate CSV/JSON and figures are versioned. Public
manifest verification uses `outputs_sha256`; `local_artifacts` and
`optional_exports` are separate inventories and are not required in a clone. Final model files are development-only fits;
do not substitute their in-sample predictions for validation estimates.

The source Word documents remain local, and historical aggregate results were preserved. Legacy files
are under `out/archive/`; the 7 September explicit-results run is an alternative
policy analysis, not the current routine-panel principal result.
Run instructions and technical contracts are in
`docs/docs_source/manuscript_reanalysis.rst`.

This routine-panel interpretation is the principal paper analysis.

See `outcome_policy_comparison.md` for the aggregate comparison with the earlier explicit-results run.
