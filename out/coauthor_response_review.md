# Response to Methodological Comments

## 1. Target population and scope
The repository confirms that the predictive models operate in patients who underwent thrombophilia testing, not in the whole VTE registry.

- Full registry rows: **119,449**.
- Tested subgroup (`Buscada positivo` or `Buscada negativo`): **22,874**.
- Explicitly not tested (`No buscada`): **35,784**.
- Therefore, model outputs should be described as the probability of a positive thrombophilia result **among already selected patients**, not the prevalence of thrombophilia in the whole VTE population.

### Tested vs not tested baseline comparison
| Variable              | Tested             | Not_Tested          | Standardized_Difference   |
|:----------------------|:-------------------|:--------------------|:--------------------------|
| N                     | 22874              | 35784               |                           |
| Age, mean (SD)        | 55.2 (18.1)        | 70.7 (14.5)         | -0.950                    |
| Female sex            | 10781 (47.1%)      | 18666 (52.2%)       | -0.101                    |
| Active cancer         | 2671 (11.7%)       | 11328 (31.7%)       | -0.500                    |
| Immobilization        | 4361 (19.1%)       | 9881 (27.6%)        | -0.203                    |
| Prior VTE             | 3062 (13.4%)       | 4644 (13.0%)        | 0.012                     |
| Known lupus           | 69 (0.3%)          | 36 (0.1%)           | 0.045                     |
| Known APS             | 27 (0.1%)          | 3 (0.0%)            | 0.044                     |
| Hemoglobin, mean (SD) | 13.46 (2.43)       | 12.72 (2.18)        | 0.320                     |
| Leukocytes, mean (SD) | 210.62 (30241.75)  | 11.87 (238.33)      | 0.009                     |
| D-dimer, mean (SD)    | 1360.25 (66333.76) | 1995.82 (120906.33) | -0.007                    |

### Outcome prevalence among tested patients
| Outcome                   | Column   |   Tested_N |   Positive_N |   Positive_% |
|:--------------------------|:---------|-----------:|-------------:|-------------:|
| Antiphospholipid syndrome | var161   |      10710 |         1908 |        17.82 |
| Factor V Leiden           | var156   |      10638 |         2048 |        19.25 |
| Protein C deficiency      | var154   |      10275 |          356 |         3.46 |
| Protein S deficiency      | var155   |      10315 |          757 |         7.34 |
| Prothrombin G20210A       | var157   |      10376 |         1602 |        15.44 |

## 2. Outcome-definition caveats
- The local dataset does not expose anticoagulant treatment timestamps at the moment of thrombophilia testing, so potential heparin/VKA/DOAC interference cannot be adjudicated from this repository snapshot.
- The registry snapshot also does not document confirmatory repeat antiphospholipid antibody testing. APS should therefore be described as a registry-coded post-thrombosis outcome, not as laboratory-adjudicated persistent APS.

## 3. Confusion-matrix audit
The existing score artifacts were converted into selected-threshold confusion matrices so denominators are explicit.

| Outcome              | Model                            |   Threshold | Decision_Rule      |   TP |    FP |    TN |   FN |   Sensitivity |   Specificity |   PPV |   NPV |
|:---------------------|:---------------------------------|------------:|:-------------------|-----:|------:|------:|-----:|--------------:|--------------:|------:|------:|
| Protein C deficiency | Automatic Integer Score          |           1 | score >= threshold |  321 | 23520 |  6842 |   17 |         0.95  |         0.225 | 0.013 | 0.998 |
| Protein C deficiency | Association-Guided Integer Score |           8 | score <= threshold |  307 | 27658 |  2704 |   31 |         0.908 |         0.089 | 0.011 | 0.989 |
| Protein S deficiency | Automatic Integer Score          |           1 | score >= threshold |  670 | 21482 |  8488 |   60 |         0.918 |         0.283 | 0.03  | 0.993 |
| Protein S deficiency | Association-Guided Integer Score |           7 | score <= threshold |  717 | 29280 |   690 |   13 |         0.982 |         0.023 | 0.024 | 0.982 |
| Factor V Leiden      | Automatic Integer Score          |           1 | score >= threshold | 1865 | 17045 | 11675 |  115 |         0.942 |         0.407 | 0.099 | 0.99  |
| Factor V Leiden      | Association-Guided Integer Score |           6 | score <= threshold | 1787 | 25487 |  3233 |  193 |         0.903 |         0.113 | 0.066 | 0.944 |
| Prothrombin G20210A  | Automatic Integer Score          |           1 | score >= threshold | 1466 | 17746 | 11395 |   93 |         0.94  |         0.391 | 0.076 | 0.992 |
| Prothrombin G20210A  | Association-Guided Integer Score |           1 | score <= threshold | 1527 | 28445 |   696 |   32 |         0.979 |         0.024 | 0.051 | 0.956 |

