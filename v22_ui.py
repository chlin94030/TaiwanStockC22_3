"""V22.3 mobile-friendly adaptive hybrid research studio."""
from pathlib import Path
import copy,json
import pandas as pd
from lab_io import read_json,DataError
from studio_pool import discover_prepared,adopt_dataset,load_dataset
from v22_runner import start_v22,v22_alive,V22_VERSION

HERE=Path(__file__).resolve().parent


def _schema3_candidate(c):
    c=copy.deepcopy(c)
    if 'horizon_stage_weights' not in c:
        sw=copy.deepcopy(c.get('stage_weights',{}));c['horizon_stage_weights']={str(h):copy.deepcopy(sw) for h in (5,20,60)}
    c.pop('stage_weights',None)
    c.setdefault('model_type','manual');c.setdefault('selection_eligible',c['model_type']!='gbm_challenger')
    if c['model_type'] in ('hybrid_ic','ic_adaptive'):
        c.setdefault('adaptive',{'blend':.35 if c['model_type']=='hybrid_ic' else .65,'lookback_cases':36,'min_history_cases':12,'stage_mix':.60,'prior_floor':.10})
    return c


def _schema3(obj):
    return {'schema':3,'candidates':[_schema3_candidate(c) for c in obj.get('candidates',[])]}


