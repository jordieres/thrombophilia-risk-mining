# Analysis outputs and provenance

## Current principal manuscript analysis

Use `manuscript_reanalysis_2026-09-08/` for the investigator-confirmed routine-panel
interpretation, all 14 coauthor replies, replacement manuscript sections,
supplementary material and figures. Its six routine outcomes interpret missing
as negative only inside documented global testing. JAK2 stays explicit-only.
Predictor missingness and prior-known-thrombophilia exclusions are separate.

## Alternative interpretation and initial audit

`archive/manuscript_reanalysis_2026-09-07/` is the completed explicit-results alternative:
all missing subtype outcomes were excluded. Its numerical results are preserved
and clearly labelled; it is no longer the principal manuscript result.

`archive/manuscript_audit_2026-09-07/` preserves the initial comparison of Word drafts
with historical analyses. It documents what was known before the clarification.

## Historical exploration

`archive/legacy_top_level/` contains the former top-level outputs;
`path_map.json` maps old to new locations. Other earlier experiments remain under
`archive/`. None supplies new model evidence. Aggregate tables are versioned;
legacy interactive figures and individual records are local-only.

## What belongs in Git

Version aggregate CSV/JSON, English Markdown, standalone aggregate figures,
source code and documentation. Keep predictions, patient-level CSVs, fitted
model binaries, notebook outputs, Sphinx caches and optional DOCX/PDF exports
local. Public `outputs_sha256` inventories verify a clone independently of
`local_artifacts` and `optional_exports`. Use
`python scripts/check_repository_artifacts.py` before publishing.

Files removed from the latest Git tree still exist in earlier commits. This
cleanup does not rewrite history; local research copies are preserved.

## Checkpoint lifecycle

`archive/checkpoints/` holds the historical association and contrast experiments.
Their tracked JSON files document configuration and feature profiles; intermediate
Parquet files remain local. To resume one deliberately, pass
`--checkpoint-dir out/archive/checkpoints --resume` with the original experiment
settings. New exploratory runs still default to `out/checkpoints/`, created on
demand. The current manuscript's outcome-level `completed.json` files remain
inside its analysis directory and continue to support manuscript `--resume`.

## Additional methodological review: continuous multiple imputation

`manuscript_mi_2026-09-09/` is the separate new run with mixed-type chained
imputation, continuous predictors, spline LASSO without univariable screening,
and held-out decision curves. Check its `run_manifest.json` for completion;
do not treat a running/failed run as finished evidence. The existing principal
package above remains preserved for comparison.
