# Chan Dynamic Position Cap Design

Date: 2026-06-19

## Goal

Implement C for `ChanStructureStrategy`: dynamic position caps and risk-budget controls that prevent high-certainty Chan signals from always expanding to the maximum position when the trend context or current open risk is unfavorable.

## Context

Current Chan strategy behavior after A and B:

- A maps signals to target units: T2 low confidence, T1/confirmation middle confidence, T3 high confidence.
- B gates ordinary T2 signals with high-score override and Chan Core V2 trend compatibility.
- T3 and armed T1 confirmations intentionally bypass the low-confidence T2 gate.

That still leaves a gap: a T3 buy can target `high_confidence_units` even in hostile or range-like contexts, and the strategy does not stop adding when the existing position is already in meaningful floating loss.

## Selected Approach

Add a buy-side target-unit cap after the existing A/B target-unit decision, before `_can_emit_target_units(...)`.

The cap applies only to buy targets:

- Sell and reduction targets are never blocked by the dynamic cap.
- If no Chan Core V2 trend context is available, preserve the current target units.
- If `position_cap_mode` is `off`, preserve current A/B behavior.

New parameters:

- `position_cap_mode: str = "trend_risk"`
  - Allowed values: `off`, `trend`, `risk`, `trend_risk`.
- `trend_cap_units: int = 2`
  - Maximum buy target units when Chan Core V2 context is not clearly supportive.
- `risk_drawdown_cap_pct: float = 3.0`
  - If the current close/signal price is at least this percentage below the strategy average entry price, do not increase units.

Trend cap rules for buy signals:

- `up`: keep the requested target.
- `transition` or `range`: cap to `trend_cap_units`.
- `down`: cap to `low_confidence_units`.
- Unknown trend type or missing trend: keep the requested target.

Risk cap rules:

- Track `average_entry_price` inside `ChanStructureStrategy`.
- On buy deltas, update the weighted average entry by position units.
- On partial sells, keep the average entry for remaining units.
- On full exits and time exits, clear the average entry.
- When drawdown from average entry is greater than or equal to `risk_drawdown_cap_pct`, cap buy targets to current `position_units`, which prevents additional buys but does not force a sell.

## Non-Goals

- No broker/equity-level risk engine changes.
- No live trading behavior.
- No optimization sweep in this implementation step.
- No change to signal generation in `research.chan_core_v2`.

## Testing

Focused unit tests must cover:

- T3 buy in downtrend is capped to `low_confidence_units` by default.
- T3 buy in uptrend can still reach `high_confidence_units`.
- T3 buy in range/transition is capped to `trend_cap_units`.
- `position_cap_mode="off"` preserves full A/B target behavior.
- Floating drawdown cap prevents add-on buys while keeping existing units.
- Full exits clear `average_entry_price`.
- Invalid cap configuration raises `ValueError`.
- Registry metadata exposes Chinese parameter guidance and defaults.

Acceptance verification must include:

- Full Python test suite.
- Frontend tests and build because parameter metadata is visible in React.
- Fixed six-stock qfq benchmark over `20230619` to `20260619`.
- QA markdown result under `docs/qa/`.
- Browser screenshots proving the three new parameters render.
