# Multiple-imputation continuous-predictor reanalysis

Numerical run completed; interpretation must follow the new validation results.

## Methods

The original registry was analysed under the investigator-confirmed routine-panel outcome policy. Known carriers/known APS were excluded. Missing predictors did not exclude patients. JAK2 required an explicit result; its outcome was never imputed. The temporal cutoff remained 2021.

20 independent mixed-type chained imputations, each with 5 sweeps, were fitted afresh within each training partition. Continuous imputation used Bayesian ridge draws with five-donor predictive mean matching; categorical imputation used bootstrap ridge multinomial logistic models and probability draws. Conditional imputation models used up to 12 training-selected predictor neighbours. No outcomes, identifiers, dates or follow-up fields entered imputation. This predictor-only strategy supports deployment with an unknown outcome, but differs from outcome-inclusive MI for coefficient inference. The missing-at-random assumption and conditional model adequacy cannot be established from these data.

Continuous age, weight, systolic pressure, hemoglobin, platelets, leukocytes, neutrophils and CRP were retained within prespecified quality bounds. Logistic models used cubic B-splines with training-quantile knots (5th, 35th, 65th, 95th percentiles) and linear extrapolation, plus training-fitted dummy coding and standardization. Degenerate numeric variables fell back to linear terms. XGBoost received continuous values and dummy-coded categories. No univariable screening was performed. Constant/all-missing training predictors were documented and omitted, with no missingness-percentage ceiling.

Nested 5-fold outer/5-fold inner validation selected penalties and tree parameters by log loss of probabilities averaged across imputations. Routine outcomes shared composite-stratified partitions and predictor-only imputations; JAK2 had separate stratification. The inner predictions selected a threshold targeting sensitivity ≥90%. Locked development ensembles predicted the temporal holdout. Each patient has one held-out prediction per model (outer CV or temporal holdout), not an in-sample prediction from a model trained on all 22,847.

Probabilities were averaged over the imputation-specific fitted models. LASSO variable-selection frequencies and half-versus-full-ensemble probability differences quantify stability. Selected penalized coefficients were not pooled with Rubin rules and no post-selection coefficient confidence intervals or integer point cards are claimed. AUC bootstrap intervals resample fixed held-out predictions; they do not include refitting uncertainty. Imputation traces require substantive review and are not proof of convergence.

Decision curves compare model-guided testing, testing all and testing none at exploratory thresholds 1–50%. Net benefit = TP/N − FP/N × threshold/(1−threshold). This represents identifying a registered positive test, not demonstrated benefit of anticoagulation or improved patient outcomes. No threshold was selected from validation curves. The threshold range requires clinical justification before publication.

## Held-out performance

