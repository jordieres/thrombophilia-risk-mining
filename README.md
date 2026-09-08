# Thrombophilia Risk Mining

This repository contains the RIETE thrombophilia manuscript reanalysis and the
historical exploratory data-mining toolkit. The supported manuscript workflow
uses explicit tested-only eligibility, pretest predictors, nested validation,
locked temporal evaluation, and traceable tables and score cards.

## Current manuscript deliverables

The recalculated evidence package is in
[`out/manuscript_reanalysis_2026-09-07/`](out/manuscript_reanalysis_2026-09-07/):

- [`coauthor_responses.md`](out/manuscript_reanalysis_2026-09-07/coauthor_responses.md): replies to all 14 Word comments, also exported to DOCX.
- [`replacement_manuscript_sections.md`](out/manuscript_reanalysis_2026-09-07/replacement_manuscript_sections.md): replacement Methods, Results, interpretation and main tables.
- [`recalculated_supplement.md`](out/manuscript_reanalysis_2026-09-07/recalculated_supplement.md): definitions, missingness, temporal/calibration tables and final development cards.
- `run_manifest.json`: data/code hashes, parameters, software versions and completion status.
- `table5_primary_performance.csv`: paired complete-case comparisons. Native-missing sensitivity results are separate.

These outputs supersede the previous top-level `out/coauthor_response_review.md`
and associated model summaries. The original Word documents and September audit
are preserved; legacy outputs are not inputs to the new models. Results are
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

Pandoc is optional and creates DOCX copies; Markdown/CSV are always available.
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
python -m sphinx -W --keep-going -b html docs/docs_source docs
```

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
