"""Reproducible manuscript reanalysis command, exports, and numerical quality gates.

Run ``python src/manuscript_reanalysis.py --help`` for the supported interface.
Results live in a dedicated run directory; historical exploratory outputs are
never consumed as model evidence. Each completed outcome has a signature-checked
checkpoint. Patient predictions are local research artifacts, not report text.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import joblib
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact, ttest_ind
from sklearn.metrics import roc_auc_score

from manuscript_cohort import (OUTCOMES, LABELS, NUMERIC, Outcome, load_registry,
    prepare_features, tested_mask, known_thrombophilia_mask, outcome_mask, missingness_table)
from manuscript_models import (LASSO_GRID, XGB_GRID, fit_tuned, nested_predictions,
                               metric_row, calibration_bins, wilson)


def log(message: str) -> None:
    """Print a timestamped, immediately flushed progress line without patient data."""
    print(f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {message}", flush=True)


def write_json(path: Path, value) -> None:
    """Write human-readable JSON, converting numpy scalars and nonfinite values."""
    def clean(x):
        if isinstance(x, dict): return {str(k):clean(v) for k,v in x.items()}
        if isinstance(x, (list,tuple)): return [clean(v) for v in x]
        if isinstance(x, np.integer): return int(x)
        if isinstance(x, (float,np.floating)): return float(x) if np.isfinite(x) else None
        if isinstance(x, np.bool_): return bool(x)
        return x
    path.write_text(json.dumps(clean(value),indent=2,ensure_ascii=False)+"\n")


def hash_file(path: Path) -> str:
    """Hash file contents without depending on modification timestamps."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def baseline_table(raw: pd.DataFrame, first: pd.Series, second: pd.Series,
                   first_name: str, second_name: str) -> pd.DataFrame:
    """Tidy descriptive comparison with explicit observed and missing denominators.

    Counts are shown per recorded category. Percentages use observed values,
    never an implicit unknown-to-No conversion. Numeric statistics use the same
    validity ranges as modelling. P-values are descriptive (Welch or chi-square/
    Fisher), not a variable-selection procedure.
    """
    features,_ = prepare_features(raw)
    rows=[]
    for col in features:
        a=features.loc[first,col];b=features.loc[second,col]
        observed_a=a.dropna();observed_b=b.dropna()
        levels=sorted(set(observed_a)|set(observed_b))
        p=np.nan
        table=np.array([[int((observed_a==level).sum()),int((observed_b==level).sum())] for level in levels])
        if len(levels)>1 and table.sum(axis=0).min()>0:
            if table.shape==(2,2): p=float(fisher_exact(table).pvalue)
            else: p=float(chi2_contingency(table,correction=False).pvalue)
        for level in levels:
            ac=int((observed_a==level).sum());bc=int((observed_b==level).sum())
            pa=ac/len(observed_a) if len(observed_a) else np.nan
            pb=bc/len(observed_b) if len(observed_b) else np.nan
            den=np.sqrt((pa*(1-pa)+pb*(1-pb))/2)
            rows.append(dict(variable=col,label=LABELS[col],category=level,first_group=first_name,second_group=second_name,
                first_n=len(a),second_n=len(b),first_observed_n=len(observed_a),second_observed_n=len(observed_b),
                first_missing_n=int(a.isna().sum()),second_missing_n=int(b.isna().sum()),
                first_count=ac,second_count=bc,first_percent=pa*100,second_percent=pb*100,
                standardized_difference=(pa-pb)/den if den>0 else np.nan,p_value=p))
    for col,(lo,hi,*_) in NUMERIC.items():
        if col not in raw: continue
        values=pd.to_numeric(raw[col],errors='coerce');values=values.where(values.between(lo,hi))
        a=values.loc[first].dropna();b=values.loc[second].dropna()
        den=np.sqrt((a.var()+b.var())/2)
        row=dict(variable=col,label=LABELS[col],category='continuous',first_group=first_name,second_group=second_name,
                 first_n=int(first.sum()),second_n=int(second.sum()),first_observed_n=len(a),second_observed_n=len(b),
                 first_missing_n=int(first.sum())-len(a),second_missing_n=int(second.sum())-len(b),
                 standardized_difference=(a.mean()-b.mean())/den if den>0 else np.nan,
                 p_value=float(ttest_ind(a,b,equal_var=False).pvalue) if len(a)>1 and len(b)>1 else np.nan)
        for name,s in [('first',a),('second',b)]:
            row.update({name+'_mean':s.mean(),name+'_sd':s.std(),name+'_median':s.median(),
                        name+'_q1':s.quantile(.25),name+'_q3':s.quantile(.75)})
        rows.append(row)
    return pd.DataFrame(rows)


