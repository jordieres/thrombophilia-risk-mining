# Responses to the new methodological review

1. **Missing predictors / all eligible patients.** The new models use multiple imputation within validation partitions; no eligible patient is excluded for missing predictors. The seven routine outcomes use the common eligible population; JAK2 still requires an observed result. Imputation-specific predictions are averaged; Rubin coefficient pooling is not claimed for selected LASSO models.
2. **Continuous information and screening.** Continuous values are retained, logistic models include splines, XGBoost uses continuous measurements, and univariable significance screening is removed. We do not assume that the old negative inference will survive this analysis.
3. **Decision curves.** Held-out net benefit is exported and plotted against testing all/none. The 1–50% range is exploratory pending clinical agreement; no universal journal requirement is asserted.
4. **FP-Growth discrepancy.** Association-rule mining is removed from the new manuscript package. Previously examined clinical profiles are reported only as observed negative-result frequencies, with explicit missing-component denominators. Confidence/lift thresholds and association-rule claims are absent.

See replacement_manuscript_sections.md and the aggregate CSVs for the executed settings, results and limitations. Previous result packages are retained separately.