def render(st,root):
    root=Path(root);st.title('Alpha Radar V22.3｜科斯托蘭尼 × 自適應混合模型')
    st.caption(V22_VERSION+'｜市場階段先決；5/20/60日各自權重；手工科斯托蘭尼、走期IC與混合模型同條件比較。')
    st.info('保留V22核心：A1／B3買進區、A2等待／續抱代理、A3／B1賣出且不開新倉、B2現金等待。Claude版的IC走期、自適應模型與Excel報告被納入，但不取代階段閘門。')
    from lab_jobs import workspace_busy
    busy=v22_alive(root) or workspace_busy(root)
    prepared=discover_prepared(root);dataset=None
    try:
        if (root/'studio'/'active_dataset.json').exists():_,dataset=load_dataset(root)
    except Exception as exc:st.warning(str(exc))
    with st.expander('① 沿用既有資料庫',expanded=dataset is None):
        st.write('V22.3直接沿用V22.2／V21.6資料與因子快取；策略調整不重新下載全市場。')
        if prepared:
            selected=st.selectbox('已準備資料',prepared,format_func=lambda p:p['name']+' | '+str(p['start'])+' ~ '+str(p['end']))
            if st.button('採用這份資料（不下載）',disabled=busy):
                try:adopt_dataset(root,selected['run']);st.rerun()
                except Exception as exc:st.error(str(exc))
        if dataset:st.caption('Dataset ID: '+dataset['dataset_id']+'｜'+dataset['source_config']['start']+' ~ '+dataset['source_config']['end'])
    if not dataset:return

    editor=read_json(root/'v22'/'editor.json');default_profiles=read_json(HERE/'v22_profiles.json')
    loaded=editor.get('profiles',default_profiles);settings=editor.get('settings',read_json(HERE/'v22_settings.json'))
    key='v223_profiles_editor'
    if key not in st.session_state:st.session_state[key]=_schema3(loaded)
    profiles=st.session_state[key]

    with st.expander('② 一次性母池校準（策略調整時不要重跑）',expanded=False):
        st.write('比較ADV200／ADV300／KOSTO250／KOSTO300；只用開發期。完成後固定母池，後續只調策略。')
        latest=read_json(root/'v22'/'latest_pool_study.json')
        if latest.get('suggested_pool'):st.success('上次開發期建議母池：'+str(latest['suggested_pool'])+'（不是全局最適證明）')
        if st.button('執行一次母池校準',disabled=busy):
            try:start_v22(root,profiles,settings,pool_study=True);st.success('已開始母池校準。')
            except Exception as exc:st.error(str(exc))
        if latest.get('run'):
            p=Path(latest['run'])
            if (p/'V22_POOL_REPORT.zip').is_file():st.download_button('下載母池校準完整報告',(p/'V22_POOL_REPORT.zip').read_bytes(),'V22_POOL_REPORT.zip','application/zip',on_click='ignore')

    st.subheader('③ 快速策略工作台')
    st.write('日常只改固定母池內的策略。V22.3新增「5／20／60日分開權重」與Claude式走期IC；同一資料、同一成本、同一日期直接比較。')
    pool_options=['ADV200','ADV300','KOSTO250','KOSTO300'];current=settings.get('pool_rule','KOSTO300')
    pool_choice=st.selectbox('固定母池規則',pool_options,index=pool_options.index(current) if current in pool_options else 3)
    settings=dict(settings);settings['pool_rule']=pool_choice

    names=[c.get('name','') for c in profiles.get('candidates',[])]
    if names:
        c1,c2,c3=st.columns(3)
        sel=c1.selectbox('快速編輯策略',names);h=c2.selectbox('週期',[5,20,60],index=1);stage=c3.selectbox('市場階段',['A1','A2','B3'])
        cand=next(c for c in profiles['candidates'] if c['name']==sel)
        mt_opts=['manual','hybrid_ic','ic_adaptive']
        mt=st.selectbox('模型型態',mt_opts,index=mt_opts.index(cand.get('model_type','manual')) if cand.get('model_type','manual') in mt_opts else 0,
            help='manual=固定權重；hybrid_ic=科斯托蘭尼先驗為主、走期IC微調；ic_adaptive=IC調整幅度較大。')
        src=cand.get('horizon_stage_weights',{}).get(str(h),{}).get(stage,{})
        df=pd.DataFrame({'factor':list(src),'weight':list(src.values())})
        edited=st.data_editor(df,num_rows='dynamic',hide_index=True,use_container_width=True,key=f'v223edit_{sel}_{h}_{stage}')
        blend=float((cand.get('adaptive') or {}).get('blend',.35 if mt=='hybrid_ic' else .65))
        if mt in ('hybrid_ic','ic_adaptive'):
            blend=st.slider('走期IC調整幅度',0.0,0.8,float(blend),0.05,help='只使用當時已成熟的歷史結果；不使用當期或未來報酬。')
        eligible=st.checkbox('可參與模型勝負選擇',value=bool(cand.get('selection_eligible',True)),key='v223_eligible')
        if st.button('套用上述權重到本次策略JSON',disabled=busy):
            try:
                q={}
                for _,r in edited.iterrows():
                    factor=str(r['factor']).strip();w=float(r['weight'])
                    if factor and w>0:q[factor]=w
                if not 1<=len(q)<=4:raise ValueError('每個階段請使用1～4個正權重因子')
                z=sum(q.values());q={k:v/z for k,v in q.items()}
                cand['horizon_stage_weights'][str(h)][stage]=q;cand['model_type']=mt;cand['selection_eligible']=eligible
                if mt in ('hybrid_ic','ic_adaptive'):
                    a=dict(cand.get('adaptive') or {});a.update(blend=blend,lookback_cases=int(a.get('lookback_cases',36)),min_history_cases=int(a.get('min_history_cases',12)),stage_mix=float(a.get('stage_mix',.60)),prior_floor=float(a.get('prior_floor',.10)));cand['adaptive']=a
                st.session_state[key]=profiles;st.success('已套用。尚未執行回測。')
            except Exception as exc:st.error(str(exc))

    c1,c2=st.columns(2)
    if c1.button('載入V22.3預設策略組',disabled=busy,use_container_width=True):
        st.session_state[key]=copy.deepcopy(default_profiles);st.rerun()
    include_gbm=c2.checkbox('加入GBM研究挑戰者（較慢，不可自動勝出）',value=False,help='沿用Claude版GBM概念，但只用已成熟歷史資料；預設selection_eligible=false。')

    with st.expander('進階：完整策略JSON',expanded=False):
        profile_text=st.text_area('策略JSON',json.dumps(st.session_state[key],ensure_ascii=False,indent=2),height=480,key='v223_raw')
        if st.button('從JSON覆蓋快速編輯器',disabled=busy):
            try:st.session_state[key]=_schema3(json.loads(profile_text));st.success('JSON已載入');st.rerun()
            except Exception as exc:st.error(str(exc))
        setting_text=st.text_area('測試設定',json.dumps(settings,ensure_ascii=False,indent=2),height=240)

    run_profiles=copy.deepcopy(st.session_state[key])
    if include_gbm:
        opt=read_json(HERE/'v223_optional_profiles.json')
        have={c['name'] for c in run_profiles['candidates']}
        run_profiles['candidates'] += [c for c in opt.get('candidates',[]) if c.get('name') not in have]

    cols=st.columns(2)
    if cols[0].button('▶ 快速驗證（不看最後保留期）',disabled=busy,use_container_width=True,type='primary'):
        try:start_v22(root,run_profiles,settings,'fast');st.success('V22.3快速測試已啟動。')
        except Exception as exc:st.error(str(exc))
    with cols[1].popover('凍結後最終確認'):
        st.warning('同一保留期反覆重開會失去盲測意義。')
        ok=st.checkbox('我已凍結母池、模型型態、因子與權重')
        if st.button('執行一次凍結確認',disabled=busy or not ok):
            try:start_v22(root,run_profiles,settings,'confirm');st.success('V22.3確認測試已啟動。')
            except Exception as exc:st.error(str(exc))

    @st.fragment(run_every='3s')
    def monitor():
        err=read_json(root/'v22'/'launch_error.json')
        if err:st.error(err.get('type','')+': '+err.get('message',''))
        latest=read_json(root/'v22'/'latest.json')
        if not latest.get('run'):return
        run=Path(latest['run']);state=read_json(run/'state.json')
        if state:st.caption('狀態：'+str(state.get('status'))+'｜'+str(state.get('phase')))
        result=read_json(run/'results.json')
        if result:
            st.subheader('④ 最新測試結果')
            for h,m in result['models'].items():
                st.write(f"**{h}日｜{m['pool']}｜{m['choice']['name']}｜{m['choice'].get('model_type','manual')}｜{m['verdict']}**")
                if m.get('stage_performance'):st.dataframe(m['stage_performance'],use_container_width=True)
            if (run/'REPORT.txt').is_file():
                with st.expander('直接閱讀測試報告'):st.text((run/'REPORT.txt').read_text(encoding='utf-8-sig'))
            if (run/'V22_TEST_REPORT.zip').is_file():st.download_button('下載V22.3完整測試報告ZIP',(run/'V22_TEST_REPORT.zip').read_bytes(),'V22_TEST_REPORT.zip','application/zip',on_click='ignore')
            if (run/'V22_TEST_REPORT.xlsx').is_file():st.download_button('下載V22.3 Excel測試報告',(run/'V22_TEST_REPORT.xlsx').read_bytes(),'V22_TEST_REPORT.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',on_click='ignore')
            for fn,mime in [('candidate_ranking.csv','text/csv'),('strategy_by_stage.csv','text/csv'),('factor_ic_summary.csv','text/csv'),('adaptive_weight_path.csv','text/csv'),('static_weight_suggestions.csv','text/csv'),('factor_sensitivity.csv','text/csv'),('market_stage.csv','text/csv')]:
                if (run/fn).is_file():st.download_button('下載 '+fn,(run/fn).read_bytes(),fn,mime,on_click='ignore',key='v223'+fn)
    monitor()
