# Chan Volume Fusion Strategy Design

Date: 2026-06-19

## Decision

Implement option 2 as a new built-in strategy: `ChanVolumeFusionStrategy`.

The strategy is not a generic portfolio vote. It is a master-helper strategy:

- `ChanStructureStrategy` remains the master structure engine.
- `VolumeConfirmedMomentumStrategy` semantics become helper evidence.
- Helper evidence cannot open a position by itself.
- Chan sell/exit structure keeps final priority when it conflicts with volume momentum.

This keeps the existing `PortfolioStrategy` useful for flat multi-strategy voting while adding a dedicated strategy for "缠论为主，量价为辅".

## Problem

The current flat portfolio approach can combine Chan and volume momentum, but its `weighted_vote` mode is closer to OR logic. If either strategy emits a signal, it can influence trading. That improves participation but does not guarantee higher confidence. It also increases trade count and can amplify drawdown.

Recent evidence:

- Fixed six-stock small grid: Chan + volume weighted mix improved average return versus either alone, but increased drawdown versus both.
- STAR Top-20 sample: Chan + volume weighted mix improved average return materially, but trade count and average drawdown rose.
- Chan-only STAR Top-20 evidence showed the current Chan strategy participates in rallies but is often too defensive in strong STAR Market trends.

The next iteration should test whether volume momentum can improve Chan structure decisions without turning the system into a loose signal union.

## Goals

- Add a backtestable built-in `ChanVolumeFusionStrategy`.
- Preserve the existing `Strategy` interface and registry/API/frontend strategy discovery path.
- Use Chan signals as the only source of entry/exit intent.
- Use volume momentum as a helper for:
  - allowing or blocking low-confidence Chan entries,
  - increasing target units for high-confidence Chan entries,
  - extending holding time during strong volume-confirmed uptrends,
  - reducing or accelerating exits when volume momentum weakens.
- Keep defaults conservative enough to compare against current `ChanStructureStrategy`.
- Record fixed six-stock benchmark results and STAR Top-20 exploratory results.

## Non-Goals

- Do not replace `PortfolioStrategy`.
- Do not add live trading behavior.
- Do not add multi-symbol portfolio holdings.
- Do not implement a generic factor framework yet.
- Do not optimize parameters exhaustively in the first implementation.
- Do not require new frontend surfaces; the strategy should appear through existing strategy discovery and parameter controls.

## Strategy Behavior

### Inputs

`ChanVolumeFusionStrategy` accepts the current symbol plus a subset of Chan and volume parameters.

Primary Chan defaults should mirror the current Chan strategy unless explicitly overridden:

- `min_signal_score=28.0`
- `signal_mode="all"`
- `allowed_point_types="all"`
- `allowed_levels="all"`
- `max_holding_bars=15`
- `watch_confirm_bars=20`
- `low_confidence_gate="divergence_or_trend"`
- `position_cap_mode="risk"`
- `risk_drawdown_cap_pct=8.0`
- `trade_size=100`

Volume helper defaults should mirror the current volume momentum strategy:

- `momentum_window=20`
- `min_momentum_pct=0.08`
- `volume_window=20`
- `volume_multiplier=1.5`
- `trend_window=60`

Fusion-specific defaults:

- `low_confidence_requires_volume=True`
- `high_confidence_volume_boost=True`
- `volume_boost_units=1`
- `strong_volume_extend_bars=10`
- `weak_volume_exit_mode="reduce"`
- `weak_volume_momentum_pct=0.0`
- `max_units=3`

### Volume State

Each bar derives a lightweight helper state:

- `strong`: price momentum >= `min_momentum_pct`, volume ratio >= `volume_multiplier`, and close above trend average.
- `neutral`: not strong and not weak.
- `weak`: momentum <= `weak_volume_momentum_pct` or close below trend average.

The helper state is internal evidence. It should also be reflected in signal reasons so attribution can distinguish volume-confirmed and volume-weakened Chan decisions.

### Entry Rules

Chan remains the master trigger.

- T1 divergence watch signals should keep existing watch/confirmation behavior.
- T2 second-buy entries are low confidence. They are allowed only when:
  - existing Chan low-confidence gate allows them, and
  - either volume state is `strong`, or `low_confidence_requires_volume=False`.
- T3 third-buy entries are high confidence. They can enter without volume confirmation, but strong volume adds `volume_boost_units` up to `max_units`.
- Divergence confirmation buys target middle/high units as Chan currently defines. Strong volume can boost one additional unit up to `max_units`.
- Volume-only buy signals do not create orders.

### Exit Rules

Chan structure exits have priority.

- Chan second-sell, third-sell, top divergence confirmation, and opposite confirmation exits should pass through even if volume remains strong.
- If volume state becomes `weak` while holding:
  - `weak_volume_exit_mode="reduce"` lowers target units by one, but does not force a full exit unless target reaches zero.
  - `weak_volume_exit_mode="exit"` exits to zero.
  - `weak_volume_exit_mode="ignore"` leaves Chan exits in full control.
