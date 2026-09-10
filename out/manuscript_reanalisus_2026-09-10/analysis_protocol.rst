Continuous multiple-imputation reanalysis
=========================================

This is a separate response to the additional methodological review. It does
not overwrite the September 7 or September 8 analyses. A run is finished only
when its ``run_manifest.json`` says ``complete``; ``smoke: true`` always means
nonpublication test evidence, even if that test completes.

Scientific contract
-------------------

* Use the original ``data/patD.parquet`` and the existing pretest allowlist.
  Retain continuous numeric measurements within the documented quality bounds.
* The composite and six routine subtypes share 22,847 eligible patients under
  the investigator-confirmed routine-panel outcome convention. This is separate
  from predictor imputation. JAK2 requires an explicit outcome (2,239 eligible).
* Retain patients with missing predictors. Preserve observed values. Exclude
  only unavailable/constant training predictors, without significance screening
  or a predictor missingness-percentage ceiling. Highly incomplete predictors
  and structural missingness remain scientific limitations.
* Mixed-type fully conditional specification uses Bayesian ridge parameter
  draws with five-donor predictive mean matching for continuous variables,
  and bootstrap ridge multinomial logistic fits with probability draws for
  categorical variables. Initialization samples observed training values.
  Up to 12 conditional predictors are selected using absolute correlations
  of initial training encodings; categorical regressors then enter as dummies.
  This is an approximate, regularized mixed-type MICE implementation, not a
  call to the R ``mice`` package or Gaussian imputation of category codes.
* Outcome labels never enter imputation. This deployment-compatible prediction
  strategy differs from outcome-inclusive MI used for parameter inference.
  MAR and model adequacy are assumptions, not verified properties.
* All imputation, dummy coding, scaling and spline knots are fitted inside the
  relevant inner or outer training split. Fitted conditional models impute
  validation predictors without refitting or using validation labels.
* Logistic models use L1 penalization and cubic B-splines with training-quantile
  knots and linear extrapolation. XGBoost receives continuous measurements.
  Neither model performs univariable significance screening.
* Hyperparameters minimize inner-CV log loss of averaged probabilities. Final
  prediction is the average over imputation-specific fitted models. Export
  LASSO selection frequencies, not Rubin confidence intervals for selected
  penalized coefficients or a new integer point card.
* Five outer and five inner folds are the production defaults. Routine outcomes
  share composite-stratified folds and predictor-only imputations. JAK2 uses its
  own stratification. The temporal cutoff stays 2021. No temporal records enter
  development fitting. Every eligible patient has one held-out prediction for
  each model, either outer CV (development) or temporal validation.
* AUC intervals use 500 stratified bootstraps of fixed predictions, not model
  refitting. Report calibration and decision curves separately by validation.
* Decision curves evaluate testing, not treatment, over an exploratory 1–50%
  risk-threshold grid. Clinical justification of the range is still needed.
  Net benefit is TP/N - FP/N * pt/(1-pt). Test-all/test-none are comparators.
* No FP-Growth is performed. Five previously examined clinical profiles are
  reported as observed negative fractions with missing-component denominators.
  Do not describe them as discovered/validated association rules.

Execution
---------

The scientific dependencies are the same as the earlier pipeline. Exact
installed versions and all numerical source/data hashes enter the manifest
signature, preventing reuse across incompatible environments or changes.

.. code-block:: bash

   OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     python src/manuscript_mi_reanalysis.py \
       --output-dir out/manuscript_mi_2026-09-09

The defaults use 20 imputations, five chain sweeps, five-by-five nested folds,
500 AUC bootstraps and four local worker processes. This is a substantial run.
Workers parallelize imputation/model computation; they are not coding agents.
No patients are subsampled. Trace stability should guide a follow-up run with
more sweeps/imputations if needed; five sweeps are not a convergence guarantee.

Resume with the identical command plus ``--resume``. Completed chain jobs are
reused only under a matching run signature. Partitions and chain seeds are
recorded. Do not edit a running analysis's numerical source files.

For a real-data integration test (not publication results):

.. code-block:: bash

   OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
     python src/manuscript_mi_reanalysis.py --outcomes andujak2 --smoke \
       --imputations 2 --iterations 2 --outer-splits 2 --inner-splits 2 \
       --bootstrap 0 --workers 2 --output-dir /tmp/thrombophilia_mi_smoke

Artifacts
---------

* ``replacement_manuscript_sections.md`` and ``coauthor_responses.md``: new
  English methods, numerical results, profile description and review responses.
* ``model_cohort_flow.csv``: explicit eligible/development/temporal counts.
* ``all_model_metrics.csv``, ``calibration.csv``, ``decision_curves.csv`` and
  ``figures/``: held-out performance and decision curves.
* ``descriptive_negative_profiles.csv``: observed profile frequencies.
* ``imputation_prediction_stability.csv``: per-patient between-imputation SD
  aggregated across patients, and half/full ensemble differences.
* ``partitions/``: training/validation audits, imputation traces, searches and
  development LASSO selection stability. Categorical trace means refer to
  category codes, not clinically meaningful continuous measurements.
* ``*/predictions.parquet``: local-only held-out patient predictions.
* ``partitions/*/development/final_fit/*_model.joblib``: local-only imputers,
  encoders and classifiers. Other joblib files are resumable chain caches.
* ``*/quality_checks.json``: cohort, dates, counts and full coverage checks.

No manuscript inference of little predictive signal is carried forward without
examining the new estimates. Earlier complete-case and new MI populations differ;
a difference between their metrics cannot be attributed solely to modeling.

References
----------

* `Clinical prediction model development guide <https://www.bmj.com/content/386/bmj-2023-078276>`_
* `MI and prediction under missing predictors <https://arxiv.org/abs/1810.05099>`_
* `Decision curve analysis <https://www.danieldsjoberg.com/dcurves/articles/dca.html>`_