| Outcome | Validation | Model | N | AUC (95% conditional CI) | Brier | Sensitivity | Specificity |
|---|---|---|---:|---|---:|---:|---:|
| Composite thrombophilia | nested_cv | MI continuous XGBoost | 21762 | 0.582 (0.573–0.589) | 0.230 | 0.902 | 0.158 |
| Composite thrombophilia | nested_cv | MI spline LASSO | 21762 | 0.581 (0.574–0.589) | 0.230 | 0.902 | 0.166 |
| Composite thrombophilia | temporal_holdout | MI continuous XGBoost | 1085 | 0.584 (0.551–0.622) | 0.215 | 0.907 | 0.154 |
| Composite thrombophilia | temporal_holdout | MI spline LASSO | 1085 | 0.596 (0.562–0.632) | 0.215 | 0.901 | 0.164 |
| Factor V Leiden | nested_cv | MI continuous XGBoost | 21762 | 0.654 (0.642–0.665) | 0.080 | 0.903 | 0.245 |
| Factor V Leiden | nested_cv | MI spline LASSO | 21762 | 0.660 (0.649–0.672) | 0.080 | 0.902 | 0.261 |
| Factor V Leiden | temporal_holdout | MI continuous XGBoost | 1085 | 0.650 (0.590–0.709) | 0.062 | 0.931 | 0.234 |
| Factor V Leiden | temporal_holdout | MI spline LASSO | 1085 | 0.653 (0.587–0.712) | 0.062 | 0.903 | 0.264 |
| Prothrombin G20210A | nested_cv | MI continuous XGBoost | 21762 | 0.596 (0.582–0.611) | 0.065 | 0.903 | 0.186 |
| Prothrombin G20210A | nested_cv | MI spline LASSO | 21762 | 0.602 (0.588–0.618) | 0.065 | 0.900 | 0.202 |
| Prothrombin G20210A | temporal_holdout | MI continuous XGBoost | 1085 | 0.622 (0.556–0.687) | 0.050 | 0.966 | 0.167 |
| Prothrombin G20210A | temporal_holdout | MI spline LASSO | 1085 | 0.628 (0.556–0.698) | 0.051 | 0.948 | 0.165 |
| Registry-coded APS | nested_cv | MI continuous XGBoost | 21762 | 0.611 (0.599–0.624) | 0.073 | 0.904 | 0.207 |
| Registry-coded APS | nested_cv | MI spline LASSO | 21762 | 0.609 (0.597–0.621) | 0.073 | 0.898 | 0.195 |
| Registry-coded APS | temporal_holdout | MI continuous XGBoost | 1085 | 0.656 (0.607–0.707) | 0.098 | 0.910 | 0.180 |
| Registry-coded APS | temporal_holdout | MI spline LASSO | 1085 | 0.606 (0.556–0.661) | 0.098 | 0.902 | 0.174 |
| Protein S deficiency | nested_cv | MI continuous XGBoost | 21762 | 0.587 (0.567–0.608) | 0.032 | 0.901 | 0.167 |
| Protein S deficiency | nested_cv | MI spline LASSO | 21762 | 0.591 (0.570–0.611) | 0.032 | 0.897 | 0.179 |
| Protein S deficiency | temporal_holdout | MI continuous XGBoost | 1085 | 0.537 (0.451–0.630) | 0.028 | 0.871 | 0.212 |
| Protein S deficiency | temporal_holdout | MI spline LASSO | 1085 | 0.556 (0.466–0.652) | 0.028 | 0.871 | 0.198 |
| Protein C deficiency | nested_cv | MI continuous XGBoost | 21762 | 0.569 (0.537–0.599) | 0.016 | 0.914 | 0.127 |
| Protein C deficiency | nested_cv | MI spline LASSO | 21762 | 0.548 (0.514–0.581) | 0.016 | 0.900 | 0.151 |
| Protein C deficiency | temporal_holdout | MI continuous XGBoost | 1085 | 0.597 (0.419–0.761) | 0.006 | 1.000 | 0.092 |
| Protein C deficiency | temporal_holdout | MI spline LASSO | 1085 | 0.450 (0.225–0.631) | 0.006 | 0.833 | 0.138 |
| Antithrombin deficiency | nested_cv | MI continuous XGBoost | 21762 | 0.570 (0.536–0.605) | 0.011 | 0.885 | 0.179 |
| Antithrombin deficiency | nested_cv | MI spline LASSO | 21762 | 0.553 (0.518–0.590) | 0.011 | 0.902 | 0.151 |
| Antithrombin deficiency | temporal_holdout | MI continuous XGBoost | 1085 | 0.617 (0.484–0.748) | 0.014 | 0.867 | 0.192 |
| Antithrombin deficiency | temporal_holdout | MI spline LASSO | 1085 | 0.620 (0.469–0.751) | 0.014 | 0.867 | 0.208 |
| JAK2 mutation | nested_cv | MI continuous XGBoost | 2098 | 0.792 (0.705–0.875) | 0.019 | 0.863 | 0.379 |
| JAK2 mutation | nested_cv | MI spline LASSO | 2098 | 0.828 (0.755–0.894) | 0.019 | 0.863 | 0.520 |
| JAK2 mutation | temporal_holdout | MI continuous XGBoost | 141 | 0.940 (0.840–0.994) | 0.043 | 1.000 | 0.443 |
| JAK2 mutation | temporal_holdout | MI spline LASSO | 141 | 0.901 (0.754–0.985) | 0.046 | 0.900 | 0.496 |

## Descriptive clinical profiles

The five clinical profiles from the prior manuscript were retained solely as observed descriptive frequencies. No FP-Growth mining or association-rule thresholds are used in this analysis. Missing profile components are not imputed for these descriptions. These profiles were previously examined in this registry, so their frequencies are not independent validation.

- Female, age <50, no prior VTE: 2684/4326 negative (62.0%); 0 eligible patients lack at least one profile component.
- Hemoglobin ≥12, negative D-dimer, no cancer: 365/565 negative (64.6%); 1622 eligible patients lack at least one profile component.
- Female, age 50–69, no hormone exposure: 1795/2710 negative (66.2%); 283 eligible patients lack at least one profile component.
- Normal platelets, no immobilization, no prior VTE: 8303/13448 negative (61.7%); 40 eligible patients lack at least one profile component.
- Female, no prior VTE, normal creatinine: 5428/8375 negative (64.8%); 751 eligible patients lack at least one profile component.

## Interpretation and limitations

The earlier conclusion of little predictive signal is not carried forward automatically. Compare discrimination, calibration and decision curves on the new paired populations. Comparisons with the prior complete-case results also change the population and cannot isolate the effect of continuous modeling alone. Extremely sparse predictors, structural missingness and the routine-panel outcome convention remain limitations; imputation cannot supply missing laboratory ground truth. JAK2 remains descriptive because events are scarce.

## Sources

- [Clinical prediction model development guide](https://www.bmj.com/content/386/bmj-2023-078276)
- [MI and prediction under missing predictors](https://arxiv.org/abs/1810.05099)
- [Decision-curve analysis](https://www.danieldsjoberg.com/dcurves/articles/dca.html)