- Time exits are extended by `strong_volume_extend_bars` while volume state is strong and Chan context is not bearish.

### Position Sizing

The strategy should reuse the current Chan target-unit mental model:

- low confidence: small unit
- divergence confirmation: middle unit
- high confidence T3: high unit

Fusion adds or subtracts units from Chan target units rather than producing separate volume orders.

The emitted order volume remains a delta from current target units:

```text
delta_shares = (target_units - current_units) * trade_size
```

## Architecture

### Preferred Implementation Shape

Add `ChanVolumeFusionStrategy` in `src/ai_trade_system/strategies/popular.py`.

To keep the first implementation scoped:

- Reuse `ChanStructureStrategy` and `VolumeConfirmedMomentumStrategy` concepts.
- Avoid changing the public `Strategy` interface.
- Avoid changing `PortfolioStrategy`.
- Keep helper calculations local to the new strategy unless duplication becomes substantial.

If direct reuse of `ChanStructureStrategy.on_bar` hides too much reason metadata, add small protected helper methods to Chan only when they serve both strategies clearly. Otherwise, duplicate the minimal control logic in the new strategy and keep tests tight.

### Registry And Metadata

Register the new strategy as built-in:

- Display name: `缠论量价融合`
- Description: `以缠论结构信号为主，使用量价动量确认低确定性买点、增强高确定性买点并调节持仓节奏。`

Expose Chinese parameter guidance for the new fusion parameters. Enum-like parameters should use existing parameter option metadata:

- `weak_volume_exit_mode`: `reduce`, `exit`, `ignore`
- boolean parameters can stay bool inputs unless the existing UI requires another shape.

### Attribution

Signal reasons must encode both Chan point family and volume helper outcome:

- `CHAN_VOLUME_T2_BUY_VOLUME_CONFIRMED`
- `CHAN_VOLUME_T2_BUY_VOLUME_BLOCKED` should not emit an order but can be useful in internal tests.
- `CHAN_VOLUME_T3_BUY_VOLUME_BOOST`
- `CHAN_VOLUME_CONFIRM_BUY_VOLUME_BOOST`
- `CHAN_VOLUME_WEAK_REDUCE`
- `CHAN_VOLUME_WEAK_EXIT`
- `CHAN_VOLUME_TIME_EXIT_EXTENDED`
- `CHAN_VOLUME_CHAN_SELL`

Existing `classify_signal_family` can initially classify these as Chan families by preserving `_T2`, `_T3`, `CONFIRM`, and `TIME_EXIT` tokens where possible. If needed, extend it only enough for meaningful QA labels.

## Testing

Unit tests:

- Strategy discovery includes `ChanVolumeFusionStrategy` with Chinese metadata and parameter guidance.
- Low-confidence T2 buy is blocked when volume state is not strong and `low_confidence_requires_volume=True`.
- Low-confidence T2 buy passes when volume state is strong.
- T3 buy can pass without volume confirmation.
- T3 buy target units increase when volume state is strong.
- Weak volume reduces or exits according to `weak_volume_exit_mode`.
- Strong volume extends time exit by `strong_volume_extend_bars`.
- Chan sell exits override strong volume.

Route/API tests:

- `/api/strategies` exposes the new strategy.
- `/api/backtest` can run the new strategy on demo/local bars and returns metrics/trades without schema changes.

Benchmark tests and QA:

- Run fixed six-stock benchmark:
  - `688981/SSE`
  - `000858/SZSE`
  - `601318/SSE`
  - `600901/SSE`
  - `600989/SSE`
  - `603986/SSE`
- Use local qfq fixtures under `data/market/a_share/{exchange}/{code}/`.
- Use effective available date range `2023-06-19` to `2026-06-18` unless fixture refresh changes that.
- Record comparable metrics under `docs/qa/`.
- Also run STAR Top-20 exploratory benchmark if the persisted STAR sample exists locally.

Verification commands:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_api_routes.py -q
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

Browser QA is only required if the implementation changes frontend rendering. If only registry metadata changes and existing strategy controls render it automatically, a screenshot is useful but not required for the strategy-core acceptance.

## Expected Outcome

The first implementation should answer two questions:

1. Does using volume as helper evidence improve Chan's absolute return profile versus current Chan defaults?
2. Does the improvement come with acceptable drawdown and turnover, especially on STAR Market high-beta names?

Success is not defined as beating buy-and-hold in the first pass. The first pass is successful if it produces a reproducible strategy, fixed benchmark evidence, STAR exploratory evidence, and clear next tuning targets.

## Risks

- Chan analysis is currently expensive in grid runs because the incremental analyzer still re-scans windows. Benchmarks should stay bounded until caching is improved.
- Duplicating Chan control logic may drift from `ChanStructureStrategy`; tests should pin key behavior.
- Volume confirmation can overfit to recent high-beta conditions. Fixed six-stock and STAR samples should both be reported.
- More active position resizing may increase trade count and commission drag.
