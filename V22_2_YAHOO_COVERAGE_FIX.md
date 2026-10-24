# Alpha Radar V22.2 — Yahoo Coverage Repair

This release fixes a V22.1 false-success condition in the Yahoo fast bootstrap.

## What failed

V22.1 could finish all Yahoo application-level batches and then show a pool error such as:

`only 2 eligible turnover histories, cannot claim Top-500`

The problem was not the pool rule. A non-empty yfinance bulk DataFrame can still contain partial or sparse per-ticker history after timeouts/rate limiting. V22.1 cached those sparse columns and counted the bootstrap phase as complete before checking 252-session rankability.

## V22.2 behavior

1. Yahoo application chunks are reduced from 80 to 20 tickers.
2. The Yahoo turnover cache schema is bumped; V22.1 sparse checkpoints are not reused.
3. Before any Top-N pool is claimed, every monthly signal is audited for actual 252-session turnover history.
4. Sparse tickers are retried in 5-ticker repair batches, prioritising names with larger recent turnover proxy.
5. Repair is bounded. It cannot silently become another multi-hour retry loop.
6. In `AUTO_FAST`, if Yahoo history is still insufficient, the job automatically switches to resumable `OFFICIAL_BULK` (TWSE + TPEx whole-market-by-date data).
7. It never falls back to the 7+ hour serial FinMind per-stock path unless the user explicitly selects `FINMIND`.

## Existing data

Do not delete `data/`. SQLite, finished strategy caches and official bulk checkpoints remain reusable. Only the old Yahoo turnover-batch cache is bypassed by the new schema directory.

## Important limitation

Yahoo turnover is still a development proxy based on typical price × historical Yahoo volume. Formal/exact pool confirmation should use FinLab actual traded value, official TWSE/TPEx bulk history, or another audited actual-amount source.
