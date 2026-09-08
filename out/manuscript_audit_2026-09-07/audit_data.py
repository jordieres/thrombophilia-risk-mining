from pathlib import Path
import sys, json
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'src'))
from data_processor import ClinicalDataProcessor
out=Path(__file__).parent
raw=pd.read_parquet(ROOT/'data/patD.parquet'); clean=ClinicalDataProcessor(str(ROOT/'data/patD.parquet')).transform_pipeline(); slim=pd.read_parquet(ROOT/'data/patD_slim.parquet')
tested=clean.ana_dura.isin(['Buscada positivo','Buscada negativo'])
rows=[]
for col in ['var154','var155','var156','var157','var158','var161','andujak2']:
 s=raw[col].astype('string'); binary=s.isin(['Sí','No'])
 rows.append(dict(outcome=col,full_binary_n=int(binary.sum()),tested_binary_n=int((binary&tested).sum()),tested_positive_n=int(((s=='Sí').fillna(False)&tested).sum()),tested_negative_n=int(((s=='No').fillna(False)&tested).sum()),tested_unavailable_n=int((~binary&tested).sum()),outside_tested_binary_n=int((binary&~tested).sum()),outside_tested_positive_n=int(((s=='Sí').fillna(False)&~tested).sum()),positive_pct=100*int(((s=='Sí').fillna(False)&tested).sum())/int((binary&tested).sum())))
pd.DataFrame(rows).to_csv(out/'cohort_denominators.csv',index=False); print(pd.DataFrame(rows).to_string(index=False))
missing=[]
sentinel=np.iinfo(np.int64).min
for name,df in [('full_raw',raw),('tested_raw',raw.loc[tested]),('slim_tested',slim[slim.ana_dura.isin(['Buscada positivo','Buscada negativo'])])]:
 for col in df.columns:
  s=df[col]; null=s.isna(); sent=s.eq(sentinel).fillna(False) if pd.api.types.is_numeric_dtype(s) else pd.Series(False,index=s.index)
  explicit=s.astype('string').str.strip().str.casefold().isin(['missing','no practicado','no realizada','no realizado','no realizado/a','no consta','desconocido'])
  missing.append(dict(cohort=name,variable=col,n=len(df),null_n=int(null.sum()),sentinel_n=int(sent.sum()),explicit_unknown_or_not_performed_n=int(explicit.sum()),unavailable_n=int((null|sent|explicit).sum()),unavailable_pct=100*(null|sent|explicit).mean()))
pd.DataFrame(missing).to_csv(out/'missingness_by_variable.csv',index=False)
from manuscript_support import build_tested_vs_not_tested_table
base=build_tested_vs_not_tested_table(clean)
# Complete the manuscript's baseline variables using the documented preprocessing.
for col,label in [('hip_art','Hypertension'),('diabetes','Diabetes'),('fum_act','Active smoking'),('fr_antfa','Family history of VTE')]:
 vals=[]
 for mask in [tested,~tested]:
  s=clean.loc[mask,col].astype('string'); yes=s.isin(['Sí','Si','Yes']); vals.append(f'{yes.sum()} ({100*yes.mean():.1f}%)')
 base.loc[len(base)]=[label,*vals,np.nan]
for mask,label in [(tested,'Tested'),(~tested,'Not_Tested')]:
 q=clean.loc[mask,'edad'].quantile([.25,.5,.75]).tolist(); print(label,'age quantiles',q)
base.to_csv(out/'baseline_recomputed.csv',index=False)
print('BASELINE',base.to_string(index=False));print('ana_port',pd.crosstab(raw.ana_port,raw.ana_dura).to_string())
print('D DIMER',raw.ana_dime.value_counts(dropna=False).to_dict())
print('slim D DIMER',slim.ana_dime.value_counts(dropna=False).to_dict())
print('RAW unique ids',raw.id_pacie.nunique())
# Arithmetic checks: implied rates, not new model estimates.
a=[]
for label,n,p,se,sp,ppv,npv in [('Composite XGB',22874,8345,.900,.187,.402,.755),('Composite integer',22874,8345,.932,.094,.384,.695),('APS XGB',10710,1908,.900,.587,.123,.989),('APS integer',10710,1908,.905,.472,.100,.987),('FVL XGB',10638,2048,.901,.610,.137,.989),('FVL integer',10638,2048,.942,.407,.099,.990),('Prothrombin XGB',10376,1602,.901,.574,.102,.991),('Prothrombin integer',10376,1602,.940,.391,.076,.992),('Protein S XGB',10315,757,.901,.511,.043,.995),('Protein S integer',10315,757,.918,.283,.030,.993),('Protein C XGB',10275,356,.902,.399,.016,.997),('Protein C integer',10275,356,.950,.225,.013,.998)]:
 tp=p*se;fn=p*(1-se);tn=(n-p)*sp;fp=(n-p)*(1-sp)
 a.append(dict(model=label,n_reported=n,positive_reported=p,ppv_reported=ppv,ppv_implied=tp/(tp+fp),npv_reported=npv,npv_implied=tn/(tn+fn),avoided_per_1000_implied=(tn+fn)/n*1000,missed_per_1000_implied=fn/n*1000))
pd.DataFrame(a).to_csv(out/'table5_arithmetic_check_NOT_model_results.csv',index=False)
# Link historical score outputs to source cohort labels, without publishing patient data.
links=[]
for f in [ROOT/'out/clinical_risk_score_per_patient.csv',*sorted((ROOT/'out/archive').glob('*_score/clinical_risk_score_per_patient.csv'))]:
 d=pd.read_csv(f); target=next((c for c in ['ana_dura','var154','var155','var156','var157','var161'] if c in d),None)
 if 'id_pacie' not in d: continue
 joined=d[['id_pacie']].merge(raw[['id_pacie','ana_dura']],on='id_pacie',how='left',validate='many_to_one'); status=joined.ana_dura.isin(['Buscada positivo','Buscada negativo'])
 links.append(dict(file=str(f.relative_to(ROOT)),n=len(d),target=target,tested_n=int(status.sum()),outside_tested_n=int((~status).sum())))
pd.DataFrame(links).to_csv(out/'historical_prediction_cohorts.csv',index=False);print('HISTORICAL',links)
