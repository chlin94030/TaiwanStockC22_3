# V22.3 QA status

Release: `22.3-adaptive-hybrid-studio`

## Automated tests

- Full repository test suite: **198 passed, 0 failed**.
- New V22.3 tests cover:
  - schema-2 backward compatibility;
  - independent 5/20/60 horizon weights;
  - matured-history-only adaptive IC;
  - current/future outcome mutation cannot change date-T adaptive selection;
  - diagnostic candidates cannot become the automatic winner;
  - Excel workbook is included in the report ZIP.
- Python compileall: passed.

## Performance smoke test

Synthetic fixed-pool case set: 72 monthly cases × 300 stocks, 20-session horizon.

- manual first computation: ~0.009 s; cache replay ~0.001 s;
- hybrid_ic first computation: ~0.672 s; cache replay ~0.001 s;
- ic_adaptive first computation: ~0.671 s; cache replay ~0.001 s.

Optional GBM challenger smoke test completed successfully; one small synthetic walk-forward fit/evaluation was ~0.745 s in this container.

These are engineering timings in the current container, not Streamlit Cloud guarantees and not market-performance results.

## Deployment dependency note

V22.3 adds `openpyxl==3.1.5` for the workbook and `scikit-learn==1.9.1` for the optional GBM challenger. GBM is lazy-imported and not run unless explicitly included.

## Limits

- No real Streamlit Cloud deployment was performed from this environment.
- No new real-market profitability test was run for V22.3.
- Repeated fast-mode tuning consumes development evidence; it is not a fresh holdout.
