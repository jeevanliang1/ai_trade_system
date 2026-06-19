# Chan Offensive Fusion Combo Design

Date: 2026-06-19

## Decision

Implement the next Chan optimization as a two-layer change:

- Upgrade `ChanVolumeFusionStrategy` from a conservative master-helper strategy into an offensive Chan-led fusion strategy.
- Add or update a portfolio preset so the combination layer is also Chan-led, with volume momentum, MACD, and volatility breakout acting as trend-strength helpers instead of equal peers.

The goal is not lower risk alone. The goal is to improve both upside and downside versus the current `ChanVolumeFusionStrategy` benchmark.

## Problem

The current `ChanVolumeFusionStrategy` improved the fixed six-stock worst return and average drawdown, but it became too defensive:

- It reduced exposure too quickly when volume-price momentum weakened.
- It under-captured strong-trend names such as 兆易创新.
- The STAR supplemental sample remained positive on most names, but still lagged explosive buy-and-hold trends because the strategy cut exposure too early.

The user wants the combination result to lift both the upper bound and the lower bound. A purely conservative volume gate does not satisfy that. A purely aggressive parameter change may raise upside but can damage the lower bound. The next version needs regime-aware offense: add exposure when Chan structure and trend helpers agree, and avoid premature defensive exits while the broader trend remains intact.

## Goals

- Increase upside capture in strong-trend fixtures.
- Preserve or improve the fixed six-stock worst return compared with the current `ChanVolumeFusionStrategy`.
- Keep Chan as the primary signal engine; helper strategies and indicators may confirm or size, but they must not independently override Chan structure.
- Add a Chan-led offensive portfolio preset that expresses the same philosophy at the combination layer.
- Preserve existing `Strategy`, `PortfolioStrategy`, API, and frontend contracts unless a small additive field is required.
- Record fixed six-stock benchmarks and STAR supplemental benchmarks in `docs/qa/`.

## Non-Goals

- Do not add live trading behavior.
- Do not implement multi-symbol portfolio holdings.
- Do not replace all existing portfolio presets.
- Do not make volume momentum a standalone entry source inside the Chan fusion strategy.
- Do not tune exhaustively across a large grid in this slice.

## Strategy-Layer Design

### Current Behavior To Change

The current fusion strategy treats weak volume-price state as a direct position reducer when no Chan sell exists. This protects downside but can sell too early during strong trends that pause or consolidate.

### New Behavior

Add trend-continuation gating before weak-volume reductions.

Weak volume should reduce or exit only when at least one broader bearish condition is present:

- Chan Core V2 trend context is `down`, or a compatible bearish/transition state is present for the signal level.
- Price is below a configurable continuation trend average.
- Momentum weakness is severe enough to cross a stricter drawdown-style threshold.
- An explicit Chan sell signal appears; this remains highest priority and bypasses the weak-volume gate.

Strong volume should improve upside capture:

- High-confidence Chan buys can still receive volume boost units up to `max_units`.
- A new trend-continuation hold rule should suppress weak-volume reductions while price remains above the continuation trend average and Chan Core V2 is not bearish.
- Time exit should remain extendable under strong volume, but the extension should not block explicit Chan sell signals.

### Candidate Parameters

Add focused parameters to `ChanVolumeFusionStrategy`:

- `weak_volume_requires_trend_break=True`
  - When true, weak volume alone is insufficient to reduce; broader trend must also break.
- `continuation_trend_window=60`
  - Trend average used to decide whether a weak-volume pause is still acceptable.
- `severe_weak_momentum_pct=-0.06`
  - Severe short-term weakness can still reduce even before the trend average breaks.
- `offensive_high_confidence_units=3`
  - Default high-confidence target for the offensive version; this can be implemented by changing defaults or by preset overrides.
- `offensive_max_units=4`
  - Maximum target units when high-confidence Chan and strong helper evidence align.

The implementation should prefer backwards-compatible defaults where possible. If changing existing defaults would make historical comparisons unclear, use a new preset override and leave the raw strategy defaults conservative.

## Portfolio-Layer Design

### New Preset

Add a portfolio preset, tentatively:

- id: `chan_offensive_fusion_stack`
- name: `缠论进攻融合组合`
- mode: `weighted_vote`
- intent: Chan-led offensive confirmation, not flat voting.

Recommended allocations:

- `ChanVolumeFusionStrategy`, weight `1.4`, role `缠论量价主策略`
- `ChanStructureStrategy`, weight `0.6`, role `缠论结构基准`
- `VolumeConfirmedMomentumStrategy`, weight `0.8`, role `量价趋势确认`
- `MacdTrendStrategy`, weight `0.55`, role `趋势延续确认`
- `AtrVolatilityBreakoutStrategy`, weight `0.45`, role `波动突破确认`

Preset overrides for `ChanVolumeFusionStrategy` should be used to express offensive behavior first. This avoids globally making the standalone strategy aggressive before benchmarks justify it.

### Why Not Change PortfolioStrategy Yet

`PortfolioStrategy.weighted_vote` is simple and already exposed through API and frontend. For this slice, use weights and strategy parameters to express Chan leadership. If results still dilute Chan signals, the next slice can add a dedicated `leader_confirmed` portfolio mode where helper strategies only scale leader volume instead of voting independently.

## Testing

Use TDD.

Strategy tests:

- Weak volume does not reduce when `weak_volume_requires_trend_break=True` and price remains above the continuation trend average.
- Weak volume reduces when price breaks the continuation trend average.
- Severe weak momentum reduces even before the trend average break.
- Explicit Chan sell still exits even when continuation hold would otherwise suppress weak-volume reduction.
- Strong volume plus high-confidence Chan buy can reach the offensive max units when configured.

Portfolio preset tests:

- Bootstrap exposes `chan_offensive_fusion_stack`.
- The preset contains `ChanVolumeFusionStrategy` as the highest-weight allocation.
- The preset passes valid params for the current symbol.
- Existing presets remain available.

API/frontend tests:

- Existing `/api/bootstrap` portfolio preset contract remains unchanged.
- Portfolio Lab can apply the new preset through existing controls; no new UI surface is required unless existing tests reveal a missing type field.

## Benchmark Acceptance

Run benchmarks after implementation using persisted local qfq fixtures.

Fixed six-stock required set:

- `688981/SSE` 中芯国际
- `000858/SZSE` 五粮液
- `601318/SSE` 中国平安
- `600901/SSE` 江苏金租
- `600989/SSE` 宝丰能源
- `603986/SSE` 兆易创新

Primary comparison baseline:

- Current `ChanVolumeFusionStrategy` results recorded in `docs/qa/2026-06-19-chan-volume-fusion-benchmark.md`.

Success target:

- Average return improves versus current `ChanVolumeFusionStrategy`.
- Best return improves versus current `ChanVolumeFusionStrategy`.
- Worst return does not materially worsen; target is improvement.
- Average max drawdown should not worsen enough to erase the lower-bound improvement.

Supplemental check:

- Re-run the local STAR-market 20-stock sample if persisted fixtures are present.
- Record positive-count, average return, median return, average max drawdown, best, and worst results.

## Verification Commands

Expected implementation verification:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_api_routes.py tests/test_portfolio.py -q
PYTHONPATH=src python -m pytest
cd frontend && npm test
cd frontend && npm run build
```

Because this changes strategy logic and portfolio presets, final delivery must also include fixed-stock benchmark results under `docs/qa/`.