def descriptive_exports(raw: pd.DataFrame, X: pd.DataFrame, output: Path) -> None:
    """Rebuild mutually exclusive baselines, subtype denominators and sex summaries."""
    tested=tested_mask(raw); known=known_thrombophilia_mask(raw)
    baseline_table(raw,tested,~tested,'Tested','Not tested or unknown').to_csv(output/'table1_baseline.csv',index=False)
    baseline_table(raw,raw.ana_dura.eq('Buscada positivo'),raw.ana_dura.eq('Buscada negativo'),
                   'Positive','Negative').to_csv(output/'table2_positive_negative.csv',index=False)
    pd.concat([missingness_table(raw,X,pd.Series(True,index=raw.index),'Full registry'),
               missingness_table(raw,X,tested,'Globally tested')]).to_csv(output/'supplement_missingness.csv',index=False)
    cohort=[]
    for o in OUTCOMES:
        neg='Buscada negativo' if o.column=='ana_dura' else 'No'
        binary=raw[o.column].astype('string').isin([o.positive,neg]);s=raw[o.column].astype('string')
        m=outcome_mask(raw,o)
        cohort.append(dict(outcome=o.column,label=o.label,priority=o.priority,registry_n=len(raw),
            tested_n=int(tested.sum()),tested_binary_n=int((tested&binary).sum()),
            tested_positive_n=int((tested&s.eq(o.positive).fillna(False)).sum()),
            tested_unavailable_n=int((tested&~binary).sum()),outside_tested_binary_n=int((~tested&binary).sum()),
            known_excluded_n=int((tested&binary&known).sum()),eligible_n=int(m.sum()),
            eligible_positive_n=int(s.loc[m].eq(o.positive).sum())))
    pd.DataFrame(cohort).to_csv(output/'supplement_outcome_denominators.csv',index=False)
    sex=[]
    for label in ['Hombre','Mujer']:
        mask=raw.sexo.eq(label);n=int(mask.sum());tested_n=int((mask&tested).sum());p=int((mask&raw.ana_dura.eq('Buscada positivo')).sum())
        tl,tu=wilson(tested_n,n);pl,pu=wilson(p,tested_n)
        sex.append(dict(sex='Male' if label=='Hombre' else 'Female',n=n,tested_n=tested_n,positive_n=p,
                        tested_percent=100*tested_n/n,testing_lower=tl,testing_upper=tu,
                        yield_percent=100*p/tested_n,yield_lower=pl,yield_upper=pu))
    pd.DataFrame(sex).to_csv(output/'sex_testing_yield.csv',index=False)
    effects=[]
    for endpoint in ['tested','positive']:
        male,female=sex
        a=male[endpoint+'_n'];c=female[endpoint+'_n']
        nm=male['n' if endpoint=='tested' else 'tested_n'];nf=female['n' if endpoint=='tested' else 'tested_n']
        b=nm-a;d=nf-c;rr=(a/nm)/(c/nf);odds=a*d/(b*c);rd=a/nm-c/nf
        rrse=np.sqrt(1/a-1/nm+1/c-1/nf);orse=np.sqrt(1/a+1/b+1/c+1/d)
        rdse=np.sqrt(a/nm*(1-a/nm)/nm+c/nf*(1-c/nf)/nf)
        effects.append(dict(endpoint=endpoint,risk_ratio=rr,rr_lower=np.exp(np.log(rr)-1.96*rrse),
            rr_upper=np.exp(np.log(rr)+1.96*rrse),odds_ratio=odds,or_lower=np.exp(np.log(odds)-1.96*orse),
            or_upper=np.exp(np.log(odds)+1.96*orse),risk_difference=rd,rd_lower=rd-1.96*rdse,rd_upper=rd+1.96*rdse,
            p_value=float(chi2_contingency([[a,b],[c,d]],correction=False).pvalue)))
    pd.DataFrame(effects).to_csv(output/'sex_effect_sizes.csv',index=False)
    write_json(output/'registry_flow.json',dict(registry_n=len(raw),tested_n=int(tested.sum()),
        explicitly_not_tested_n=int(raw.ana_dura.eq('No buscada').sum()),
        unknown_testing_n=int(raw.ana_dura.isna().sum()),not_tested_or_unknown_n=int((~tested).sum()),
        positive_n=int(raw.ana_dura.eq('Buscada positivo').sum()),negative_n=int(raw.ana_dura.eq('Buscada negativo').sum()),
        known_thrombophilia_tested_n=int((tested&known).sum())))


