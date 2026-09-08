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
