# Response to Methodological Comments

## 1. Target population and scope
The repository data confirm that the predictive models operate within the subgroup that underwent thrombophilia testing, not the full VTE registry.

- Full registry rows: **119,449**.
- Patients with mutually exclusive `tested` status (`Buscada positivo` or `Buscada negativo`): **22,874**.
- Patients classified as `No buscada` after preprocessing normalization of missing study labels: **96,575**.
- Consequently, all reported discrimination, calibration, and threshold metrics should be framed as the probability of a positive thrombophilia result among already selected patients, rather than the prevalence of thrombophilia among all VTE patients.

### Tested vs not tested baseline comparison
| Variable              | Tested             | Not_Tested         | Standardized_Difference   |
|:----------------------|:-------------------|:-------------------|:--------------------------|
| N                     | 22874              | 96575              |                           |
| Age, mean (SD)        | 55.2 (18.1)        | 67.7 (16.1)        | -0.734                    |
| Female sex            | 10781 (47.1%)      | 48943 (50.7%)      | -0.071                    |
| Active cancer         | 2671 (11.7%)       | 26850 (27.8%)      | -0.414                    |
| Immobilization        | 4361 (19.1%)       | 22903 (23.7%)      | -0.114                    |
| Prior VTE             | 3062 (13.4%)       | 12896 (13.4%)      | 0.001                     |
| Known lupus           | 69 (0.3%)          | 146 (0.2%)         | 0.032                     |
| Known APS             | 27 (0.1%)          | 36 (0.0%)          | 0.029                     |
| Hemoglobin, mean (SD) | 13.46 (2.43)       | 12.83 (2.43)       | 0.261                     |
| Leukocytes, mean (SD) | 210.62 (30241.75)  | 11.83 (203.37)     | 0.009                     |
| D-dimer, mean (SD)    | 1360.25 (66333.76) | 1013.08 (76199.68) | 0.005                     |

### Outcome prevalence among tested patients
| Outcome                   | Column   |   Tested_N |   Positive_N |   Positive_% |
|:--------------------------|:---------|-----------:|-------------:|-------------:|
| Antiphospholipid syndrome | var161   |      10710 |         1908 |        17.82 |
| Factor V Leiden           | var156   |      10638 |         2048 |        19.25 |
| Protein C deficiency      | var154   |      10275 |          356 |         3.46 |
| Protein S deficiency      | var155   |      10315 |          757 |         7.34 |
| Prothrombin G20210A       | var157   |      10376 |         1602 |        15.44 |

## 2. Outcome-definition caveats
- The preprocessing pipeline normalizes missing `ana_dura` values to `No buscada`, so the not-tested cohort combines explicitly unrequested and previously unlabeled thrombophilia-study rows. The repository still does not expose treatment-at-testing timestamps for heparin, VKAs, or DOACs.
- The available dataset also does not document confirmatory repeat testing for antiphospholipid antibodies, so APS classification should be described as registry-defined rather than laboratory-adjudicated persistent APS.

## 3. Confusion-matrix audit, calibration, and clinical utility
### Protein C deficiency (`var154`)
Tested binary cohort size: **31,036**.

Selected-threshold confusion matrices from the cross-validated score audit:
| Model                            |   Threshold | Decision_Rule      | Selected_Threshold   |   TP |    FP |    TN |   FN |   Sensitivity |   Specificity |   PPV |   NPV |   Predicted_Positive_Count |   Predicted_Negative_Count |
|:---------------------------------|------------:|:-------------------|:---------------------|-----:|------:|------:|-----:|--------------:|--------------:|------:|------:|---------------------------:|---------------------------:|
| Automatic Integer Score          |           5 | score >= threshold | True                 |  347 |  8914 | 21766 |    9 |         0.975 |         0.709 | 0.037 | 1     |                       9261 |                      21775 |
| Association-Guided Integer Score |           5 | score <= threshold | True                 |  328 | 27631 |  3049 |   28 |         0.921 |         0.099 | 0.012 | 0.991 |                      27959 |                       3077 |

### Protein S deficiency (`var155`)
Tested binary cohort size: **31,076**.

Selected-threshold confusion matrices from the cross-validated score audit:
| Model                            |   Threshold | Decision_Rule      | Selected_Threshold   |   TP |    FP |    TN |   FN |   Sensitivity |   Specificity |   PPV | NPV   |   Predicted_Positive_Count |   Predicted_Negative_Count |
|:---------------------------------|------------:|:-------------------|:---------------------|-----:|------:|------:|-----:|--------------:|--------------:|------:|:------|---------------------------:|---------------------------:|
| Automatic Integer Score          |           8 | score >= threshold | True                 |  729 |  6229 | 24090 |   28 |         0.963 |         0.795 | 0.105 | 0.999 |                       6958 |                      24118 |
| Association-Guided Integer Score |           7 | score <= threshold | True                 |  757 | 30319 |     0 |    0 |         1     |         0     | 0.024 |       |                      31076 |                          0 |