def association_exports(raw: pd.DataFrame, X: pd.DataFrame, output: Path) -> None:
    """Recalculate the published example profiles and bounded negative FP-Growth rules.

    Rules are descriptive within the eligible composite cohort, not validated
    predictions. Antecedent support and joint rule support are separate exports.
    Clinical descriptors are fixed in advance and unknowns activate no descriptor.
    """
    from mlxtend.frequent_patterns import fpgrowth
    m=outcome_mask(raw,OUTCOMES[0]);f=X.loc[m];negative=raw.loc[m,'ana_dura'].eq('Buscada negativo').to_numpy()
    def eq(c,value): return f[c].eq(value).fillna(False).to_numpy(dtype=bool)
    descriptors={
        'Female':eq('sexo','Female'),'Age <50':eq('edad','<50'),'Age 50–69':eq('edad','50–69'),
        'No prior VTE':eq('fr_tvp_a','No'),'Hemoglobin ≥12':eq('ana_hemo','≥12'),
        'Negative D-dimer':eq('ana_dime','Negative'),'No cancer':eq('fr_cance','No'),
        'No hormone exposure':eq('fr_estro','No'),'Normal platelets':eq('ana_plaq','144–400'),
        'No immobilization':eq('fr_inmov','No'),'Normal creatinine':eq('ana_crea','Normal'),
        'Male':eq('sexo','Male'),'Age ≥70':eq('edad','≥70'),'Prior VTE':eq('fr_tvp_a','Yes'),
        'Cancer':eq('fr_cance','Yes'),'Immobilization':eq('fr_inmov','Yes')}
    def row(names, mask):
        a=int(mask.sum());joint=int((mask&negative).sum());n=len(mask);conf=joint/a if a else np.nan;base=negative.mean()
        return dict(antecedent=' AND '.join(names),n=n,antecedent_n=a,negative_n=joint,
                    antecedent_support=a/n,rule_support=joint/n,confidence=conf,lift=conf/base,
                    leverage=joint/n-(a/n)*base)
    examples=[['Female','Age <50','No prior VTE'],['Hemoglobin ≥12','Negative D-dimer','No cancer'],
              ['Female','Age 50–69','No hormone exposure'],['Normal platelets','No immobilization','No prior VTE'],
              ['Female','No prior VTE','Normal creatinine']]
    pd.DataFrame([row(names,np.logical_and.reduce([descriptors[k] for k in names])) for names in examples]).to_csv(output/'table3_recalculated_profiles.csv',index=False)
    transactions=pd.DataFrame(descriptors);transactions['Negative result']=negative
    itemsets=fpgrowth(transactions,min_support=.01,use_colnames=True,max_len=4)
    rules=[]
    for item in itemsets.itertuples():
        names=sorted(set(item.itemsets)-{'Negative result'})
        if 'Negative result' in item.itemsets and names:
            r=row(names,np.logical_and.reduce([descriptors[k] for k in names]))
            if r['confidence']>=.8 and r['lift']>=1:rules.append(r)
    result=pd.DataFrame(rules,columns=list(row([],negative).keys()))
    if len(result):result=result.sort_values(['confidence','lift','rule_support'],ascending=False)
    result.to_csv(output/'supplement_negative_association_rules.csv',index=False)
    write_json(output/'association_config.json',dict(cohort_n=int(m.sum()),min_joint_support=.01,min_confidence=.8,
        min_lift=1,max_antecedents=3,retained_rules=len(result),descriptors=list(descriptors),
        note='Descriptive, not cross-validated; old No DVT wording is operationalized as No prior VTE.'))


