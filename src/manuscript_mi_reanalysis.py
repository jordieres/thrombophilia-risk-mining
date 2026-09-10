"""New continuous, multiple-imputation reanalysis; old result packages are preserved.

Shared predictor-only imputations across the seven routine outcomes reduce
computation without sharing outcome information. JAK2 has its own cohort.
Each imputation is repeated within every inner/outer training partition.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit, logit
from sklearn.metrics import roc_auc_score, log_loss
from joblib import Parallel, delayed
from threadpoolctl import threadpool_limits
from manuscript_cohort import OUTCOMES, NUMERIC, outcome_mask, outcome_labels, load_registry, prepare_features
from manuscript_models import LASSO_GRID, XGB_GRID, split_indices, select_threshold, metric_row, calibration_bins
from manuscript_reanalysis import write_json, hash_file, log, descriptive_exports, validate_predictions
from manuscript_artifacts import artifact_inventory
from manuscript_mi_models import MixedMICE, ContinuousDesign, continuous_features, fit_classifier, decision_curve

MODEL_NAMES = {'lasso': 'MI spline LASSO', 'xgb': 'MI continuous XGBoost'}


def chain_job(x, train, val, targets, grids, config, seed, cache, save_models):
    """Fit one chain and all requested classifiers; checkpoint only full success."""
    model_path = cache.with_name(cache.stem + '_model.joblib')
    if cache.exists() and (not save_models or model_path.exists()):
        return joblib.load(cache)
    with threadpool_limits(limits=1):
        imp = MixedMICE(seed=seed, iterations=config['iterations'], neighbors=config['neighbors'])
        a = imp.fit_transform(x.iloc[train]); b = imp.transform(x.iloc[val])
        result = {'probabilities': {}, 'diagnostics': imp.diagnostics_, 'selected': [], 'columns': imp.columns_}
        designs = {k: ContinuousDesign(splines=k == 'lasso').fit(a) for k in ['lasso', 'xgb']}
        matrices = {k: (d.transform(a), d.transform(b)) for k, d in designs.items()}
        models = {}
        for outcome, y in targets.items():
            if len(np.unique(y[train])) != 2:
                raise ValueError(f'{outcome}: training partition has only one outcome class')
            for kind in ['lasso', 'xgb']:
                values, fits = [], []
                for params in grids[outcome][kind]:
                    fit = fit_classifier(kind, params, matrices[kind][0], y[train], seed, threads=1)
                    values.append(fit.predict_proba(matrices[kind][1])[:, 1]); fits.append(fit)
                result['probabilities'][outcome, kind] = np.array(values)
                if save_models:
                    models[outcome, kind] = fits[0]
                    if kind == 'lasso':
                        for col in imp.columns_:
                            indices = np.array(designs[kind].sources_) == col
                            result['selected'].append(dict(outcome=outcome, variable=col,
                                selected=bool(np.any(np.abs(fits[0].coef_[0][indices]) > 1e-6))))
        if save_models:
            joblib.dump(dict(imputer=imp, designs=designs, models=models), model_path, compress=3)
        temporary = cache.with_suffix('.tmp.joblib')
        joblib.dump(result, temporary, compress=3); temporary.replace(cache)
        return result


def stage(x, train, val, targets, grids, config, directory, seed, save_models=False):
    directory.mkdir(parents=True, exist_ok=True)
    results = Parallel(n_jobs=config['workers'], backend='loky')(
        delayed(chain_job)(x, train, val, targets, grids, config, seed+1009*i,
                           directory/f'chain_{i+1:02}.joblib', save_models)
        for i in range(config['imputations']))
    probabilities = {key: np.stack([r['probabilities'][key] for r in results]) for key in results[0]['probabilities']}
    traces = pd.concat([pd.DataFrame(r['diagnostics']).assign(imputation=i+1) for i, r in enumerate(results)], ignore_index=True)
    traces.to_csv(directory/'imputation_trace.csv', index=False)
    write_json(directory/'partition_audit.json', dict(training_n=len(train), validation_n=len(val),
        disjoint=not bool(set(train) & set(val)), training_index_sha256=hashlib.sha256(np.asarray(train).tobytes()).hexdigest(),
        validation_index_sha256=hashlib.sha256(np.asarray(val).tobytes()).hexdigest(),
        retained_columns=results[0]['columns'], excluded_columns=[c for c in x if c not in results[0]['columns']],
        outcome_in_imputer=False))
    if save_models:
        pd.DataFrame([dict(r, imputation=i+1) for i, result in enumerate(results) for r in result['selected']]).to_csv(directory/'selection_by_imputation.csv', index=False)
    return probabilities


def tune(x, train, targets, stratify, config, directory, seed):
    grids = {o: {'lasso': LASSO_GRID[:2] if config['smoke'] else LASSO_GRID,
                  'xgb': XGB_GRID[:2] if config['smoke'] else XGB_GRID} for o in targets}
    pooled = {(o, k): np.zeros((len(g), len(train))) for o, kinds in grids.items() for k, g in kinds.items()}
    for fold, (t, v) in enumerate(split_indices(stratify[train], config['inner_splits'], seed), 1):
        log(f'{directory.name}: inner fold {fold}, n={len(t)} / {len(v)}')
        values = stage(x, train[t], train[v], targets, grids, config, directory/f'inner_{fold}', seed+fold*7919)
        for key, array in values.items():
            pooled[key][:, v] = array.mean(axis=0)
    chosen, thresholds, searches = {}, {}, []
    for o in targets:
        chosen[o], thresholds[o] = {}, {}
        for kind in ['lasso', 'xgb']:
            # Proper scoring rule encourages calibrated risks for decision curves.
            losses = [log_loss(targets[o][train], p, labels=[0, 1]) for p in pooled[o, kind]]
            best = int(np.argmin(losses)); chosen[o][kind] = [grids[o][kind][best]]
            thresholds[o][kind] = select_threshold(targets[o][train], pooled[o, kind][best], config['min_sensitivity'])
            for i, params in enumerate(grids[o][kind]):
                searches.append(dict(outcome=o, kind=kind, candidate=i, selected=i == best,
                    log_loss=losses[i], auc=roc_auc_score(targets[o][train], pooled[o, kind][i]), **params))
    pd.DataFrame(searches).to_csv(directory/'hyperparameter_search.csv', index=False)
    write_json(directory/'selected_models.json', dict(parameters=chosen, thresholds=thresholds))
    return chosen, thresholds


def prediction_rows(values, targets, ids, val, thresholds, validation, fold):
    rows = []
    for (o, kind), array in values.items():
        p = array[:, 0].mean(axis=0); threshold = thresholds[o][kind]
        # First-half vs full ensemble is a Monte Carlo stability diagnostic.
        half = array[:max(1, len(array)//2), 0].mean(axis=0)
        rows.append(pd.DataFrame(dict(id_pacie=ids[val], outcome=o, y_true=targets[o][val],
            model=MODEL_NAMES[kind], probability=p, imputation_sd=array[:, 0].std(axis=0, ddof=1),
            half_ensemble_probability=half, raw_score=p, threshold=threshold,
            predicted_positive=p >= threshold, integer_cutoff=np.nan, fold=fold,
            analysis='multiple_imputation_continuous', validation=validation)))
    return pd.concat(rows, ignore_index=True)


def run_population(raw, features, outcomes, config, output, name):
    mask = outcome_mask(raw, outcomes[0]); years = pd.to_datetime(raw.fecha_di, errors='coerce').dt.year
    for o in outcomes:
        if not outcome_mask(raw, o).equals(mask):
            raise ValueError('Shared imputation requires exactly identical eligible patients')
    if (mask & years.isna()).any():
        raise ValueError('Eligible patients have missing dates; resolve temporal policy explicitly')
    x = features.loc[mask].reset_index(drop=True); ids = raw.loc[mask, 'id_pacie'].to_numpy()
    yy = years.loc[mask].to_numpy()
    train = np.flatnonzero(yy <= config['cutoff_year']); val = np.flatnonzero(yy > config['cutoff_year'])
    targets = {o.column: outcome_labels(raw, o).loc[mask].eq(o.positive).to_numpy(dtype=int) for o in outcomes}
    stratify = targets[outcomes[0].column]
    directory = output/'partitions'/name; directory.mkdir(parents=True, exist_ok=True)
    frames = []
    for fold, (t, v) in enumerate(split_indices(stratify[train], config['outer_splits'], config['seed']), 1):
        log(f'{name}: outer fold {fold}/{config["outer_splits"]}')
        path = directory/f'outer_{fold}'
        chosen, thresholds = tune(x, train[t], targets, stratify, config, path, config['seed']+fold*100003)
        values = stage(x, train[t], train[v], targets, chosen, config, path/'outer_fit', config['seed']+fold*100019)
        frames.append(prediction_rows(values, targets, ids, train[v], thresholds, 'nested_cv', fold))
    log(f'{name}: locked development ensemble and temporal validation')
    chosen, thresholds = tune(x, train, targets, stratify, config, directory/'development', config['seed']+900001)
    values = stage(x, train, val, targets, chosen, config, directory/'development'/'final_fit', config['seed']+900019, save_models=True)
    frames.append(prediction_rows(values, targets, ids, val, thresholds, 'temporal_holdout', 0))
    predictions = pd.concat(frames, ignore_index=True)
    for o in outcomes:
        dest = output/o.column; dest.mkdir(exist_ok=True)
        predictions[predictions.outcome.eq(o.column)].to_parquet(dest/'predictions.parquet', index=False)
        write_json(dest/'cohort_flow.json', dict(outcome=o.column, label=o.label, eligible_n=int(mask.sum()),
            eligible_positive_n=int(targets[o.column].sum()), development_n=len(train), temporal_n=len(val),
            excluded_for_missing_predictors_n=0, outcome_policy='routine-panel', priority=o.priority))
    selection = pd.read_csv(directory/'development'/'final_fit'/'selection_by_imputation.csv')
    selection.groupby(['outcome', 'variable']).selected.agg(['mean', 'sum', 'count']).reset_index().rename(
        columns={'mean': 'selection_fraction', 'sum': 'selected_imputations', 'count': 'imputations'}).to_csv(directory/'selection_stability.csv', index=False)


def profile_exports(raw, output):
    """Observed profiles only; no mining, confidence, lift or rule-selection claim."""
    f, _ = prepare_features(raw); m = outcome_mask(raw, OUTCOMES[0]); f = f.loc[m]
    negative = raw.loc[m, 'ana_dura'].eq('Buscada negativo')
    profiles = [(['sexo', 'edad', 'fr_tvp_a'], ['Female', '<50', 'No'], 'Female, age <50, no prior VTE'),
        (['ana_hemo', 'ana_dime', 'fr_cance'], ['≥12', 'Negative', 'No'], 'Hemoglobin ≥12, negative D-dimer, no cancer'),
        (['sexo', 'edad', 'fr_estro'], ['Female', '50–69', 'No'], 'Female, age 50–69, no hormone exposure'),
        (['ana_plaq', 'fr_inmov', 'fr_tvp_a'], ['144–400', 'No', 'No'], 'Normal platelets, no immobilization, no prior VTE'),
        (['sexo', 'fr_tvp_a', 'ana_crea'], ['Female', 'No', 'Normal'], 'Female, no prior VTE, normal creatinine')]
    rows = []
    for cols, levels, label in profiles:
        if not set(cols).issubset(f):
            continue
        observed = f[cols].notna().all(axis=1)
        match = (f[cols].eq(levels).fillna(False)).all(axis=1)
        n = int(match.sum()); negatives = int((match & negative).sum())
        rows.append(dict(profile=label, eligible_n=len(f), profile_fields_observed_n=int(observed.sum()),
            profile_fields_missing_n=int((~observed).sum()), profile_n=n, negative_n=negatives,
            negative_fraction=negatives/n if n else np.nan))
    pd.DataFrame(rows).to_csv(output/'descriptive_negative_profiles.csv', index=False)


def summarize(output, outcomes, config):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    metrics, curves, calibrations, stability = [], [], [], []
    raw = load_registry(Path(config['data']))
    for o in outcomes:
        pred = pd.read_parquet(output/o.column/'predictions.parquet')
        expected = set(raw.loc[outcome_mask(raw, o), 'id_pacie'])
        om = []
        for (validation, model), frame in pred.groupby(['validation', 'model']):
            r = metric_row(frame, bootstrap=config['bootstrap'], seed=config['seed'])
            r.update(outcome=o.column, label=o.label, priority=o.priority, validation=validation, model=model)
            y = frame.y_true.to_numpy(); z = logit(np.clip(frame.probability.to_numpy(), 1e-8, 1-1e-8))
            fit = minimize(lambda b: np.mean(np.logaddexp(0, b[0]+b[1]*z)-y*(b[0]+b[1]*z)), [0., 1.], method='BFGS')
            r.update(calibration_intercept=float(fit.x[0]), calibration_slope=float(fit.x[1]),
                     calibration_fit_success=bool(fit.success))
            om.append(r)
            dc = decision_curve(y, frame.probability, np.arange(1, 51)/100)
            curves.append(dc.assign(outcome=o.column, validation=validation, model=model))
            calibrations.append(calibration_bins(frame).assign(outcome=o.column, validation=validation, model=model))
            delta = (frame.probability-frame.half_ensemble_probability).abs()
            stability.append(dict(outcome=o.column, validation=validation, model=model,
                mean_imputation_sd=frame.imputation_sd.mean(), half_full_mean_absolute_difference=delta.mean(),
                half_full_max_absolute_difference=delta.max()))
        for model, group in pred.groupby('model'):
            assert set(group.id_pacie) == expected and len(group) == len(expected), 'Not all eligible patients have one held-out prediction'
        checks = validate_predictions(pred, pd.DataFrame(om), raw, o, config['cutoff_year'])
        checks.update(all_eligible_patients_predicted=True, no_missing_predictor_patient_exclusion=True,
                      outcome_not_used_for_imputation=True, no_univariable_screening=True)
        write_json(output/o.column/'quality_checks.json', checks)
        pd.DataFrame(om).to_csv(output/o.column/'metrics.csv', index=False); metrics += om
    metrics = pd.DataFrame(metrics); curves = pd.concat(curves, ignore_index=True)
    metrics.to_csv(output/'all_model_metrics.csv', index=False)
    curves.to_csv(output/'decision_curves.csv', index=False)
    pd.concat(calibrations).to_csv(output/'calibration.csv', index=False)
    pd.DataFrame(stability).to_csv(output/'imputation_prediction_stability.csv', index=False)
    pd.DataFrame([json.loads((output/o.column/'cohort_flow.json').read_text()) for o in outcomes]).to_csv(output/'model_cohort_flow.csv', index=False)
    figures = output/'figures'; figures.mkdir(exist_ok=True)
    for (o, validation), d in curves.groupby(['outcome', 'validation']):
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for model, g in d.groupby('model'):
            ax.plot(g.threshold, g.net_benefit, label=model)
        g = next(iter(d.groupby('model')))[1]
        ax.plot(g.threshold, g.test_all_net_benefit, '--', label='Test all', color='gray')
        ax.axhline(0, color='black', linestyle=':', label='Test none')
        ax.set(xlabel='Risk threshold for testing', ylabel='Net benefit', title=f'{o}: {validation}', ylim=(-.05, max(.05, float(d.net_benefit.max())*1.1)))
        ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(figures/f'dca_{o}_{validation}.png', dpi=160); fig.savefig(figures/f'dca_{o}_{validation}.svg'); plt.close(fig)
    report(output, outcomes, config, metrics)


def report(output, outcomes, config, metrics):
    lines = ['# Multiple-imputation continuous-predictor reanalysis', '',
        '**Smoke test only; not publication evidence.**' if config['smoke'] else 'Numerical run completed; interpretation must follow the new validation results.', '',
        '## Methods', '',
        f'The original registry was analysed under the investigator-confirmed routine-panel outcome policy. Known carriers/known APS were excluded. Missing predictors did not exclude patients. JAK2 required an explicit result; its outcome was never imputed. The temporal cutoff remained {config["cutoff_year"]}.', '',
        f'{config["imputations"]} independent mixed-type chained imputations, each with {config["iterations"]} sweeps, were fitted afresh within each training partition. Continuous imputation used Bayesian ridge draws with five-donor predictive mean matching; categorical imputation used bootstrap ridge multinomial logistic models and probability draws. Conditional imputation models used up to {config["neighbors"]} training-selected predictor neighbours. No outcomes, identifiers, dates or follow-up fields entered imputation. This predictor-only strategy supports deployment with an unknown outcome, but differs from outcome-inclusive MI for coefficient inference. The missing-at-random assumption and conditional model adequacy cannot be established from these data.', '',
        'Continuous age, weight, systolic pressure, hemoglobin, platelets, leukocytes, neutrophils and CRP were retained within prespecified quality bounds. Logistic models used cubic B-splines with training-quantile knots (5th, 35th, 65th, 95th percentiles) and linear extrapolation, plus training-fitted dummy coding and standardization. Degenerate numeric variables fell back to linear terms. XGBoost received continuous values and dummy-coded categories. No univariable screening was performed. Constant/all-missing training predictors were documented and omitted, with no missingness-percentage ceiling.', '',
        f'Nested {config["outer_splits"]}-fold outer/{config["inner_splits"]}-fold inner validation selected penalties and tree parameters by log loss of probabilities averaged across imputations. Routine outcomes shared composite-stratified partitions and predictor-only imputations; JAK2 had separate stratification. The inner predictions selected a threshold targeting sensitivity ≥{config["min_sensitivity"]:.0%}. Locked development ensembles predicted the temporal holdout. Each patient has one held-out prediction per model (outer CV or temporal holdout), not an in-sample prediction from a model trained on all 22,847.', '',
        'Probabilities were averaged over the imputation-specific fitted models. LASSO variable-selection frequencies and half-versus-full-ensemble probability differences quantify stability. Selected penalized coefficients were not pooled with Rubin rules and no post-selection coefficient confidence intervals or integer point cards are claimed. AUC bootstrap intervals resample fixed held-out predictions; they do not include refitting uncertainty. Imputation traces require substantive review and are not proof of convergence.', '',
        'Decision curves compare model-guided testing, testing all and testing none at exploratory thresholds 1–50%. Net benefit = TP/N − FP/N × threshold/(1−threshold). This represents identifying a registered positive test, not demonstrated benefit of anticoagulation or improved patient outcomes. No threshold was selected from validation curves. The threshold range requires clinical justification before publication.', '',
        '## Held-out performance', '', '| Outcome | Validation | Model | N | AUC (95% conditional CI) | Brier | Sensitivity | Specificity |', '|---|---|---|---:|---|---:|---:|---:|']
    for r in metrics.itertuples():
        lines.append(f'| {r.label} | {r.validation} | {r.model} | {r.n} | {r.auc:.3f} ({r.auc_lower:.3f}–{r.auc_upper:.3f}) | {r.brier:.3f} | {r.sensitivity:.3f} | {r.specificity:.3f} |')
    lines += ['', '## Descriptive clinical profiles', '',
        'The five clinical profiles from the prior manuscript were retained solely as observed descriptive frequencies. No FP-Growth mining or association-rule thresholds are used in this analysis. Missing profile components are not imputed for these descriptions. These profiles were previously examined in this registry, so their frequencies are not independent validation.', '']
    for r in pd.read_csv(output/'descriptive_negative_profiles.csv').itertuples():
        lines.append(f'- {r.profile}: {r.negative_n}/{r.profile_n} negative ({r.negative_fraction:.1%}); {r.profile_fields_missing_n} eligible patients lack at least one profile component.')
    lines += ['', '## Interpretation and limitations', '',
        'The earlier conclusion of little predictive signal is not carried forward automatically. Compare discrimination, calibration and decision curves on the new paired populations. Comparisons with the prior complete-case results also change the population and cannot isolate the effect of continuous modeling alone. Extremely sparse predictors, structural missingness and the routine-panel outcome convention remain limitations; imputation cannot supply missing laboratory ground truth. JAK2 remains descriptive because events are scarce.', '',
        '## Sources', '',
        '- [Clinical prediction model development guide](https://www.bmj.com/content/386/bmj-2023-078276)',
        '- [MI and prediction under missing predictors](https://arxiv.org/abs/1810.05099)',
        '- [Decision-curve analysis](https://www.danieldsjoberg.com/dcurves/articles/dca.html)', '']
    (output/'replacement_manuscript_sections.md').write_text('\n'.join(lines))
    (output/'coauthor_responses.md').write_text('''# Responses to the new methodological review

1. **Missing predictors / all eligible patients.** The new models use multiple imputation within validation partitions; no eligible patient is excluded for missing predictors. The seven routine outcomes use the common eligible population; JAK2 still requires an observed result. Imputation-specific predictions are averaged; Rubin coefficient pooling is not claimed for selected LASSO models.
2. **Continuous information and screening.** Continuous values are retained, logistic models include splines, XGBoost uses continuous measurements, and univariable significance screening is removed. We do not assume that the old negative inference will survive this analysis.
3. **Decision curves.** Held-out net benefit is exported and plotted against testing all/none. The 1–50% range is exploratory pending clinical agreement; no universal journal requirement is asserted.
4. **FP-Growth discrepancy.** Association-rule mining is removed from the new manuscript package. Previously examined clinical profiles are reported only as observed negative-result frequencies, with explicit missing-component denominators. Confidence/lift thresholds and association-rule claims are absent.

See replacement_manuscript_sections.md and the aggregate CSVs for the executed settings, results and limitations. Previous result packages are retained separately.
''')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=Path('data/patD.parquet'))
    p.add_argument('--output-dir', type=Path, default=Path('out/manuscript_mi_2026-09-09'))
    p.add_argument('--imputations', type=int, default=20)
    p.add_argument('--iterations', type=int, default=5)
    p.add_argument('--neighbors', type=int, default=12)
    p.add_argument('--outer-splits', type=int, default=5)
    p.add_argument('--inner-splits', type=int, default=5)
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--bootstrap', type=int, default=500)
    p.add_argument('--cutoff-year', type=int, default=2021)
    p.add_argument('--min-sensitivity', type=float, default=.9)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--outcomes', nargs='+', choices=[o.column for o in OUTCOMES])
    p.add_argument('--smoke', action='store_true', help='Reduced search grid; explicitly nonpublication run')
    p.add_argument('--resume', action='store_true')
    args = p.parse_args(); config = vars(args).copy(); output = config.pop('output_dir'); resume = config.pop('resume')
    config['data'] = str(args.data.resolve())
    if args.imputations < 2 or args.iterations < 1 or min(args.outer_splits, args.inner_splits) < 2 or args.workers < 1 or args.neighbors < 1 or args.bootstrap < 0 or not 0 < args.min_sensitivity <= 1:
        raise ValueError('Invalid run settings')
    selected = [o for o in OUTCOMES if args.outcomes is None or o.column in args.outcomes]
    # Include composite for common stratification whenever a routine endpoint is requested.
    if any(o.column != 'andujak2' for o in selected) and OUTCOMES[0] not in selected:
        raise ValueError('Include ana_dura when requesting routine outcomes (shared stratification)')
    code = {name: hash_file(Path(__file__).with_name(name)) for name in ['manuscript_mi_models.py',
        'manuscript_mi_reanalysis.py', 'manuscript_cohort.py', 'manuscript_models.py', 'manuscript_reanalysis.py', 'manuscript_artifacts.py']}
    versions = {p: importlib.metadata.version(p) for p in ['numpy', 'pandas', 'scipy', 'scikit-learn', 'xgboost', 'joblib', 'pyarrow', 'matplotlib']}
    signature_data = dict(config=config, code=code, data=hash_file(args.data), versions=versions)
    signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
    output.mkdir(parents=True, exist_ok=True); manifest_path = output/'run_manifest.json'
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text())
        if not resume or old['signature'] != signature:
            raise ValueError('Existing run differs or --resume missing; use a new directory')
    manifest = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(), signature=signature, **signature_data)
    write_json(manifest_path, manifest)
    (output/'README.md').write_text('# Continuous multiple-imputation reanalysis\n\nConsult run_manifest.json: only status complete is a finished run.\n\nPatient predictions, imputation caches and fitted ensembles are local-only joblib/parquet files. Aggregate tables, diagnostics, figures and English manuscript text are shareable. Earlier analyses are preserved.\n')
    try:
        raw = load_registry(args.data); x, quality = continuous_features(raw)
        quality.to_csv(output/'numeric_and_category_quality.csv', index=False)
        descriptive_exports(raw, prepare_features(raw)[0], output)
        profile_exports(raw, output)
        routine = [o for o in selected if o.column != 'andujak2']
        if routine:
            run_population(raw, x, routine, config, output, 'routine')
        if OUTCOMES[-1] in selected:
            run_population(raw, x, [OUTCOMES[-1]], config, output, 'jak2')
        summarize(output, selected, config)
        manifest.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(), **artifact_inventory(output))
        write_json(manifest_path, manifest); log(f'Completed: {output}')
    except Exception as exc:
        manifest.update(status='failed', error=f'{type(exc).__name__}: {exc}')
        write_json(manifest_path, manifest)
        raise


if __name__ == '__main__':
    main()