## 4. Practical interpretation of high NPV
High NPV alone is not enough when prevalence is low. The table below translates the selected operating points into tests avoided and true-positive misses per 1,000 tested patients.

| Outcome              | Model                            |   Selected_Threshold |   Sensitivity |   Specificity |   PPV |   NPV |   Tests_Avoided_per_1000 |   Missed_True_Positives_per_1000 |
|:---------------------|:---------------------------------|---------------------:|--------------:|--------------:|------:|------:|-------------------------:|---------------------------------:|
| Protein C deficiency | Automatic Integer Score          |                    1 |          0.95 |          0.23 |  0.01 |  1    |                   223.42 |                             0.55 |
| Protein C deficiency | Association-Guided Integer Score |                    8 |          0.91 |          0.09 |  0.01 |  0.99 |                    89.09 |                             1.01 |
| Protein S deficiency | Automatic Integer Score          |                    1 |          0.92 |          0.28 |  0.03 |  0.99 |                   278.44 |                             1.95 |
| Protein S deficiency | Association-Guided Integer Score |                    7 |          0.98 |          0.02 |  0.02 |  0.98 |                    22.9  |                             0.42 |
| Factor V Leiden      | Automatic Integer Score          |                    1 |          0.94 |          0.41 |  0.1  |  0.99 |                   384.04 |                             3.75 |
| Factor V Leiden      | Association-Guided Integer Score |                    6 |          0.9  |          0.11 |  0.07 |  0.94 |                   111.6  |                             6.29 |
| Prothrombin G20210A  | Automatic Integer Score          |                    1 |          0.94 |          0.39 |  0.08 |  0.99 |                   374.2  |                             3.03 |
| Prothrombin G20210A  | Association-Guided Integer Score |                    1 |          0.98 |          0.02 |  0.05 |  0.96 |                    23.71 |                             1.04 |

## 5. Temporal validation
A lightweight temporal holdout was feasible because `fecha_di` is available from 2001 to 2024. Development years were up to **2021**, and validation used later years.

| Outcome                   | Column   |   Cutoff_Year |   Development_N |   Validation_N |   Selected_Threshold |   Sensitivity |   Specificity |   PPV |   NPV |   TP |   FP |   TN |   FN |
|:--------------------------|:---------|--------------:|----------------:|---------------:|---------------------:|--------------:|--------------:|------:|------:|-----:|-----:|-----:|-----:|
| Protein C deficiency      | var154   |          2021 |           30814 |            222 |                    9 |         0.833 |         0.12  | 0.026 | 0.963 |    5 |  190 |   26 |    1 |
| Protein S deficiency      | var155   |          2021 |           30845 |            231 |                   10 |         1     |         0.005 | 0.135 | 1     |   31 |  199 |    1 |    0 |
| Factor V Leiden           | var156   |          2021 |           31159 |            240 |                   11 |         1     |         0.03  | 0.306 | 1     |   72 |  163 |    5 |    0 |
| Prothrombin G20210A       | var157   |          2021 |           30914 |            223 |                   12 |         0.948 |         0.048 | 0.259 | 0.727 |   55 |  157 |    8 |    3 |
| Antiphospholipid syndrome | var161   |          2021 |           31202 |            269 |                   16 |         0.984 |         0     | 0.453 | 0     |  121 |  146 |    0 |    2 |

No country or center variable was identifiable in the local parquet columns inspected here, so leave-country or leave-center internal-external validation could not be reproduced from the current repository snapshot.


## 5A. Calibration
A lightweight calibration summary was added using the available patient-level probability exports for `var154`-`var157` and an isolated APS run for `var161`. Lower mean absolute calibration error indicates closer agreement between predicted and observed risk.