### Factor V Leiden (`var156`)
Tested binary cohort size: **31,399**.

Selected-threshold confusion matrices from the cross-validated score audit:
| Model                            |   Threshold | Decision_Rule      | Selected_Threshold   |   TP |    FP |    TN |   FN |   Sensitivity |   Specificity |   PPV |   NPV |   Predicted_Positive_Count |   Predicted_Negative_Count |
|:---------------------------------|------------:|:-------------------|:---------------------|-----:|------:|------:|-----:|--------------:|--------------:|------:|------:|---------------------------:|---------------------------:|
| Automatic Integer Score          |          10 | score >= threshold | True                 | 1943 |  4791 | 24560 |  105 |         0.949 |         0.837 | 0.289 | 0.996 |                       6734 |                      24665 |
| Association-Guided Integer Score |           3 | score <= threshold | True                 | 1856 | 26376 |  2975 |  192 |         0.906 |         0.101 | 0.066 | 0.939 |                      28232 |                       3167 |

### Prothrombin G20210A (`var157`)
Tested binary cohort size: **31,137**.

Selected-threshold confusion matrices from the cross-validated score audit:
| Model                   |   Threshold | Decision_Rule      | Selected_Threshold   |   TP |   FP |    TN |   FN |   Sensitivity |   Specificity |   PPV |   NPV |   Predicted_Positive_Count |   Predicted_Negative_Count |
|:------------------------|------------:|:-------------------|:---------------------|-----:|-----:|------:|-----:|--------------:|--------------:|------:|------:|---------------------------:|---------------------------:|
| Automatic Integer Score |          11 | score >= threshold | True                 | 1523 | 5058 | 24477 |   79 |         0.951 |         0.829 | 0.231 | 0.997 |                       6581 |                      24556 |

### Antiphospholipid syndrome (`var161`)
Tested binary cohort size: **31,471**.

Selected-threshold confusion matrices from the cross-validated score audit:
| Model                            |   Threshold | Decision_Rule      | Selected_Threshold   |   TP |    FP |    TN |   FN |   Sensitivity |   Specificity |   PPV | NPV   |   Predicted_Positive_Count |   Predicted_Negative_Count |
|:---------------------------------|------------:|:-------------------|:---------------------|-----:|------:|------:|-----:|--------------:|--------------:|------:|:------|---------------------------:|---------------------------:|
| Automatic Integer Score          |          11 | score >= threshold | True                 | 1839 |  5642 | 23921 |   69 |         0.964 |         0.809 | 0.246 | 0.997 |                       7481 |                      23990 |
| Association-Guided Integer Score |           1 | score <= threshold | True                 | 1908 | 29563 |     0 |    0 |         1     |         0     | 0.061 |       |                      31471 |                          0 |

### Threshold-derived clinical utility
The table below translates high NPV operating points into more interpretable resource terms: how many tests might be avoided per 1,000 tested patients, and how many true positives would be missed.

| Outcome                   | Model                            |   Selected_Threshold |   Sensitivity |   Specificity |   PPV | NPV   |   Tests_Avoided_per_1000 |   Missed_True_Positives_per_1000 |
|:--------------------------|:---------------------------------|---------------------:|--------------:|--------------:|------:|:------|-------------------------:|---------------------------------:|
| Protein C deficiency      | Automatic Integer Score          |                    5 |          0.97 |          0.71 |  0.04 | 1.00  |                   701.6  |                             0.29 |
| Protein C deficiency      | Association-Guided Integer Score |                    5 |          0.92 |          0.1  |  0.01 | 0.99  |                    99.14 |                             0.9  |
| Protein S deficiency      | Automatic Integer Score          |                    8 |          0.96 |          0.79 |  0.1  | 1.00  |                   776.1  |                             0.9  |
| Protein S deficiency      | Association-Guided Integer Score |                    7 |          1    |          0    |  0.02 |       |                     0    |                             0    |
| Factor V Leiden           | Automatic Integer Score          |                   10 |          0.95 |          0.84 |  0.29 | 1.00  |                   785.53 |                             3.34 |
| Factor V Leiden           | Association-Guided Integer Score |                    3 |          0.91 |          0.1  |  0.07 | 0.94  |                   100.86 |                             6.11 |
| Prothrombin G20210A       | Automatic Integer Score          |                   11 |          0.95 |          0.83 |  0.23 | 1.00  |                   788.64 |                             2.54 |
| Antiphospholipid syndrome | Automatic Integer Score          |                   11 |          0.96 |          0.81 |  0.25 | 1.00  |                   762.29 |                             2.19 |
| Antiphospholipid syndrome | Association-Guided Integer Score |                    1 |          1    |          0    |  0.06 |       |                     0    |                             0    |

