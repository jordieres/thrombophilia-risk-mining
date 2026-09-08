# Responses to all Word comments — recalculated analysis

All replies below refer to the completed reanalysis directory containing this document. Original comment IDs are preserved (zero-based). The source Word files were not edited in place.

## Applied outcome interpretation

According to the study investigators’ routine-panel interpretation clarified on 8 September 2026, globally tested patients are assumed to have had FVL, prothrombin G20210A, APS, protein C, protein S and antithrombin assessed. Missing results for those six subtypes were therefore interpreted as negative, only when ana_dura was explicitly positive or negative. JAK2 was not considered routine: its missing results remained missing and only explicit positive/negative JAK2 results were eligible. Source labels were preserved and all interpreted negatives were counted separately. This is an explicit clinical registry-coding assumption, not patient-level laboratory adjudication. Nonbinary labels other than missing were not converted to negative.

## Current analysis populations

| label | eligible_n | development_complete_n | temporal_complete_n | missing_excluded_n |
| --- | --- | --- | --- | --- |
| Composite thrombophilia | 22847 | 7209 | 423 | 15215 |
| Factor V Leiden | 22847 | 7209 | 423 | 15215 |
| Prothrombin G20210A | 22847 | 7209 | 423 | 15215 |
| Registry-coded APS | 22847 | 7209 | 423 | 15215 |
| Protein S deficiency | 22847 | 7209 | 423 | 15215 |
| Protein C deficiency | 22847 | 7209 | 423 | 15215 |
| Antithrombin deficiency | 22847 | 7209 | 423 | 15215 |
| JAK2 mutation | 2239 | 648 | 54 | 1537 |

## Current primary performance

| Outcome | Model | N | Positive | AUC_95CI | Sensitivity | Specificity | PPV | NPV | Avoided_per_1000 | Missed_per_1000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Composite thrombophilia | Logistic LASSO | 7209 | 2801 | 0.584 [0.571, 0.596] | 90.3% | 16.1% | 40.6% | 72.2% | 136.400 | 37.900 |
| Composite thrombophilia | Automatic integer score | 7209 | 2801 | 0.584 [0.571, 0.596] | 90.1% | 16.3% | 40.6% | 72.1% | 138.000 | 38.600 |
| Composite thrombophilia | XGBoost | 7209 | 2801 | 0.591 [0.578, 0.605] | 90.8% | 16.8% | 40.9% | 74.0% | 138.400 | 35.900 |
| Factor V Leiden | Logistic LASSO | 7209 | 806 | 0.619 [0.598, 0.639] | 91.1% | 20.5% | 12.6% | 94.8% | 191.700 | 10.000 |
| Factor V Leiden | Automatic integer score | 7209 | 806 | 0.619 [0.598, 0.639] | 91.2% | 20.2% | 12.6% | 94.8% | 189.500 | 9.800 |
| Factor V Leiden | XGBoost | 7209 | 806 | 0.615 [0.595, 0.634] | 90.7% | 20.2% | 12.5% | 94.5% | 190.000 | 10.400 |
| Prothrombin G20210A | Logistic LASSO | 7209 | 592 | 0.546 [0.523, 0.569] | 90.9% | 14.1% | 8.6% | 94.5% | 136.800 | 7.500 |
| Prothrombin G20210A | Automatic integer score | 7209 | 592 | 0.547 [0.524, 0.570] | 91.4% | 13.4% | 8.6% | 94.6% | 130.100 | 7.100 |
| Prothrombin G20210A | XGBoost | 7209 | 592 | 0.558 [0.537, 0.582] | 90.4% | 16.0% | 8.8% | 94.9% | 154.900 | 7.900 |
| Registry-coded APS | Logistic LASSO | 7209 | 636 | 0.596 [0.572, 0.616] | 91.4% | 16.3% | 9.6% | 95.1% | 156.300 | 7.600 |
| Registry-coded APS | Automatic integer score | 7209 | 636 | 0.595 [0.572, 0.615] | 91.0% | 16.3% | 9.5% | 95.0% | 156.900 | 7.900 |
| Registry-coded APS | XGBoost | 7209 | 636 | 0.612 [0.588, 0.631] | 92.0% | 16.8% | 9.7% | 95.6% | 159.900 | 7.100 |
| Protein S deficiency | Logistic LASSO | 7209 | 261 | 0.546 [0.512, 0.583] | 83.1% | 24.5% | 4.0% | 97.5% | 242.200 | 6.100 |
| Protein S deficiency | Automatic integer score | 7209 | 261 | 0.546 [0.515, 0.586] | 88.9% | 14.9% | 3.8% | 97.3% | 147.600 | 4.000 |
| Protein S deficiency | XGBoost | 7209 | 261 | 0.558 [0.524, 0.591] | 92.0% | 12.0% | 3.8% | 97.5% | 118.700 | 2.900 |
| Protein C deficiency | Logistic LASSO | 7209 | 120 | 0.503 [0.453, 0.552] | 73.3% | 26.4% | 1.7% | 98.3% | 264.500 | 4.400 |
| Protein C deficiency | Automatic integer score | 7209 | 120 | 0.502 [0.452, 0.549] | 89.2% | 11.2% | 1.7% | 98.4% | 112.400 | 1.800 |
| Protein C deficiency | XGBoost | 7209 | 120 | 0.576 [0.520, 0.630] | 89.2% | 14.8% | 1.7% | 98.8% | 146.900 | 1.800 |
| Antithrombin deficiency | Logistic LASSO | 7209 | 92 | 0.549 [0.483, 0.605] | 83.7% | 19.8% | 1.3% | 98.9% | 197.400 | 2.100 |
| Antithrombin deficiency | Automatic integer score | 7209 | 92 | 0.559 [0.493, 0.616] | 95.7% | 5.6% | 1.3% | 99.0% | 55.600 | 0.600 |
| Antithrombin deficiency | XGBoost | 7209 | 92 | 0.619 [0.566, 0.680] | 90.2% | 19.5% | 1.4% | 99.4% | 193.600 | 1.200 |
| JAK2 mutation | Logistic LASSO | 648 | 15 | 0.688 [0.498, 0.865] | 73.3% | 18.3% | 2.1% | 96.7% | 185.200 | 6.200 |
| JAK2 mutation | Automatic integer score | 648 | 15 | 0.679 [0.482, 0.861] | 86.7% | 7.7% | 2.2% | 96.1% | 78.700 | 3.100 |
| JAK2 mutation | XGBoost | 648 | 15 | 0.700 [0.578, 0.854] | 93.3% | 29.5% | 3.0% | 99.5% | 290.100 | 1.500 |

