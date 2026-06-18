# Chan watch divergence arming design

Date: 2026-06-19

## Goal

Let `ChanStructureStrategy` remember watchable T1 bottom/top divergence signals for a bounded number of bars and convert them into trades when later repair or pivot-retest structure confirms the same direction.

## Context

`research.chan_structure` now emits unconfirmed T1 divergence signals with a `watch` tag. The strategy currently filters and consumes only same-bar candidates. That means a useful T1 divergence watch can disappear before a later T2/T3 repair signal arrives. This slice adds strategy-local arming state so the watch signal can influence a later entry or exit without changing the research analyzer payload.

## Behavioral Contract

1. `ChanStructureStrategy` accepts `watch_confirm_bars: int = 20`.
2. `watch_confirm_bars=0` disables arming. Negative values raise `ValueError`.
3. A current-bar `CHAN_STRUCT_BUY_T1_DIVERGENCE` or `CHAN_STRUCT_SELL_T1_DIVERGENCE` carrying tag `watch` arms the strategy for that action.
4. The arming record stores action, kind, score, price, reason, trading day, and bar index.
5. An armed `buy` can be confirmed by a later same-direction `CHAN_STRUCT_BUY_CONFIRM`, `CHAN_STRUCT_BUY_T2`, or `CHAN_STRUCT_BUY_T3`.
6. An armed `sell` can be confirmed by a later same-direction `CHAN_STRUCT_SELL_CONFIRM`, `CHAN_STRUCT_SELL_T2`, or `CHAN_STRUCT_SELL_T3`.
7. Confirmation emits a normal `Signal` with reason prefix `chan_structure:ARMED_CONFIRM:<watch_kind>-><confirm_kind>`.
8. The arming record expires after more than `watch_confirm_bars` bars or when an opposite watch is armed.
9. Same-bar direct confirmation behavior remains unchanged.

## Verification

- Add pytest coverage for buy arming then T2/T3 confirmation, sell arming then T2/T3 confirmation, expiry, disabled arming, and negative parameter validation.
- Run fixed 中芯国际 and 五粮液 benchmarks for default all, confirmation lifecycle, armed confirmation lifecycle, and structure lifecycle configs.
- Browser-check Strategy Workshop still renders the new parameter guidance.
