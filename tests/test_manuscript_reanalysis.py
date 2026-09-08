"""Regression tests for the manuscript's cohort, leakage and reporting contracts."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from manuscript_cohort import OUTCOMES, outcome_mask, prepare_features, known_thrombophilia_mask
from manuscript_models import (CategoryEncoder,LassoPointModel,metric_row,select_threshold,
                               nested_predictions,calibration_bins)


def registry():
    return pd.DataFrame(dict(id_pacie=[1,2,3,4,5],ana_dura=['Buscada positivo','Buscada negativo','No buscada',None,'Buscada positivo'],
        ana_port=['No']*5,e_con_af=['No','No','No','No','Sí'],var156=['Sí','No','No','No','Sí'],
        sexo=['Mujer','Hombre','Mujer','Hombre','Mujer'],edad=[49,50,69,70,44],
        ana_dime=['No practicado',None,'Negativo','Positivo','Positivo'],
        ana_hemo=[11.9,12,21,np.nan,13],ana_plaq=[143,144,400,401,1501],
        trat_est=['Sí','No',None,'No','No'],fr_estro=['No','Sí',None,'No','No'],
        fr_tvp_a=['Sí',None,'No','No','No'],ddvalmcg=[1,2,3,4,5],evn_reci=['Sí']*5,
        tv_l_vpo=['No','Sí',None,'No','No'],tv_l_vme=['No',None,'No',None,'No'],tv_l_ves=['No','No','No','No','No']))


def test_subtype_negative_cannot_admit_unknown_or_untested_controls():
    raw=registry();o=next(o for o in OUTCOMES if o.column=='var156')
    assert raw.loc[outcome_mask(raw,o),'id_pacie'].tolist()==[1,2]
    assert known_thrombophilia_mask(raw).tolist()==[False,False,False,False,True]


def test_fixed_cutpoints_unknown_history_and_ddimer_are_not_conflated():
    raw=registry();x,a=prepare_features(raw)
    assert x.edad.tolist()==['<50','50–69','50–69','≥70','<50']
    assert x.ana_plaq.iloc[:4].tolist()==['<144','144–400','144–400','>400']
    assert pd.isna(x.ana_plaq.iloc[4]) and pd.isna(x.ana_hemo.iloc[2])
    assert x.ana_dime.iloc[0]=='Not performed' and pd.isna(x.ana_dime.iloc[1])
    assert pd.isna(x.fr_tvp_a.iloc[1])
    assert x.splanchnic.iloc[0]=='No' and x.splanchnic.iloc[1]=='Yes' and pd.isna(x.splanchnic.iloc[2])
    assert not {'ana_dura','var156','ana_port','e_con_af','evn_reci','ddvalmcg'}&set(x)
    assert 'Statin' in a.set_index('variable').loc['trat_est','label']
    raw['evn_hemo']='future outcome';x2,_=prepare_features(raw)
    pd.testing.assert_frame_equal(x,x2)


def test_tree_encoding_preserves_observed_zero_and_marks_unknown_block_nan():
    train=pd.DataFrame({'a':['No','Yes',None],'b':['x','y','x']})
    encoder=CategoryEncoder(native_missing=True).fit(train)
    encoded=encoder.transform(pd.DataFrame({'a':['No',None,'unseen'],'b':['x','x','x']}))
    assert np.isfinite(encoded[0]).all() and (encoded[0]==0).any()
    assert np.isnan(encoded[1,:3]).all() and np.isnan(encoded[2,:3]).all()
    assert np.isfinite(encoded[1,3:]).all()
    assert 'unseen' not in encoder.encoder_.categories_[0]


def test_integer_probability_is_calibration_of_actual_points():
    rng=np.random.default_rng(4);n=160
    x=pd.DataFrame({'risk':rng.choice(['high','low'],n),'noise':rng.choice(['a','b'],n)})
    y=(rng.random(n)<np.where(x.risk=='high',.8,.2)).astype(int)
    model=LassoPointModel(C=1).fit(x,y)
    from scipy.special import expit
    p=model.probabilities(x)['Automatic integer score'];scores=model.point_scores(x)
    assert np.allclose(p,expit(model.offset_+model.slope_*scores))
    threshold=select_threshold(y,p)
    assert np.array_equal(p>=threshold,scores>=model.integer_cutoff(threshold))
    assert model.slope_>=0
    with pytest.raises(ValueError,match='complete-case'):
        model.fit(x.assign(risk=pd.NA),y)


def test_confusion_utility_and_undefined_npv_are_mathematically_consistent():
    frame=pd.DataFrame(dict(y_true=[1,1,0,0],predicted_positive=[True,False,True,False],
        probability=[.8,.2,.6,.1],raw_score=[8,2,6,1],fold=[0]*4))
    r=metric_row(frame,bootstrap=0)
    assert [r[k] for k in ['tp','fn','fp','tn']]==[1,1,1,1]
    assert r['tests_avoided_per_1000']==500 and r['missed_positive_per_1000']==250
    assert r['npv']==.5
    frame['predicted_positive']=True
    assert np.isnan(metric_row(frame,bootstrap=0)['npv'])
    assert calibration_bins(frame).n.sum()==len(frame)


def test_nested_predictions_are_unique_and_thresholds_are_training_derived(monkeypatch):
    import manuscript_models as mm
    x=pd.DataFrame({'patient_marker':np.arange(40).astype(str)})
    y=np.tile([0,1],20);ids=np.arange(40)
    calls=[]
    class Fake:
        def __init__(self,seen):self.seen=seen
        def probabilities(self,validation):
            assert not set(validation.patient_marker)&self.seen
            return {'XGBoost':np.full(len(validation),.1)}
    def fake_fit(train,train_y,*args,**kwargs):
        calls.append(set(train.patient_marker))
        return mm.TunedFit(Fake(calls[-1]),{'XGBoost':.7},{},pd.DataFrame({'candidate':[0]}),{},2)
    monkeypatch.setattr(mm,'fit_tuned',fake_fit)
    pred,_=nested_predictions(x,y,ids,'xgb',outer_splits=2,inner_splits=2)
    assert len(pred)==40 and pred.id_pacie.nunique()==40
    assert pred.threshold.eq(.7).all() and not pred.predicted_positive.any()
    # Low holdout sensitivity does not trigger threshold reselection.
    assert metric_row(pred,bootstrap=0)['sensitivity']==0


def test_routine_panel_fills_only_missing_routine_results_inside_global_testing():
    from manuscript_cohort import ROUTINE_SUBTYPES, outcome_labels
    raw=registry()
    # A tested positive evaluation can have no recorded result for this subtype.
    for col in ROUTINE_SUBTYPES:
        raw[col]=[None,'No',None,None,'Sí']
        o=next(o for o in OUTCOMES if o.column==col)
        labels=outcome_labels(raw,o)
        assert labels.iloc[0]=='No' and labels.iloc[1]=='No'
        assert pd.isna(labels.iloc[2]) and pd.isna(labels.iloc[3])
        assert labels.iloc[4]=='Sí'
        assert raw.loc[outcome_mask(raw,o),'id_pacie'].tolist()==[1,2]
        assert raw.loc[outcome_mask(raw,o,'explicit-results'),'id_pacie'].tolist()==[2]
        assert pd.isna(raw[col].iloc[0]), 'Source outcomes must not be mutated'
    raw['andujak2']=[None,'No',None,None,'Sí']
    jak=next(o for o in OUTCOMES if o.column=='andujak2')
    assert pd.isna(outcome_labels(raw,jak).iloc[0])
    assert raw.loc[outcome_mask(raw,jak),'id_pacie'].tolist()==[2]


def test_literal_missing_is_missing_but_other_nonbinary_outcome_codes_are_not_negative():
    from manuscript_cohort import outcome_labels
    raw=registry();o=next(o for o in OUTCOMES if o.column=='var156')
    raw['var156']=[' Missing ','Not performed',None,None,'Sí']
    labels=outcome_labels(raw,o)
    assert labels.iloc[0]=='No' and labels.iloc[1]=='Not performed'
    assert not outcome_mask(raw,o).iloc[1]
    with pytest.raises(ValueError,match='Unknown outcome policy'):
        outcome_labels(raw,o,'unrecognized')


def test_public_manifest_does_not_require_private_predictions_or_optional_word(tmp_path):
    from manuscript_artifacts import artifact_inventory,verify_public_artifacts
    (tmp_path/'metrics.csv').write_text('n,auc\n100,0.6\n')
    (tmp_path/'patients.csv').write_text('id_pacie,y_true\n1,0\n')
    (tmp_path/'predictions.parquet').write_bytes(b'local research data')
    (tmp_path/'report.docx').write_bytes(b'optional export')
    manifest=artifact_inventory(tmp_path)
    assert list(manifest['outputs_sha256'])==['metrics.csv']
    assert set(manifest['local_artifacts'])=={'patients.csv','predictions.parquet'}
    assert list(manifest['optional_exports'])==['report.docx']
    for name in ['patients.csv','predictions.parquet','report.docx']:(tmp_path/name).unlink()
    assert verify_public_artifacts(tmp_path,manifest)==[]
    (tmp_path/'metrics.csv').write_text('n,auc\n100,0.7\n')
    assert 'hash mismatch' in verify_public_artifacts(tmp_path,manifest)[0]


def test_existing_manifest_is_not_overwritten_when_run_reuse_is_rejected(tmp_path):
    from manuscript_reanalysis import run_reanalysis
    data=tmp_path/'raw.parquet';data.write_bytes(b'not read before reuse checks')
    output=tmp_path/'run';output.mkdir()
    original='{"status":"complete","signature":"other","outcomes":["var156"]}'
    (output/'run_manifest.json').write_text(original)
    with pytest.raises(ValueError,match='Existing run differs'):
        run_reanalysis(data,output,outcomes=['var156'])
    assert (output/'run_manifest.json').read_text()==original


def test_generated_methods_state_routine_exception_and_explicit_sensitivity():
    from manuscript_reporting import outcome_policy_text
    routine=outcome_policy_text({'outcome_policy':'routine-panel'})
    assert 'JAK2' in routine and 'remained missing' in routine
    assert 'only when ana_dura was explicitly positive or negative' in routine
    explicit=outcome_policy_text({'outcome_policy':'explicit-results'})
    assert 'remain excluded' in explicit and 'does not apply' in explicit