def run_outcome(raw: pd.DataFrame, features: pd.DataFrame, outcome: Outcome,
                output: Path, config: dict) -> None:
    """Train primary paired models and an incomplete-data tree sensitivity analysis."""
    output.mkdir(parents=True,exist_ok=True)
    mask=outcome_mask(raw,outcome);year=pd.to_datetime(raw.fecha_di,errors='coerce').dt.year
    development=mask&year.le(config['cutoff_year']);holdout=mask&year.gt(config['cutoff_year'])
    availability=features.loc[development].isna().mean();variable=features.loc[development].nunique().gt(1)
    columns=availability.index[(availability<=config['max_missing'])&variable].tolist()
    if not columns:raise ValueError(f'{outcome.column}: no complete-case candidate predictors.')
    pd.DataFrame(dict(variable=features.columns,label=[LABELS[c] for c in features],
        development_missing_fraction=availability,nonconstant=variable,
        retained_for_primary=features.columns.isin(columns))).to_csv(output/'candidate_availability.csv',index=False)
    complete=mask&features[columns].notna().all(axis=1)
    baseline_table(raw,complete,mask&~complete,'Complete cases','Excluded for missing predictors').to_csv(output/'included_vs_excluded.csv',index=False)
    baseline_table(raw,development,holdout,'Development eligible','Temporal eligible').to_csv(output/'development_vs_temporal.csv',index=False)
    missingness_table(raw,features,mask,outcome.label).to_csv(output/'missingness.csv',index=False)
    flow=dict(outcome=outcome.column,label=outcome.label,priority=outcome.priority,eligible_n=int(mask.sum()),
        eligible_positive_n=int(raw.loc[mask,outcome.column].eq(outcome.positive).sum()),
        development_eligible_n=int(development.sum()),temporal_eligible_n=int(holdout.sum()),
        missing_date_n=int((mask&year.isna()).sum()),candidate_n=len(columns),complete_case_n=int(complete.sum()),
        complete_case_positive_n=int(raw.loc[complete,outcome.column].eq(outcome.positive).sum()),
        missing_excluded_n=int((mask&~complete).sum()),development_complete_n=int((development&complete).sum()),
        temporal_complete_n=int((holdout&complete).sum()),cutoff_year=config['cutoff_year'])
    write_json(output/'cohort_flow.json',flow)
    result_frames=[]; search_frames=[]; final_metadata=[]
    experiments=[('primary_complete_case','lasso',development&complete,holdout&complete,columns),
                 ('primary_complete_case','xgb',development&complete,holdout&complete,columns),
                 ('sensitivity_native_missing','xgb',development,holdout,features.columns[variable].tolist())]
    # The guided comparison is exploratory and composite-only; its descriptors were
    # prespecified from the previous manuscript, never selected on validation outcomes.
    if outcome.column=='ana_dura':
        guided=[c for c in ['sexo','edad','fr_tvp_a','ana_hemo','ana_dime','fr_cance','fr_inmov','fr_estro'] if c in columns]
        experiments.append(('guided_complete_case','lasso',development&complete,holdout&complete,guided))
    for analysis,kind,dev,val,cols in experiments:
        label=f'{outcome.column}/{analysis}/{kind}'
        log(f'{label}: development n={int(dev.sum())}, holdout n={int(val.sum())}, predictors={len(cols)}')
        X=features.loc[dev,cols].reset_index(drop=True);y=raw.loc[dev,outcome.column].eq(outcome.positive).to_numpy(dtype=int)
        ids=raw.loc[dev,'id_pacie'].to_numpy()
        if min(np.bincount(y,minlength=2))<3:
            raise ValueError(f'{label}: fewer than three development events or nonevents.')
        pred,search=nested_predictions(X,y,ids,kind,seed=config['seed'],outer_splits=config['outer_splits'],
            inner_splits=config['inner_splits'],min_sensitivity=config['min_sensitivity'],threads=config['threads'],
            compact=config['compact'],progress=lambda msg:log(f'{label}: {msg}'))
        result_frames.append(pred.assign(analysis=analysis,validation='nested_cv'))
        search_frames.append(search.assign(analysis=analysis,kind=kind))
        log(f'{label}: fitting locked development model')
        fit=fit_tuned(X,y,kind,config['seed'],config['inner_splits'],config['min_sensitivity'],config['threads'],config['compact'])
        tag=f'{analysis}_{kind}'
        joblib.dump(dict(model=fit.estimator,columns=cols,thresholds=fit.thresholds,outcome=asdict(outcome)),output/f'{tag}_model.joblib')
        fit.search.to_csv(output/f'{tag}_final_search.csv',index=False)
        meta=dict(analysis=analysis,kind=kind,parameters=fit.parameters,thresholds=fit.thresholds,
                  training_n=len(y),training_positive_n=int(y.sum()),columns=cols,inner_splits=fit.inner_splits)
        if kind=='lasso':
            points=fit.estimator.points_.copy();points['label']=points.variable.map(LABELS)
            points.to_csv(output/f'{tag}_points.csv',index=False)
            fit.estimator.screen_.to_csv(output/f'{tag}_univariable_screen.csv',index=False)
            meta.update(score_intercept=fit.estimator.offset_,score_slope=fit.estimator.slope_,
                        integer_cutoff=fit.estimator.integer_cutoff(fit.thresholds['Automatic integer score']))
        final_metadata.append(meta)
        if val.any():
            vx=features.loc[val,cols];vy=raw.loc[val,outcome.column].eq(outcome.positive).to_numpy(dtype=int)
            for name,p in fit.estimator.probabilities(vx).items():
                score=fit.estimator.point_scores(vx) if name=='Automatic integer score' else p
                cutoff=fit.estimator.integer_cutoff(fit.thresholds[name]) if name=='Automatic integer score' else np.nan
                result_frames.append(pd.DataFrame(dict(id_pacie=raw.loc[val,'id_pacie'].to_numpy(),fold=0,y_true=vy,
                    model=name,probability=p,raw_score=score,threshold=fit.thresholds[name],integer_cutoff=cutoff,
                    predicted_positive=p>=fit.thresholds[name],analysis=analysis,validation='temporal_holdout')))
    predictions=pd.concat(result_frames,ignore_index=True).assign(outcome=outcome.column)
    predictions.to_parquet(output/'predictions.parquet',index=False)
    pd.concat(search_frames,ignore_index=True).to_csv(output/'nested_hyperparameter_search.csv',index=False)
    write_json(output/'final_models.json',final_metadata)
    metrics=[];calibrations=[]
    for (analysis,validation,model),frame in predictions.groupby(['analysis','validation','model'],sort=False):
        row=metric_row(frame,bootstrap=config['bootstrap'],seed=config['seed'])
        bins=calibration_bins(frame)
        row.update(outcome=outcome.column,label=outcome.label,priority=outcome.priority,analysis=analysis,validation=validation,model=model,
                   mace=float(bins.absolute_error.mean()),ece=float(np.average(bins.absolute_error,weights=bins.n)))
        metrics.append(row);calibrations.append(bins.assign(outcome=outcome.column,analysis=analysis,validation=validation,model=model))
    pd.DataFrame(metrics).to_csv(output/'metrics.csv',index=False)
    pd.concat(calibrations,ignore_index=True).to_csv(output/'calibration.csv',index=False)
    checks=validate_predictions(predictions,pd.DataFrame(metrics),raw,outcome,config['cutoff_year'])
    write_json(output/'quality_checks.json',checks)
    log(f'{outcome.column}: completed; all numerical integrity checks passed')


