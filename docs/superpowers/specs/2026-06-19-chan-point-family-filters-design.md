# Chan Point-Family Filters Design

## Goal

Add metadata-backed filters to `ChanStructureStrategy` so the same Chan analyzer output can be backtested as first/second/third buy-sell point families and segment/stroke/fractal levels without changing analyzer output.

## Context

`research.chan_structure` now emits structured `ResearchSignal.metadata` for Chan hierarchy:

- `point_type`: `first-buy`, `first-sell`, `second-buy`, `second-sell`, `third-buy`, or `third-sell`
- `level`: `segment`, `stroke`, or `fractal`
- lineage and pivot relationship fields for diagnostics

`ChanStructureStrategy` already supports `signal_mode`, score thresholds, optional max-holding exits, and bounded T1 divergence watch arming. The remaining strategy-consumption gap is that every allowed signal family is still traded as one blended stream, so benchmark comparisons cannot isolate point types or structure levels.

## Behavioral Contract

1. `ChanStructureStrategy` accepts two new string constructor parameters:
   - `allowed_point_types: str = "all"`
   - `allowed_levels: str = "all"`
2. Each filter accepts either `all` or a comma-separated list of exact tokens.
3. Valid point-type tokens are:
   - `first-buy`
   - `first-sell`
   - `second-buy`
   - `second-sell`
   - `third-buy`
   - `third-sell`
4. Valid level tokens are:
   - `segment`
   - `stroke`
   - `fractal`
5. When a filter is not `all`, a tradable research signal must carry matching metadata. Signals missing the relevant metadata are excluded.
6. Direct tradable candidates and armed-watch confirmation candidates both respect the filters.
7. T1 divergence watch signals remain setup-only. Arming a watch signal should not be blocked by the point/level filters, because a filtered second-buy or third-buy can still validly consume a prior first-buy watch setup.
8. Existing defaults preserve current behavior: `allowed_point_types="all"` and `allowed_levels="all"` admit the same signals as before this change.
9. Unknown tokens fail fast with `ValueError` messages that name the invalid parameter.
10. Strategy registry parameter guidance describes the accepted tokens in Chinese so the React parameter form can expose the controls as plain text until enum controls are implemented.

## Non-Goals

- Do not change `research.chan_structure` signal generation.
- Do not tune strategy thresholds in this slice.
- Do not add frontend select controls yet; that remains the next pending item for enum-like strategy parameters.
- Do not add live trading behavior.

## Verification

- TDD tests first fail because `ChanStructureStrategy` does not yet accept or apply `allowed_point_types` and `allowed_levels`.
- Python tests cover:
  - direct point-type filtering;
  - direct level filtering;
  - armed-watch confirmation filtering;
  - unknown point-type and level validation;
  - registry metadata defaults and Chinese guidance.
- Fixed benchmark backtests must run on:
  - 中芯国际 `688981/SSE`: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
  - 五粮液 `000858/SZSE`: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- QA evidence is recorded under `docs/qa/`.
- Full close-out verification:
  - `PYTHONPATH=src python -m pytest`
  - `cd frontend && npm test -- --run`
  - `cd frontend && npm run build`
  - `git diff --check`
  - React browser QA screenshot from `./scripts/run_app.sh`
