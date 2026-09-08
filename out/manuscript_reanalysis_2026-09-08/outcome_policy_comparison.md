# Effect of the investigator-confirmed outcome interpretation

The principal analysis uses the routine-panel policy confirmed on 8 September 2026. The 7 September explicit-results run remains an alternative analysis. Both runs use the same source registry and modelling settings. Composite and JAK2 aggregate model metrics were verified to be exactly unchanged across every analysis and validation.

For the six routine subtypes, missing outcomes become negative only among globally tested patients. This changes eligibility, class prevalence, complete-case populations and fitted models. Differences are descriptive and must not be presented as an isolated improvement in algorithm performance. Missing predictors retain their separate handling.

The total eligible positive count is unchanged for each routine subtype. The candidate availability rule is reapplied to the expanded development population and can retain a different candidate set. Complete-case membership can therefore change in both directions, and fewer positive cases may remain in the primary comparison despite the larger eligible population. This is documented in each run’s model_cohort_flow.csv and candidate_availability.csv.

The table shows primary complete-case XGBoost nested-validation results. The CSV gives all models and both nested and temporal validation; suffixes identify the outcome policy.

| label | n_explicit | n_routine | positive_n_explicit | positive_n_routine | auc_explicit | auc_routine |
| --- | --- | --- | --- | --- | --- | --- |
| Composite thrombophilia | 7209 | 7209 | 2801 | 2801 | 0.5913 | 0.5913 |
| Factor V Leiden | 5864 | 7209 | 1167 | 806 | 0.6234 | 0.6151 |
| Prothrombin G20210A | 5758 | 7209 | 850 | 592 | 0.5734 | 0.5583 |
| Registry-coded APS | 5866 | 7209 | 851 | 636 | 0.6017 | 0.6121 |
| Protein S deficiency | 5723 | 7209 | 384 | 261 | 0.5662 | 0.5575 |
| Protein C deficiency | 5711 | 7209 | 180 | 120 | 0.5864 | 0.5765 |
| Antithrombin deficiency | 5742 | 7209 | 127 | 92 | 0.6543 | 0.6186 |
| JAK2 mutation | 648 | 648 | 15 | 15 | 0.7002 | 0.7002 |

The associated provenance JSON records both run signatures and hashes of the aggregate source tables. No patient records are needed to reproduce this comparison.