def validate_predictions(predictions: pd.DataFrame, metrics: pd.DataFrame,
                         raw: pd.DataFrame, outcome: Outcome, cutoff_year: int) -> dict:
    """Fail on cohort leakage, duplicate predictions, broken counts or nonfinite risk."""
    eligible=set(raw.loc[outcome_mask(raw,outcome),'id_pacie'])
    assert set(predictions.id_pacie).issubset(eligible), 'Prediction outside eligible tested cohort'
    assert np.isfinite(predictions.probability).all() and predictions.probability.between(0,1).all()
    assert not predictions.duplicated(['id_pacie','analysis','validation','model']).any()
    years=pd.to_datetime(raw.set_index('id_pacie').fecha_di).dt.year
    for val,group in predictions.groupby('validation'):
        actual=years.loc[group.id_pacie]
        assert (actual.le(cutoff_year) if val=='nested_cv' else actual.gt(cutoff_year)).all()
    assert (metrics[['tp','fp','tn','fn']].sum(axis=1)==metrics.n).all()
    assert ((metrics.tp+metrics.fn)==metrics.positive_n).all()
    assert np.allclose(metrics.tests_avoided_per_1000,1000*(metrics.tn+metrics.fn)/metrics.n)
    assert np.allclose(metrics.missed_positive_per_1000,1000*metrics.fn/metrics.n)
    primary=predictions[predictions.analysis.eq('primary_complete_case')]
    for _,g in primary.groupby('validation'):
        idsets=[set(x.id_pacie) for _,x in g.groupby('model')]
        assert all(ids==idsets[0] for ids in idsets), 'Unpaired primary comparison'
    integer=predictions[predictions.model.eq('Automatic integer score')]
    assert np.array_equal(integer.predicted_positive.to_numpy(),(integer.raw_score>=integer.integer_cutoff).to_numpy())
    return dict(eligible_patients_only=True,unique_predictions=True,dates_disjoint=True,
                paired_primary_cohorts=True,finite_probabilities=True,confusion_counts_match=True,
                utility_identity=True,integer_probability_decisions_match=True)


