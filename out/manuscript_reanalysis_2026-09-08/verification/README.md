# Verification evidence

`pytest.txt` records the full 27-test suite. Its five warnings come from legacy
exploratory workflows (unknown categories and deterministic UMAP threading);
the manuscript-policy tests pass without warnings. `policy_tests.txt` records
13 focused checks covering cohort interpretation, missing predictors, score
calibration, policy comparison and public artifact inventories.

`sphinx.txt` records a successful English HTML documentation build with warnings
treated as errors. A public-only copy of the preserved alternative run was also
verified and its English reports regenerated without patient predictions,
fitted models or the raw registry.

The run manifest records numerical source and input hashes. Every outcome has
`quality_checks.json`; publication checks and the policy comparison provide
additional evidence for the completed run. `release_checks.json` confirms all
eight completed outcomes, matching source hashes, valid Word documents and 14
comment responses. `public_export_check.txt` records byte-identical regeneration
of all three English Markdown reports from the principal public-only package.
`global_subtype_consistency.json` confirms no positive subtype conflicts with an
explicitly negative global testing label. Local execution logs
are excluded from Git.