## 4. Temporal validation
A temporal split was feasible because diagnosis dates are present in the repository (`fecha_di`, years 2001-2024). The holdout threshold was fixed from the development era and then applied unchanged to later years.

| strategy_name           |   cutoff_year |   development_n |   validation_n |   auc |   brier_score |   selected_threshold |   sensitivity |   specificity |   ppv |   npv |   tp |   fp |   tn |   fn |
|:------------------------|--------------:|----------------:|---------------:|------:|--------------:|---------------------:|--------------:|--------------:|------:|------:|-----:|-----:|-----:|-----:|
| Automatic Integer Score |          2021 |           30814 |            222 | 0.418 |         0.415 |                    8 |         0.833 |         0.12  | 0.026 | 0.963 |    5 |  190 |   26 |    1 |
| Automatic Integer Score |          2021 |           30845 |            231 | 0.495 |         0.37  |                    9 |         1     |         0.005 | 0.135 | 1     |   31 |  199 |    1 |    0 |
| Automatic Integer Score |          2021 |           31159 |            240 | 0.613 |         0.126 |                   10 |         1     |         0.03  | 0.306 | 1     |   72 |  163 |    5 |    0 |
| Automatic Integer Score |          2021 |           30914 |            223 | 0.74  |         0.208 |                   11 |         0.948 |         0.048 | 0.259 | 0.727 |   55 |  157 |    8 |    3 |
| Automatic Integer Score |          2021 |           31202 |            269 | 0.382 |         0.295 |                   14 |         0.984 |         0     | 0.453 | 0     |  121 |  146 |    0 |    2 |

No country or center variable was available in the local parquet inspected here, so leave-country or leave-center internal-external validation could not be reproduced from the current repository snapshot.

## 5. Calibration
The current repository already mentioned calibration and Brier-style performance in Methods, but these results were not surfaced clearly. The generated calibration tables and plot now make that gap explicit.

| Outcome                   | Model                            |   Mean_Absolute_Calibration_Error |
|:--------------------------|:---------------------------------|----------------------------------:|
| Antiphospholipid syndrome | Association-Guided Integer Score |                             0.386 |
| Antiphospholipid syndrome | Automatic Integer Score          |                             0.091 |
| Antiphospholipid syndrome | Logistic Probability Benchmark   |                             0.091 |
| Factor V Leiden           | Association-Guided Integer Score |                             0.35  |
| Factor V Leiden           | Automatic Integer Score          |                             0.062 |
| Factor V Leiden           | Logistic Probability Benchmark   |                             0.062 |
| Protein C deficiency      | Association-Guided Integer Score |                             0.434 |
| Protein C deficiency      | Automatic Integer Score          |                             0.092 |
| Protein C deficiency      | Logistic Probability Benchmark   |                             0.092 |
| Protein S deficiency      | Association-Guided Integer Score |                             0.424 |
| Protein S deficiency      | Automatic Integer Score          |                             0.094 |
| Protein S deficiency      | Logistic Probability Benchmark   |                             0.094 |
| Prothrombin G20210A       | Automatic Integer Score          |                             0.072 |
| Prothrombin G20210A       | Logistic Probability Benchmark   |                             0.072 |

Interactive calibration plot: `calibration_overview.html`.

## 6. Interpretation of simplified score cut-points
- The present automatic score still derives several intervals from data-driven quantile binning. That makes narrow leukocyte, hemoglobin, D-dimer, or age bands possible even when their clinical meaning is weak.
- For manuscript reporting, those cut-points should therefore be described as sample-derived screening heuristics requiring external validation, not as stable biological thresholds.

## 7. Recommended wording changes for the manuscript
1. Replace any wording that implies prediction in the whole VTE cohort with wording restricted to patients already selected for thrombophilia work-up.
2. Define each outcome as a registry-coded post-thrombosis thrombophilia result and state explicitly which laboratory adjudications were unavailable.
3. Prefer mutually exclusive baseline groups (`tested` vs `not tested`) and emphasize standardized differences instead of p-values.
4. Report TP/FP/TN/FN, calibration, and the practical yield per 1,000 tested patients alongside NPV.