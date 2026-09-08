# Responses to all Word comments — recalculated analysis

All replies below refer to the completed reanalysis directory containing this document. Original comment IDs are preserved (zero-based). The source Word files were not edited in place.

## Current analysis populations

| label | eligible_n | development_complete_n | temporal_complete_n | missing_excluded_n |
| --- | --- | --- | --- | --- |
| Composite thrombophilia | 22847 | 7209 | 423 | 15215 |
| Factor V Leiden | 10618 | 5864 | 102 | 4652 |
| Prothrombin G20210A | 10356 | 5758 | 93 | 4505 |
| Registry-coded APS | 10685 | 5866 | 115 | 4704 |
| Protein S deficiency | 10295 | 5723 | 102 | 4470 |
| Protein C deficiency | 10255 | 5711 | 95 | 4449 |
| Antithrombin deficiency | 10313 | 5742 | 98 | 4473 |
| JAK2 mutation | 2239 | 648 | 54 | 1537 |

## Current primary performance

| Outcome | Model | N | Positive | AUC_95CI | Sensitivity | Specificity | PPV | NPV | Avoided_per_1000 | Missed_per_1000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Composite thrombophilia | Logistic LASSO | 7209 | 2801 | 0.584 [0.571, 0.596] | 90.3% | 16.1% | 40.6% | 72.2% | 136.400 | 37.900 |
| Composite thrombophilia | Automatic integer score | 7209 | 2801 | 0.584 [0.571, 0.596] | 90.1% | 16.3% | 40.6% | 72.1% | 138.000 | 38.600 |
| Composite thrombophilia | XGBoost | 7209 | 2801 | 0.591 [0.578, 0.605] | 90.8% | 16.8% | 40.9% | 74.0% | 138.400 | 35.900 |
| Factor V Leiden | Logistic LASSO | 5864 | 1167 | 0.623 [0.607, 0.642] | 90.0% | 19.1% | 21.7% | 88.5% | 173.100 | 20.000 |
| Factor V Leiden | Automatic integer score | 5864 | 1167 | 0.623 [0.606, 0.642] | 90.1% | 18.9% | 21.6% | 88.5% | 171.600 | 19.800 |
| Factor V Leiden | XGBoost | 5864 | 1167 | 0.623 [0.606, 0.641] | 90.3% | 18.7% | 21.6% | 88.6% | 169.000 | 19.300 |
| Prothrombin G20210A | Logistic LASSO | 5758 | 850 | 0.565 [0.543, 0.583] | 89.8% | 16.2% | 15.7% | 90.2% | 153.500 | 15.100 |
| Prothrombin G20210A | Automatic integer score | 5758 | 850 | 0.565 [0.542, 0.584] | 90.4% | 15.8% | 15.7% | 90.5% | 149.200 | 14.200 |
| Prothrombin G20210A | XGBoost | 5758 | 850 | 0.573 [0.551, 0.593] | 90.4% | 15.0% | 15.6% | 90.0% | 142.400 | 14.200 |
| Registry-coded APS | Logistic LASSO | 5866 | 851 | 0.612 [0.592, 0.633] | 90.7% | 17.3% | 15.7% | 91.7% | 161.600 | 13.500 |
| Registry-coded APS | Automatic integer score | 5866 | 851 | 0.612 [0.593, 0.632] | 90.6% | 17.4% | 15.7% | 91.6% | 162.600 | 13.600 |
| Registry-coded APS | XGBoost | 5866 | 851 | 0.602 [0.582, 0.622] | 91.1% | 17.1% | 15.7% | 91.9% | 159.200 | 13.000 |
| Protein S deficiency | Logistic LASSO | 5723 | 384 | 0.550 [0.527, 0.579] | 88.0% | 15.6% | 7.0% | 94.8% | 153.200 | 8.000 |
| Protein S deficiency | Automatic integer score | 5723 | 384 | 0.553 [0.529, 0.583] | 88.5% | 14.9% | 7.0% | 94.7% | 146.400 | 7.700 |
| Protein S deficiency | XGBoost | 5723 | 384 | 0.566 [0.543, 0.594] | 89.8% | 15.2% | 7.1% | 95.4% | 148.300 | 6.800 |
| Protein C deficiency | Logistic LASSO | 5711 | 180 | 0.546 [0.507, 0.586] | 89.4% | 17.8% | 3.4% | 98.1% | 175.600 | 3.300 |
| Protein C deficiency | Automatic integer score | 5711 | 180 | 0.549 [0.512, 0.586] | 91.7% | 16.3% | 3.4% | 98.4% | 160.400 | 2.600 |
| Protein C deficiency | XGBoost | 5711 | 180 | 0.586 [0.552, 0.629] | 91.1% | 19.8% | 3.6% | 98.6% | 194.400 | 2.800 |
| Antithrombin deficiency | Logistic LASSO | 5742 | 127 | 0.595 [0.551, 0.649] | 86.6% | 18.6% | 2.3% | 98.4% | 184.800 | 3.000 |
| Antithrombin deficiency | Automatic integer score | 5742 | 127 | 0.595 [0.552, 0.649] | 87.4% | 18.2% | 2.4% | 98.5% | 180.400 | 2.800 |
| Antithrombin deficiency | XGBoost | 5742 | 127 | 0.654 [0.616, 0.705] | 89.0% | 22.3% | 2.5% | 98.9% | 220.800 | 2.400 |
| JAK2 mutation | Logistic LASSO | 648 | 15 | 0.688 [0.498, 0.865] | 73.3% | 18.3% | 2.1% | 96.7% | 185.200 | 6.200 |
| JAK2 mutation | Automatic integer score | 648 | 15 | 0.679 [0.482, 0.861] | 86.7% | 7.7% | 2.2% | 96.1% | 78.700 | 3.100 |
| JAK2 mutation | XGBoost | 648 | 15 | 0.700 [0.578, 0.854] | 93.3% | 29.5% | 3.0% | 99.5% | 290.100 | 1.500 |

