# Thrombophilia Risk Mining

This repository contains the RIETE thrombophilia manuscript reanalysis and the
historical exploratory data-mining toolkit. The supported manuscript workflow
uses documented-global-testing eligibility, the investigator-defined routine
panel interpretation, pretest predictors, nested validation,
locked temporal evaluation, and traceable tables and score cards.

## Current manuscript deliverables

The recalculated evidence package is in
[`out/manuscript_reanalysis_2026-09-08/`](out/manuscript_reanalysis_2026-09-08/):

- [`coauthor_responses.md`](out/manuscript_reanalysis_2026-09-08/coauthor_responses.md): replies to all 14 Word comments, also exported to DOCX.
- [`replacement_manuscript_sections.md`](out/manuscript_reanalysis_2026-09-08/replacement_manuscript_sections.md): replacement Methods, Results, interpretation and main tables.
- [`recalculated_supplement.md`](out/manuscript_reanalysis_2026-09-08/recalculated_supplement.md): definitions, missingness, temporal/calibration tables and final development cards.
- `run_manifest.json`: data/code hashes, parameters, software versions and completion status.
- `table5_primary_performance.csv`: paired complete-case comparisons. Native-missing sensitivity results are separate.

The 8 September analysis interprets missing FVL, prothrombin, APS, protein C,
protein S and antithrombin outcomes as negative only within documented global
testing, as specified by the investigators. JAK2 remains explicit positive/negative
only. The 7 September explicit-results run is retained as an alternative policy
analysis under `out/archive/manuscript_reanalysis_2026-09-07/`. The initial audit
is under `out/archive/manuscript_audit_2026-09-07/`; previous exploratory
checkpoints are under `out/archive/checkpoints/`. Historical top-level results have moved to `out/archive/legacy_top_level/`. The original Word documents are preserved locally and the September audit
is retained; legacy outputs are not inputs to the new models. Results are
exploratory research estimates, not clinical deployment validation.

## Reproduce the analysis

Use the raw `data/patD.parquet`, not an already imputed or subtype-filtered file.
Install the analysis environment with `requirements-manuscript.txt`, or use the
project Poetry environment. The full command runs all eight outcomes without
patient subsampling, using five outer and five inner folds.

```bash
python src/manuscript_reanalysis.py \
  --data data/patD.parquet \
  --output-dir out/my_reanalysis
```

To continue an interrupted run with identical input, code and settings:

```bash
python src/manuscript_reanalysis.py \
  --data data/patD.parquet \
  --output-dir out/my_reanalysis \
  --resume
```

To regenerate English reports and figures from finished numerical outputs:

```bash
python src/manuscript_reporting.py out/my_reanalysis
```

Pandoc is optional and creates local DOCX copies. Markdown, aggregate CSV/JSON
and figures are versioned. Patient predictions, fitted models, executed notebook
outputs and build caches stay local. Public manifests do not require these local
files or optional Word exports. The report command can reuse published figures
when local patient predictions are unavailable.
The compatibility command `src/manuscript_support.py` now delegates to the safe
pipeline. For quick integration checks, `--compact --outer-splits 2
--inner-splits 2 --bootstrap 0` reduces search, not the patient cohort; those runs
are explicitly test-only and must not be reported as the final analysis.

## Documentation and tests

- [User and technical manuscript manual](docs/docs_source/manuscript_reanalysis.rst)
- [Technical reference](docs/technical_reference.md)
- [Published HTML documentation](docs/index.html)
- [Developer and validation guide](docs/docs_source/development.rst)

```bash
python -m pytest tests -q
python scripts/check_repository_artifacts.py
python -m sphinx -W --keep-going -b html docs/docs_source docs
```

## Explicit-results alternative and outcome audit

Use `--outcome-policy explicit-results` in a new output directory to exclude
missing subtype results, reproducing the earlier eligibility convention.
The default is `--outcome-policy routine-panel`. Each run records the policy,
raw binary counts and missing-to-negative counts; source outcomes are never
modified. Predictor missingness and complete-case selection are separate steps.

The effect of the updated outcome interpretation is documented in
[outcome_policy_comparison.md](out/manuscript_reanalysis_2026-09-08/outcome_policy_comparison.md).
Reproduce this aggregate comparison with `python scripts/compare_outcome_policies.py`
after both numerical runs are complete, then regenerate reports to refresh the
artifact inventory.

## Historical exploratory workflows

`src/cli.py` provides association mining, generic scores, permutation importance,
Bayesian summaries, clustering and screening. Their preprocessing and population
contracts differ from the supported manuscript workflow. Use them for
exploration; their outputs must not be substituted into the new manuscript
performance tables. The legacy score-screening workflow does not establish the
safety of withholding a test.

The one-off Excel preparation tool remains available:

```bash
python src/patd_spec_tool.py \
  --input-parquet data/patD.parquet \
  --spec-xlsx "data/varibeles explained.xlsx" \
  --output-parquet out/patD_spec_subset.parquet \
  --report-json out/patD_spec_subset_validation.json
```

Its numeric filters can remove rows and its historical missing-value directives
can fill absent observations. Those outputs are intentionally not the source
for the manuscript reanalysis. See the manual for the distinct contracts.
