# Analysis outputs and provenance

## Authoritative manuscript outputs

Use `manuscript_reanalysis_2026-09-07/` for the corrected paper analysis, all 14
coauthor replies, replacement manuscript sections, supplementary material,
figures and reproducibility manifests. Its README explains the individual files.

`manuscript_audit_2026-09-07/` preserves the initial comparison of the supplied Word
documents with historical code and results. It is the diagnostic audit, not the
new model run.

## Historical outputs: superseded for manuscript reporting

All older top-level model CSV/HTML files and `coauthor_response_review.md` are
historical. In particular, the former audit model loop included controls outside
the globally tested cohort and allowed outcome-related predictors; its
calibration, thresholds, utility and temporal results are not valid substitutes
for the corrected analysis. Some descriptive counts remain correct, but the new
run regenerates them with explicit definitions and missing denominators.

`archive/` preserves earlier experiments and intermediate exports. These files
are retained for traceability and are never loaded as new model evidence.
No output here is evidence of clinical deployment validation.