## Article comment 0: Missing-data reporting

We have now recalculated missingness before modelling, separating unknown from explicitly not-performed values. The full table is supplement_missingness.csv and each outcome has its own missingness.csv. The primary comparison uses complete cases for the development-defined candidate set after excluding predictors with >40% missingness; LASSO uses no imputation. XGBoost on the same complete cases provides a paired comparison. A separate XGBoost analysis includes incomplete observations using true NaN blocks and native missing handling. Included/excluded comparisons are exported for every outcome. No unknown history is silently coded as absent. See model_cohort_flow.csv for the actual analytical denominators.

## Article comment 1: Confirm subtype-specific tested controls

The historical statement was not supported, but the code now requires both a documented global testing label and a binary registered subtype result, and excludes explicit prior carrier status/known APS. Prediction IDs are checked against that eligibility definition. However, the extract has no separate assay-performed flag: we must say “binary registered subtype results among globally tested patients”, not claim independently verified performance of every assay. The new denominators and results are in supplement_outcome_denominators.csv and table5_primary_performance.csv.

## Article comment 2: Confirm Figure 1 numbers

The complete registry contains 119,449 patients; 22,874 have documented testing, with 8,568 positive and 14,306 negative global evaluations. The remaining 96,575 are explicitly untested or unknown. These counts reconcile exactly. The new figure separates the 27 known-carrier/known-APS exclusions and the outcome-specific complete-case development and temporal samples. Use figures/cohort_flow.png and model_cohort_flow.csv. The old 8,345/13,770 counts should not be combined with the full-registry tested count.

## Article comment 3: Perform missingness analyses or remove the sentence

This work has now been performed. The replacement Methods describes the actual 40% development missingness threshold, the primary complete-case definition, the native-missing XGBoost sensitivity analysis, and comparisons of included versus excluded patients. The candidate set is broader than the final nonzero score terms, so we explicitly describe complete cases for retained candidates rather than only for the final score. Remove the unspecified “Table X” reference and cite recalculated Supplementary Table S3.

## Article comment 4: Locate previous missingness work

The old Excel validation JSON files were preprocessing audits rather than manuscript missingness tables. They are now superseded for this paper by supplement_missingness.csv, each outcome/missingness.csv, candidate_availability.csv and included_vs_excluded.csv. These files distinguish original missingness, quality failures and modelling exclusion. Their generation is part of the supported reanalysis command.

## Article comment 5: Negative or positive association rules?

Negative is correct for this exploratory section. The new FP-Growth export explicitly requires a negative-result consequent and retains 0 rules under documented thresholds. Positive thrombophilia remains the outcome for the predictive models. Replace the old rule counts and examples with table3_recalculated_profiles.csv and supplement_negative_association_rules.csv; joint rule support and antecedent support are now distinguished.

## Article comment 6: Positive or negative score orientation?

The new LASSO models predict a positive registered result. Integer points preserve the signs of their coefficients, so higher total scores indicate greater predicted positivity and a positive decision is score ≥ its development cutoff. The score-to-probability mapping has a nonnegative slope. This orientation is now consistent for both the automatic and composite guided comparison. It supersedes the historical guided card that used the opposite inequality. Each final card reports exact variable/category identities, signed points and its locked threshold.

## Article comment 7: Correct and complete Table 1

