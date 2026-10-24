# Current QA — V22.3 Adaptive Hybrid Studio

- Full repository test suite: **198 passed, 0 failed**.
- Python compileall: passed.
- New coverage: horizon-specific weights, matured-history-only walk-forward IC, hybrid shrinkage, diagnostic-only GBM, Excel report export.
- No new real-market profitability claim; no Streamlit Cloud deployment performed from this environment.

See `V22_3_QA_STATUS.md` for details.

---

# V22.2 QA Status

- Full pytest suite: **192 passed / 0 failed**.
- Added regression for sparse Yahoo bulk data that initially contains only a few full histories.
- Added versioned Yahoo turnover cache so V22.1 sparse checkpoints are not reused.
- Added bounded small-batch repair before pool construction.
- Added AUTO_FAST -> OFFICIAL_BULK fallback; no automatic fallback to serial FinMind.
- Python compile check: passed for modified modules.

Limit: internet access is unavailable in the build container, so real Yahoo/TWSE/TPEx Cloud transport speed and provider availability were not end-to-end tested here.
