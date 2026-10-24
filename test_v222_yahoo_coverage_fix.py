import numpy as np
import pandas as pd
from pathlib import Path

from lab_config import Config, VERSION
from lab_yahoo_bulk import YahooFastBulk, CACHE_SCHEMA


def mixed_frame(tickers, periods=340, full_tickers=()):
    idx=pd.bdate_range('2024-01-01', periods=periods)
    data={}
    for j,t in enumerate(tickers):
        base=np.linspace(40+j,60+j,periods)
        full=t in set(full_tickers)
        mask=np.ones(periods,dtype=bool) if full else np.arange(periods)>=periods-40
        fields={
            'Open':base-.2,'High':base+.8,'Low':base-.8,'Close':base,
            'Adj Close':base*.99,'Volume':np.full(periods,1_000_000+j*1000.,dtype=float)
        }
        for k,v in fields.items():
            a=np.asarray(v,dtype=float).copy();a[~mask]=np.nan;data[(t,k)]=a
    return pd.DataFrame(data,index=idx)


def test_version_bumped_and_cache_schema_changed():
    assert VERSION.startswith('22.2')
    assert CACHE_SCHEMA >= 2


def test_sparse_bulk_is_repaired_before_pool_claim(tmp_path):
    cfg=Config(start='2024-01-01',end='2025-04-18',pools=(2,3,4,5),top_k=2,
               recent_amount_floor=1.0,active_ratio60=.90,history_provider='YAHOO_FAST',
               min_train_months=12,holdout_months=6,min_outer_folds=1).resolved()
    tickers=[f'{1101+i}.TW' for i in range(8)]
    cat=[{'ticker':t} for t in tickers]
    idx=pd.bdate_range('2024-01-01',periods=340)
    b=YahooFastBulk(cfg,lambda **kw:None,lambda:None,chunk_size=4,repair_chunk_size=2,batch_pause=0)
    b._calendar_cache=[x.strftime('%Y-%m-%d') for x in idx]
    calls=[]
    def fake_download(ts,threads=None):
        ts=list(ts);calls.append(tuple(ts))
        # Initial 4-name batches mimic a partially rate-limited Yahoo response:
        # only two symbols have full history.  Repair batches (<=2) are complete.
        if len(ts)>2:
            return mixed_frame(ts,full_tickers={tickers[0],tickers[1]})
        return mixed_frame(ts,full_tickers=set(ts))
    b._download=fake_download
    signals=pd.DatetimeIndex([idx[-1]])
    out,meta=b.turnover(signals,cat,tmp_path)
    assert int(out[out.date==signals[0]].eligible.sum()) >= 5
    assert meta['min_eligible_at_signal'] >= 5
    assert meta['repair_replaced_histories'] >= 3
    assert any(len(x)<=2 for x in calls), 'repair must use smaller batches'


def test_sparse_cache_path_is_versioned(tmp_path):
    cfg=Config(start='2024-01-01',end='2025-04-18',pools=(2,3,4,5),top_k=2,
               recent_amount_floor=1.0,active_ratio60=.90,history_provider='YAHOO_FAST',
               min_train_months=12,holdout_months=6,min_outer_folds=1).resolved()
    tickers=[f'{1201+i}.TW' for i in range(6)]
    cat=[{'ticker':t} for t in tickers]
    idx=pd.bdate_range('2024-01-01',periods=340)
    b=YahooFastBulk(cfg,lambda **kw:None,lambda:None,chunk_size=3,repair_chunk_size=2,batch_pause=0)
    b._calendar_cache=[x.strftime('%Y-%m-%d') for x in idx]
    b._download=lambda ts,threads=None:mixed_frame(list(ts),full_tickers=set(ts))
    b.turnover(pd.DatetimeIndex([idx[-1]]),cat,tmp_path)
    assert (Path(tmp_path)/f'yahoo_fast_v{CACHE_SCHEMA}').is_dir()
    assert not (Path(tmp_path)/'yahoo_fast').exists()
