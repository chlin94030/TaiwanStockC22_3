# V22.3 Claude Fusion design

## What was adopted

From the supplied Claude engine/app we adopted the useful engineering patterns rather than its whole research protocol:

- pluggable model comparison under identical data/cost conditions;
- separate 5/20/60-session weights instead of one weight vector for all horizons;
- walk-forward rank-IC adaptation based only on matured historical labels;
- a hybrid model that shrinks IC weights toward the Kostolany/book prior;
- an optional HistGradientBoosting challenger for research comparison only;
- a compact Excel workbook in addition to the auditable ZIP/CSV/JSON report;
- direct factor/model comparison that makes iteration easier.

## What was deliberately not copied

- no whole-period/latest-period universe cut before historical backtests;
- no silent current-roster result presented as survivor-bias-free;
- no single heat score replacing the A1/A2/A3/B1/B2/B3 gate;
- no random 3,000-vector search that then treats the best training vector as discovered truth;
- no missing factor silently treated as a valid neutral observation for funded eligibility;
- no automatic use of GBM as the winner merely because it fits development data better.

## V22.3 model types

`manual`: frozen horizon/stage priors.

`hybrid_ic`: 65% book prior + up to 35% matured walk-forward IC by default. The prior floor prevents the adaptive layer from silently becoming an unrelated strategy.

`ic_adaptive`: stronger adaptation (default 65%) but still shrunk to the book prior and charged a larger model-complexity penalty during development ranking.

`gbm_challenger`: optional walk-forward HistGradientBoosting model. It trains only on prior matured labels, predicts cross-sectional rank, and is `selection_eligible=false` by default.

## Chronology

At a signal date T, adaptive history consists only of prior cases with `exit < T`. Current/future outcomes cannot change the date-T weights or picks. During a final confirmation, the algorithm itself is frozen; an adaptive model may continue its predeclared online learning from earlier confirmation cases only after those cases have matured, mirroring a live online learner rather than a static vector.

## Reports

`V22_TEST_REPORT.zip` now includes:

- `V22_TEST_REPORT.xlsx`
- `candidate_ranking.csv`
- `strategy_by_stage.csv`
- `factor_ic_summary.csv`
- `adaptive_weight_path.csv`
- `adaptive_ic_walkforward.csv`
- `static_weight_suggestions.csv`
- `factor_sensitivity.csv`
- `monthly_decisions.csv`
- stage/data-quality files and JSON/TXT/Markdown summaries.

`static_weight_suggestions.csv` is a next-iteration suggestion only; it is never auto-activated in the same run.