| Outcome                   | Model                            |   Mean_Absolute_Calibration_Error |
|:--------------------------|:---------------------------------|----------------------------------:|
| Antiphospholipid syndrome | Automatic Integer Score          |                             0.093 |
| Factor V Leiden           | Association-Guided Integer Score |                             0.355 |
| Factor V Leiden           | Automatic Integer Score          |                             0.268 |
| Protein C deficiency      | Association-Guided Integer Score |                             0.439 |
| Protein C deficiency      | Automatic Integer Score          |                             0.317 |
| Protein S deficiency      | Association-Guided Integer Score |                             0.426 |
| Protein S deficiency      | Automatic Integer Score          |                             0.325 |
| Prothrombin G20210A       | Association-Guided Integer Score |                             0.376 |
| Prothrombin G20210A       | Automatic Integer Score          |                             0.288 |

Interactive plot: `calibration_overview.html`.

## 6. Interpretation of simplified score cut-points
- The current automatic score is still partly sample-derived because it bins continuous predictors empirically.
- Narrow leukocyte, hemoglobin, D-dimer, or age intervals should therefore be reported as exploratory score-card cut-points requiring external validation, not as stable biological thresholds.

## 7. Recommended manuscript edits
1. State explicitly that the models target positivity among **tested** patients.
2. Redefine baseline tables as mutually exclusive `tested` vs `not tested` groups and emphasize standardized differences instead of p-values.
3. Report TP/FP/TN/FN and practical utility metrics alongside NPV.
4. Add a limitations sentence that treatment-at-testing and confirmatory APS testing were unavailable in the registry-derived dataset.
5. Present temporal validation as additional internal validation, and note that center/country validation remains pending because those fields were not available in this repository snapshot.


## Verification
A broad repository test pass was completed on **July 25, 2026** with plugin autoload disabled to avoid the unrelated `dash` pytest plugin failure previously seen in this environment.

