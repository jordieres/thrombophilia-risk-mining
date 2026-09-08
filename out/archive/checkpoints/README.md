# Historical exploratory checkpoints

These association-explorer and contrast-mining checkpoints were moved from
`out/checkpoints/` during the manuscript output cleanup. They are independent
of the current manuscript analysis. Configuration and feature-profile JSON
files are versioned; intermediate Parquet files are preserved locally.

To deliberately resume these experiments, use the original settings with
`--checkpoint-dir out/archive/checkpoints --resume`. New exploratory runs may
create `out/checkpoints/` again. Current manuscript `completed.json` files stay
with their outcomes and have not been relocated.
