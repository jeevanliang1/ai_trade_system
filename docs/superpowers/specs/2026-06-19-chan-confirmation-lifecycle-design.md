# Chan Confirmation Lifecycle Design

## Goal

Extend `ChanStructureStrategy` so confirmation-style Chan signals can form explicit long-only entry and exit sequences, including optional time-based exits when no opposite confirmation appears.

## Background

The strategy now separates Chan signal families with `signal_mode`:

- `confirmation`: `*_DIVERGENCE` and `*_CONFIRM`
- `structure`: T2/T3 second/third buy-sell signals
- `all`: every Chan structure signal passing the score threshold

The fixed 中芯国际 and 五粮液 benchmark fixtures currently produce no confirmation-family signals at the strategy decision day, so `confirmation/30` produces zero trades. That is a data/analyzer outcome, not a lifecycle contract. The strategy still needs a clear lifecycle for fixtures or future stocks where bottom confirmations produce entries.

## Decision

Add `max_holding_bars: int = 0` to `ChanStructureStrategy`.

Behavior:

- `0` means disabled and preserves existing default behavior.
- A positive value enables a time exit after a position has been held for that many bars without an earlier opposite signal exit.
- Opposite signal behavior remains:
  - Buy-family confirmation signals enter when flat.
  - Sell-family confirmation signals exit when long.
- Time exits use the current bar close and emit reason `chan_structure:TIME_EXIT:max_holding_bars=<value>`.
- The parameter applies to `ChanStructureStrategy` generally, but this slice tests and documents it for confirmation-mode lifecycle work.

## Scope

This slice changes only the strategy wrapper, registry parameter metadata, tests, QA, and pending-feature handoff. It does not change Chan structure detection, divergence scoring, public data, backtest accounting, broker behavior, short selling, or live trading behavior.

## Acceptance Criteria

- `ChanStructureStrategy` exposes `max_holding_bars` with default `0`.
- Negative `max_holding_bars` raises `ValueError`.
- Confirmation-mode buy signals still create entries.
- Confirmation-mode sell signals still create opposite-signal exits.
- When `max_holding_bars` is positive, a long confirmation-mode position exits after that many held bars if no opposite signal exits first.
- Strategy registry inspection exposes the `max_holding_bars` default and Chinese guidance that `0` disables the time exit.
- Existing `all/30` default benchmark behavior remains unchanged.
- Fixed benchmark backtests are rerun on 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE`.