- Command: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`
- Result: **14 passed** in **36.44 s**.
- Additional check: `python -m py_compile src/*.py` passed.
- Residual warnings came from third-party libraries (`joblib`, `sklearn`, `umap`) and did not cause test failures.


## Publication-Ready Tables
The following compact tables are formatted for direct adaptation into the manuscript or supplementary appendix.

### Table A. Tested vs not tested cohorts
| Variable              | Tested cohort      | Not tested cohort   | Std diff   |
|:----------------------|:-------------------|:--------------------|:-----------|
| N                     | 22874              | 35784               |            |
| Age, mean (SD)        | 55.2 (18.1)        | 70.7 (14.5)         | -0.950     |
| Female sex            | 10781 (47.1%)      | 18666 (52.2%)       | -0.101     |
| Active cancer         | 2671 (11.7%)       | 11328 (31.7%)       | -0.500     |
| Immobilization        | 4361 (19.1%)       | 9881 (27.6%)        | -0.203     |
| Prior VTE             | 3062 (13.4%)       | 4644 (13.0%)        | 0.012      |
| Known lupus           | 69 (0.3%)          | 36 (0.1%)           | 0.045      |
| Known APS             | 27 (0.1%)          | 3 (0.0%)            | 0.044      |
| Hemoglobin, mean (SD) | 13.46 (2.43)       | 12.72 (2.18)        | 0.320      |
| Leukocytes, mean (SD) | 210.62 (30241.75)  | 11.87 (238.33)      | 0.009      |
| D-dimer, mean (SD)    | 1360.25 (66333.76) | 1995.82 (120906.33) | -0.007     |

### Table B. Outcome prevalence among tested patients
| Outcome                   |   Tested n |   Positive n |   Positive % |
|:--------------------------|-----------:|-------------:|-------------:|
| Antiphospholipid syndrome |      10710 |         1908 |        17.82 |
| Factor V Leiden           |      10638 |         2048 |        19.25 |
| Protein C deficiency      |      10275 |          356 |         3.46 |
| Protein S deficiency      |      10315 |          757 |         7.34 |
| Prothrombin G20210A       |      10376 |         1602 |        15.44 |

### Table C. Selected-threshold confusion-matrix summary
| Outcome              | Model                            |   TP |    FP |    TN |   FN |   Sensitivity |   Specificity |   PPV |   NPV |
|:---------------------|:---------------------------------|-----:|------:|------:|-----:|--------------:|--------------:|------:|------:|
| Protein C deficiency | Automatic Integer Score          |  321 | 23520 |  6842 |   17 |         0.95  |         0.225 | 0.013 | 0.998 |
| Protein C deficiency | Association-Guided Integer Score |  307 | 27658 |  2704 |   31 |         0.908 |         0.089 | 0.011 | 0.989 |
| Protein S deficiency | Automatic Integer Score          |  670 | 21482 |  8488 |   60 |         0.918 |         0.283 | 0.03  | 0.993 |
| Protein S deficiency | Association-Guided Integer Score |  717 | 29280 |   690 |   13 |         0.982 |         0.023 | 0.024 | 0.982 |
| Factor V Leiden      | Automatic Integer Score          | 1865 | 17045 | 11675 |  115 |         0.942 |         0.407 | 0.099 | 0.99  |
| Factor V Leiden      | Association-Guided Integer Score | 1787 | 25487 |  3233 |  193 |         0.903 |         0.113 | 0.066 | 0.944 |
| Prothrombin G20210A  | Automatic Integer Score          | 1466 | 17746 | 11395 |   93 |         0.94  |         0.391 | 0.076 | 0.992 |
| Prothrombin G20210A  | Association-Guided Integer Score | 1527 | 28445 |   696 |   32 |         0.979 |         0.024 | 0.051 | 0.956 |

### Table D. Clinical utility at selected thresholds
| Outcome              | Model                            |   Sensitivity |   Specificity |   PPV |   NPV |   Tests avoided /1000 |   Missed true positives /1000 |
|:---------------------|:---------------------------------|--------------:|--------------:|------:|------:|----------------------:|------------------------------:|
| Protein C deficiency | Automatic Integer Score          |          0.95 |          0.23 |  0.01 |  1    |                223.42 |                          0.55 |
| Protein C deficiency | Association-Guided Integer Score |          0.91 |          0.09 |  0.01 |  0.99 |                 89.09 |                          1.01 |
| Protein S deficiency | Automatic Integer Score          |          0.92 |          0.28 |  0.03 |  0.99 |                278.44 |                          1.95 |
| Protein S deficiency | Association-Guided Integer Score |          0.98 |          0.02 |  0.02 |  0.98 |                 22.9  |                          0.42 |
| Factor V Leiden      | Automatic Integer Score          |          0.94 |          0.41 |  0.1  |  0.99 |                384.04 |                          3.75 |
| Factor V Leiden      | Association-Guided Integer Score |          0.9  |          0.11 |  0.07 |  0.94 |                111.6  |                          6.29 |
| Prothrombin G20210A  | Automatic Integer Score          |          0.94 |          0.39 |  0.08 |  0.99 |                374.2  |                          3.03 |
| Prothrombin G20210A  | Association-Guided Integer Score |          0.98 |          0.02 |  0.05 |  0.96 |                 23.71 |                          1.04 |

### Table E. Temporal validation summary
| Outcome                   |   Cutoff year |   Development n |   Validation n |   Sensitivity |   Specificity |   PPV |   NPV |
|:--------------------------|--------------:|----------------:|---------------:|--------------:|--------------:|------:|------:|
| Protein C deficiency      |          2021 |           30814 |            222 |         0.833 |         0.12  | 0.026 | 0.963 |
| Protein S deficiency      |          2021 |           30845 |            231 |         1     |         0.005 | 0.135 | 1     |
| Factor V Leiden           |          2021 |           31159 |            240 |         1     |         0.03  | 0.306 | 1     |
| Prothrombin G20210A       |          2021 |           30914 |            223 |         0.948 |         0.048 | 0.259 | 0.727 |
| Antiphospholipid syndrome |          2021 |           31202 |            269 |         0.984 |         0     | 0.453 | 0     |

### Table F. Calibration summary
| Outcome                   | Model                            |   Mean absolute calibration error |
|:--------------------------|:---------------------------------|----------------------------------:|
| Antiphospholipid syndrome | Automatic Integer Score          |                             0.093 |
| Factor V Leiden           | Association-Guided Integer Score |                             0.355 |
| Factor V Leiden           | Automatic Integer Score          |                             0.268 |
| Protein C deficiency      | Association-Guided Integer Score |                             0.439 |
| Protein C deficiency      | Automatic Integer Score          |                             0.317 |
| Protein S deficiency      | Association-Guided Integer Score |                             0.426 |
| Protein S deficiency      | Automatic Integer Score          |                             0.325 |
| Prothrombin G20210A       | Association-Guided Integer Score |                             0.376 |
| Prothrombin G20210A       | Automatic Integer Score          |                             0.288 |


## Draft Manuscript Text
The paragraphs below are written for direct insertion and editing in the manuscript.

### Methods Draft
We developed and evaluated prediction models only within the subgroup of patients who underwent thrombophilia testing in the RIETE-derived registry snapshot. Accordingly, the target estimand was the probability of a positive thrombophilia result among patients already selected for testing, rather than the prevalence of thrombophilia in the entire venous thromboembolism population. Baseline descriptive comparisons were therefore reframed as mutually exclusive tested versus not-tested cohorts, and standardized differences were prioritized over p values to characterize between-group imbalance.

Outcome definitions were based on registry-coded post-thrombosis thrombophilia variables. Because the available dataset did not contain treatment-at-testing timestamps, we could not determine whether heparin, vitamin K antagonists, or direct oral anticoagulants were being administered at the time of laboratory assessment. Likewise, the repository snapshot did not document confirmatory repeat antiphospholipid antibody testing, so antiphospholipid syndrome was analyzed as a registry-defined outcome rather than adjudicated persistent APS.

Model performance was summarized with explicit threshold-level confusion matrices, including true positives, false positives, true negatives, and false negatives. In addition to sensitivity, specificity, positive predictive value, and negative predictive value, we translated selected operating points into pragmatic screening terms: tests avoided per 1,000 tested patients and missed true-positive diagnoses per 1,000 tested patients. Calibration was assessed using binned observed-versus-predicted comparisons and summarized with mean absolute calibration error. Internal temporal validation was performed by developing the score on earlier diagnosis years and applying the fixed development threshold to later years.

### Results Draft
Among 119,449 registry rows, 22,874 patients were coded as having undergone thrombophilia testing, whereas 35,784 were explicitly coded as not tested. The tested subgroup was younger and had a lower burden of active cancer and immobilization than the not-tested subgroup, consistent with substantial clinical selection before laboratory work-up. Among tested patients with available binary post-thrombosis outcomes, positive results were observed in 3.46% for protein C deficiency, 7.34% for protein S deficiency, 19.25% for factor V Leiden, 15.44% for prothrombin G20210A, and 17.82% for antiphospholipid syndrome.

Threshold-level audit tables showed that the high negative predictive values were driven partly by low prevalence and partly by low specificity. For example, automatic-score rule-out thresholds would avoid approximately 223 tests per 1,000 tested patients for protein C deficiency, 278 per 1,000 for protein S deficiency, 384 per 1,000 for factor V Leiden, and 374 per 1,000 for prothrombin G20210A, while missing approximately 0.6, 2.0, 3.7, and 3.0 true-positive cases per 1,000 tested patients, respectively. Temporal validation using development years up to 2021 and later-year holdout data preserved high sensitivity but showed limited specificity across outcomes, supporting cautious use as a rule-out enrichment tool rather than as a definitive diagnostic classifier.

Calibration analyses showed heterogeneous agreement between predicted and observed risk across outcomes and score types. In the lightweight homogeneous summary generated here, antiphospholipid syndrome had the lowest mean absolute calibration error among the modeled outcomes, whereas several association-guided score variants showed poorer calibration. These findings support the need to report calibration explicitly rather than relying on discrimination or negative predictive value alone.

### Discussion Draft
These analyses materially refine the interpretation of the study. The models should not be described as estimating thrombophilia risk in the overall VTE population, because they were trained and evaluated only in patients already selected for testing. Instead, they should be presented as tools for prioritizing or ruling out thrombophilia testing within an already enriched clinical subgroup. This distinction is essential for avoiding spectrum-related overinterpretation.

The practical utility of the models lies less in their high negative predictive values per se than in the trade-off between tests avoided and true diagnoses missed. In low-prevalence settings, a high NPV can be achieved even with limited specificity; therefore, the clinical meaning becomes clearer when performance is translated into absolute counts per 1,000 tested patients. Our temporal validation also suggests that these scores may retain sensitivity across later calendar years but can lose specificity, which is relevant in a multicenter registry where testing practices and laboratory workflows likely evolve over time.

Finally, several limitations should remain explicit. The current repository snapshot does not allow adjustment for anticoagulant exposure at the time of thrombophilia testing, does not document confirmatory APS testing, and does not provide identifiable center or country fields for leave-center or leave-country internal-external validation. Thus, the present results are best interpreted as an internally audited, clinically oriented screening framework that still requires stronger external and laboratory-context validation before routine implementation.