## Article comment 0: Missing-data reporting

We distinguish missing outcome labels from missing predictors. Routine subtype outcomes are interpreted according to the declared policy, with JAK2 always requiring explicit results. Predictor missingness has now been recalculated before modelling, separating unknown from explicitly not-performed values. The full table is supplement_missingness.csv and each outcome has its own missingness.csv. The primary comparison uses complete cases for the development-defined candidate set after excluding predictors with >40% missingness; LASSO uses no imputation. XGBoost on the same complete cases provides a paired comparison. A separate XGBoost analysis includes incomplete observations using true NaN blocks and native missing handling. Included/excluded comparisons are exported for every outcome. No unknown history is silently coded as absent. See model_cohort_flow.csv for the actual analytical denominators.

## Article comment 1: Confirm subtype-specific tested controls

According to the study investigators’ routine-panel interpretation clarified on 8 September 2026, globally tested patients are assumed to have had FVL, prothrombin G20210A, APS, protein C, protein S and antithrombin assessed. Missing results for those six subtypes were therefore interpreted as negative, only when ana_dura was explicitly positive or negative. JAK2 was not considered routine: its missing results remained missing and only explicit positive/negative JAK2 results were eligible. Source labels were preserved and all interpreted negatives were counted separately. This is an explicit clinical registry-coding assumption, not patient-level laboratory adjudication. Nonbinary labels other than missing were not converted to negative. This routine-panel interpretation is the principal paper analysis. Explicit prior carrier status/known APS remains excluded. Prediction IDs and their outcome labels are checked against this declared definition. Neither policy admits patients outside documented global testing. The raw, interpreted and analytical denominators are reported separately in supplement_outcome_denominators.csv and table5_primary_performance.csv.

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

According to the study investigators’ routine-panel interpretation clarified on 8 September 2026, globally tested patients are assumed to have had FVL, prothrombin G20210A, APS, protein C, protein S and antithrombin assessed. Missing results for those six subtypes were therefore interpreted as negative, only when ana_dura was explicitly positive or negative. JAK2 was not considered routine: its missing results remained missing and only explicit positive/negative JAK2 results were eligible. Source labels were preserved and all interpreted negatives were counted separately. This is an explicit clinical registry-coding assumption, not patient-level laboratory adjudication. Nonbinary labels other than missing were not converted to negative. Supplementary Table S2 separates raw explicit binary results, recorded positives, missing-to-negative interpretations, remaining unavailable results and known-carrier exclusions. Positivity uses the interpreted tested denominator for the chosen policy, not the proportion of diagnoses among globally positive patients. The table below gives availability and interpretation before predictive exclusions:

| label | tested_binary_n | tested_positive_n | missing_interpreted_negative_n | interpreted_tested_n | positive_percent | tested_unavailable_n | known_excluded_n | eligible_n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Factor V Leiden | 10638 | 2048 | 12236 | 22874 | 8.953 | 12236 | 27 | 22847 |
| Prothrombin G20210A | 10376 | 1602 | 12498 | 22874 | 7.004 | 12498 | 27 | 22847 |
| Registry-coded APS | 10710 | 1908 | 12164 | 22874 | 8.341 | 12164 | 27 | 22847 |
| Protein S deficiency | 10315 | 757 | 12559 | 22874 | 3.309 | 12559 | 27 | 22847 |
| Protein C deficiency | 10275 | 356 | 12599 | 22874 | 1.556 | 12599 | 27 | 22847 |
| Antithrombin deficiency | 10333 | 260 | 12541 | 22874 | 1.137 | 12541 | 27 | 22847 |
| JAK2 mutation | 2246 | 61 | 0 | 2246 | 2.716 | 20628 | 7 | 2239 |

## Where to find the manuscript-ready text

replacement_manuscript_sections.md/.docx contains the replacement Methods, Results, conclusion and main tables. recalculated_supplement.md/.docx contains definitions, missingness, temporal/calibration tables and all final score cards. CSV files are the numeric source of truth; figures/ contains standalone PNG and SVG files.

## Remaining limitations that wording cannot remove

No independent assay-completion flag, laboratory repeat-confirmation record, anticoagulant-at-assay timestamp, or centre/country validation identifier was available. Those limitations are reported explicitly. The routine-panel interpretation comes from the study investigators, not from independent confirmation in this extract. Complete-case attrition and the exploratory nature of the cards remain substantive limitations.