Table 1 has been rebuilt from mutually exclusive tested versus not-tested/unknown groups in the original registry. It reports observed denominators, missing counts, standardized differences and newly calculated descriptive p-values; no old p-values were carried forward. Table 2 is also rebuilt from the same source. Use table1_baseline.csv and table2_positive_negative.csv, or the formatted replacement manuscript tables. Percentages now use observed values rather than equating unknown history with absence.

## Article comment 8: Shorten the sex comparison

We suggest retaining one descriptive sentence in the main Results and moving the full effect sizes and Bayesian conditional probabilities to the supplement. The analysis addresses testing selection and yield but does not establish clinical testing criteria. sex_testing_yield.csv and sex_effect_sizes.csv contain the recalculated counts, rates and intervals from the same original registry.

## Article comment 9: Sex, hormone/pregnancy testing and recurrence

The recalculated sex difference can be retained as a descriptive finding. No recurrence model or adjudicated testing-indication analysis has been conducted, so we cannot attribute it to recurrent VTE, contraceptive use or pregnancy. Those are hypotheses, not explanations demonstrated by these results. An additional important correction is that trat_est means statin treatment; hormone exposure is fr_estro. The prior score label “estrogen treatment” for trat_est was erroneous.

## Article comment 10: Complete Table 5 and report both XGBoost and integer scores

Both models are retained because their comparison is a study objective. They now use exactly the same complete-case patients in the primary table; the full logistic LASSO benchmark is also supplied. N, positives, AUC, TP/FP/TN/FN, all threshold metrics, calibration and resource calculations come from the same stored predictions. The native-missing tree results are a separate sensitivity table. Antithrombin and JAK2 have been recomputed; JAK2 remains descriptive because of its small event count. The observed sensitivity is allowed to fall below 90% in validation: the 90% target selects training thresholds and must not be enforced retrospectively on held-out patients.

## Article comment 11: Identify the calibration figures and numbers

The authoritative files are supplement_calibration.csv, all_model_metrics.csv and figures/<outcome>_validation.png. Calibration now evaluates the actual point-score probability separately from the full logistic prediction. Recalculated Supplementary Table S6 reports Brier, MACE and ECE with explicit bin definitions. The old MACE values and placeholder Figure X should be removed. No number in the legacy calibration summary is reused.

## Article comment 12: Identify and verify temporal validation

Temporal validation is now a fixed 2021/2022 split. All category vocabularies, supervised screening, hyperparameters, score cards, probability mappings and thresholds are fitted in development only. supplement_temporal_validation.csv identifies each outcome, model, N, events and confusion matrix; the formatted primary table is Supplementary Table S5. Undefined NPV is reported as undefined, not zero. Small holdout/event counts are displayed and must accompany interpretation. The previous temporal figures have been replaced rather than relabelled.

## Supplement comment 0: Missing values in subtype distribution

Supplementary Table S2 now separates globally tested patients with a binary subtype result, positive counts, unavailable subtype results and the further known-carrier exclusions used for modelling. Positivity uses the specific binary-result denominator; it is not mixed with the distribution among globally positive patients. Unknown or not-performed subtype results are not assumed negative. The exact raw-availability numbers before predictive exclusions are:

| label | tested_binary_n | tested_positive_n | positive_percent | tested_unavailable_n | known_excluded_n | eligible_n |
| --- | --- | --- | --- | --- | --- | --- |
| Factor V Leiden | 10638 | 2048 | 19.252 | 12236 | 20 | 10618 |
| Prothrombin G20210A | 10376 | 1602 | 15.439 | 12498 | 20 | 10356 |
| Registry-coded APS | 10710 | 1908 | 17.815 | 12164 | 25 | 10685 |
| Protein S deficiency | 10315 | 757 | 7.339 | 12559 | 20 | 10295 |
| Protein C deficiency | 10275 | 356 | 3.465 | 12599 | 20 | 10255 |
| Antithrombin deficiency | 10333 | 260 | 2.516 | 12541 | 20 | 10313 |
| JAK2 mutation | 2246 | 61 | 2.716 | 20628 | 7 | 2239 |

## Where to find the manuscript-ready text

replacement_manuscript_sections.md/.docx contains the replacement Methods, Results, conclusion and main tables. recalculated_supplement.md/.docx contains definitions, missingness, temporal/calibration tables and all final score cards. CSV files are the numeric source of truth; figures/ contains standalone PNG and SVG files.

## Remaining limitations that wording cannot remove

No independent assay-completion flag, laboratory repeat-confirmation record, anticoagulant-at-assay timestamp, or centre/country validation identifier was available. Those limitations are reported explicitly. No new clinical facts were inferred from their absence. Complete-case attrition and the exploratory nature of the cards remain substantive limitations.