def run_reanalysis(data: Path, output: Path, *, outcomes: list[str] | None = None,
                   cutoff_year: int = 2021, max_missing: float = .4, seed: int = 42,
                   outer_splits: int = 5, inner_splits: int = 5, min_sensitivity: float = .9,
                   threads: int = 2, bootstrap: int = 200, compact: bool = False,
                   resume: bool = False, reports: bool = True) -> Path:
    """Run the evidence pipeline and write an auditable, self-contained result package.

    ``compact`` reduces search grids for integration testing only and marks the
    manifest accordingly. It never silently samples patients. Resume requires
    matching raw-data, analysis-code and configuration hashes.
    """
    if not 0<=max_missing<1 or not 0<min_sensitivity<=1:
        raise ValueError('Invalid missingness or sensitivity bound.')
    if outer_splits<2 or inner_splits<2 or threads<1 or bootstrap<0:
        raise ValueError('CV needs >=2 folds, threads >=1, bootstrap >=0.')
    selected=[o for o in OUTCOMES if outcomes is None or o.column in outcomes]
    if not selected or (outcomes and set(outcomes)-{o.column for o in OUTCOMES}):
        raise ValueError('Unknown or empty outcome selection.')
    output.mkdir(parents=True,exist_ok=True)
    config=dict(cutoff_year=cutoff_year,max_missing=max_missing,seed=seed,outer_splits=outer_splits,
                inner_splits=inner_splits,min_sensitivity=min_sensitivity,threads=threads,bootstrap=bootstrap,compact=compact)
    code={p.name:hash_file(p) for p in [Path(__file__),Path(__file__).with_name('manuscript_models.py'),Path(__file__).with_name('manuscript_cohort.py')]}
    source_hash=hash_file(data);signature=hashlib.sha256(json.dumps(dict(config=config,code=code,data=source_hash),sort_keys=True).encode()).hexdigest()
    manifest=dict(status='running',started_utc=datetime.now(timezone.utc).isoformat(),data_path=str(data.resolve()),
        data_sha256=source_hash,analysis_code_sha256=code,signature=signature,config=config,
        outcomes=[o.column for o in selected],lasso_grid=LASSO_GRID,xgboost_grid=XGB_GRID,
        versions={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','xgboost','mlxtend','joblib']})
    write_json(output/'run_manifest.json',manifest)
    raw=load_registry(data);features,quality=prepare_features(raw)
    quality.to_csv(output/'numeric_and_category_quality.csv',index=False)
    descriptive_exports(raw,features,output);association_exports(raw,features,output)
    try:
        for outcome in selected:
            directory=output/outcome.column; checkpoint=directory/'completed.json'
            if resume and checkpoint.exists():
                old=json.loads(checkpoint.read_text())
                if old.get('signature')!=signature:
                    raise ValueError(f'{outcome.column}: checkpoint signature differs; use a new output directory.')
                log(f'{outcome.column}: reusing verified checkpoint')
                validate_predictions(pd.read_parquet(directory/'predictions.parquet'),pd.read_csv(directory/'metrics.csv'),raw,outcome,cutoff_year)
                continue
            if checkpoint.exists():
                raise FileExistsError(f'{checkpoint} exists. Use --resume or a new output directory.')
            run_outcome(raw,features,outcome,directory,config)
            write_json(checkpoint,dict(signature=signature,completed_utc=datetime.now(timezone.utc).isoformat()))
        metrics=pd.concat([pd.read_csv(output/o.column/'metrics.csv') for o in selected],ignore_index=True)
        metrics.to_csv(output/'all_model_metrics.csv',index=False)
        metrics.query("analysis=='primary_complete_case' and validation=='nested_cv'").to_csv(output/'table5_primary_performance.csv',index=False)
        metrics.query("validation=='temporal_holdout'").to_csv(output/'supplement_temporal_validation.csv',index=False)
        metrics.query("analysis=='sensitivity_native_missing'").to_csv(output/'supplement_native_missing_performance.csv',index=False)
        pd.concat([pd.read_csv(output/o.column/'calibration.csv') for o in selected]).to_csv(output/'supplement_calibration.csv',index=False)
        pd.DataFrame([json.loads((output/o.column/'cohort_flow.json').read_text()) for o in selected]).to_csv(output/'model_cohort_flow.csv',index=False)
        if reports:
            from manuscript_reporting import generate_reports
            generate_reports(output)
        manifest.update(status='complete',completed_utc=datetime.now(timezone.utc).isoformat(),
                        outputs_sha256={str(p.relative_to(output)):hash_file(p) for p in output.rglob('*') if p.is_file() and p.name!='run_manifest.json'})
        write_json(output/'run_manifest.json',manifest)
    except Exception as exc:
        manifest.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        write_json(output/'run_manifest.json',manifest)
        raise
    return output/'coauthor_responses.md'


def main() -> None:
    """Parse reproducible analysis settings; manuscript defaults use five-by-five CV."""
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=Path('data/patD.parquet'))
    parser.add_argument('--output-dir',type=Path,default=Path('out/manuscript_reanalysis_2026-09-07'))
    parser.add_argument('--outcomes',nargs='+',choices=[o.column for o in OUTCOMES])
    parser.add_argument('--cutoff-year',type=int,default=2021)
    parser.add_argument('--max-missing',type=float,default=.4,help='Development-only candidate missingness ceiling; primary complete cases use retained candidates.')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--outer-splits',type=int,default=5)
    parser.add_argument('--inner-splits',type=int,default=5)
    parser.add_argument('--min-sensitivity',type=float,default=.9)
    parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--bootstrap',type=int,default=200)
    parser.add_argument('--compact',action='store_true',help='Test-only reduced search grid; never a publication run.')
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--no-reports',action='store_true',help='Generate numerical outputs only; reports can be generated separately.')
    args=parser.parse_args()
    path=run_reanalysis(args.data,args.output_dir,outcomes=args.outcomes,cutoff_year=args.cutoff_year,
        max_missing=args.max_missing,seed=args.seed,outer_splits=args.outer_splits,inner_splits=args.inner_splits,
        min_sensitivity=args.min_sensitivity,threads=args.threads,bootstrap=args.bootstrap,compact=args.compact,
        resume=args.resume,reports=not args.no_reports)
    log(f'Completed result directory: {path.parent}')

if __name__=='__main__':
    main()
