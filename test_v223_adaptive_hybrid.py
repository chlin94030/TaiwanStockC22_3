import json,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from lab_backtest import Case
from lab_config import Config
from v22_engine import V22Case,validate_profiles,evaluate,evaluate_at
from v22_regime import ACTIONS
from v223_adaptive import adaptive_weights
from v22_runner import _export,_choose_candidate,V22_VERSION


def _case(date, horizon=20, stage='A1', good='f1', n=40):
    d=pd.Timestamp(date);tick=np.array([f'{1000+i}.TW' for i in range(n)])
    x=np.linspace(.02,.98,n);ranks=np.column_stack([x,1-x])
    net=(x-.5)*.20 if good=='f1' else ((1-x)-.5)*.20
    base=Case(d,tick,ranks,np.ones(n)*2e8,net,np.ones(n,bool),np.ones(n)*-.03,.01,.005,0.,d+pd.Timedelta(days=1),d+pd.Timedelta(days=horizon+2),('f1','f2'))
    return V22Case(base,np.array(['S'+str(i%8) for i in range(n)]),np.ones(n)*50,np.zeros(n),np.zeros(n),np.ones(n),np.ones(n),stage,.8,ACTIONS[stage],horizon)


def _profiles(model='manual', blend=.35):
    q={
      'schema':3,'candidates':[{
        'name':'x','model_type':model,'selection_eligible':True,
        'horizon_stage_weights':{
          '5':{'A1':{'f1':1.0}},
          '20':{'A1':{'f1':.5,'f2':.5}},
          '60':{'A1':{'f2':1.0}},
        },
        'stage_exposure':{'A1':1.,'A2':0.,'A3':0.,'B1':0.,'B2':0.,'B3':0.,'UNKNOWN':0.},
        'discipline':False,
        'adaptive':{'blend':blend,'lookback_cases':36,'min_history_cases':12,'stage_mix':.6,'prior_floor':.1}
      }]}
    return validate_profiles(q,['f1','f2'])[0]


def _spec():
    return {'pool_rule':'KOSTO300','top_k':10,'capital':1e6,'stage_confidence_floor':.03,'sector_cap':1.,'max_rsi':100.,'max_bias20':1.,'b3_confirmation_rank':0.}


def test_schema3_horizon_specific_weights_change_selection():
    cfg=Config(end='2026-01-01',top_k=10)
    p=_profiles('manual')
    a=evaluate(_case('2024-01-31',5),p,cfg,_spec())
    b=evaluate(_case('2024-01-31',60),p,cfg,_spec())
    assert a['selected'] != b['selected']
    assert a['effective_weights']=={'f1':1.0}
    assert b['effective_weights']=={'f2':1.0}


def test_schema2_backward_compatible():
    obj={'schema':2,'candidates':[{'name':'old','stage_weights':{'A1':{'f1':1.0}},
        'stage_exposure':{'A1':1.,'A2':0.,'A3':0.,'B1':0.,'B2':0.,'B3':0.,'UNKNOWN':0.},'discipline':False}]}
    c=validate_profiles(obj,['f1'])[0]
    assert c['model_type']=='manual' and all(c['weights_by_horizon'][h]['A1']=={'f1':1.0} for h in (5,20,60))


def test_hybrid_ic_uses_only_matured_past_and_moves_toward_good_factor():
    cases=[]
    for i in range(18):
        # monthly spacing keeps old 20d exits mature before later signals
        cases.append(_case(pd.Timestamp('2022-01-31')+pd.offsets.MonthEnd(i),20,good='f1'))
    p=_profiles('hybrid_ic',.35)
    w,diag=adaptive_weights(cases,17,p)
    assert diag['history_cases']>=12
    assert w['f1']>w['f2']
    before=dict(w)
    # Current/future outcome mutation must not alter its own date-T weights.
    cases[17].base.net[:]=999
    w2,_=adaptive_weights(cases,17,p)
    assert w2==before


def test_evaluate_at_selection_ignores_current_future_label():
    cases=[_case(pd.Timestamp('2022-01-31')+pd.offsets.MonthEnd(i),20,good='f1') for i in range(18)]
    cfg=Config(end='2026-01-01',top_k=10);p=_profiles('ic_adaptive',.65)
    a=evaluate_at(cases,17,p,cfg,_spec())
    cases[17].base.net[:]=np.linspace(-99,99,len(cases[17].base.net))
    b=evaluate_at(cases,17,p,cfg,_spec())
    assert a['selected']==b['selected'] and a['effective_weights']==b['effective_weights']


def test_diagnostic_candidate_cannot_win():
    table=[{'candidate_id':'d','score':.9,'selection_eligible':False},{'candidate_id':'m','score':.1,'selection_eligible':True}]
    cands=[{'id':'d','name':'diag'},{'id':'m','name':'manual'}]
    row,c=_choose_candidate(table,cands)
    assert row['candidate_id']=='m' and c['name']=='manual'


def test_export_contains_excel_and_zip(tmp_path):
    pd.DataFrame([{'horizon':5,'name':'x'}]).to_csv(tmp_path/'candidate_ranking.csv',index=False)
    result={'version':V22_VERSION,'mode':'fast','pool_rule':'KOSTO300','data_scope':{},'automatic_orders_authorized':False,'global_optimum_proven':False,
        'models':{'5':{'pool':'KOSTO300','choice':{'name':'x','model_type':'manual'},'choice_score':.01,'verdict':'DEVELOPMENT_ONLY_NOT_ACCEPTANCE','final_tail_inspected':False,'stage_performance':[]}}}
    _export(tmp_path,result,[tmp_path/'candidate_ranking.csv'])
    assert (tmp_path/'V22_TEST_REPORT.xlsx').is_file()
    with zipfile.ZipFile(tmp_path/'V22_TEST_REPORT.zip') as z:
        assert z.testzip() is None
        assert 'V22_TEST_REPORT.xlsx' in z.namelist()
