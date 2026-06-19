# Chan Structure Position Sizing Design

## Goal

Revise `ChanStructureStrategy` so Chan buy/sell point certainty controls target position size instead of treating every valid signal as a full binary entry or exit.

## Approved Scope

- Implement option A from the strategy discussion.
- Treat 二买/二卖 as low-certainty signals.
- Treat 三买/三卖 as high-certainty signals.
- Use bottom/top divergence confirmation to increase certainty between low and high.
- Keep the strategy long-only and compatible with the current single-symbol backtest engine.
- Keep later B/C strategy ideas out of this change.

## Trading Semantics

One unit equals `trade_size` shares. The default maximum position is 3 units.

Buy-side targets:

- 二买 (`CHAN_STRUCT_BUY_T2`) targets `low_confidence_units`, default 1 unit.
- Bottom divergence confirmation (`CHAN_STRUCT_BUY_CONFIRM`) and armed bottom divergence confirmation target `divergence_confirm_units`, default 2 units.
- 三买 (`CHAN_STRUCT_BUY_T3`) targets `high_confidence_units`, default 3 units.

Sell-side targets:

- 二卖 (`CHAN_STRUCT_SELL_T2`) reduces by `low_confidence_units`, default 1 unit.
- Top divergence confirmation (`CHAN_STRUCT_SELL_CONFIRM`) and armed top divergence confirmation reduce to `sell_confirm_units`, default 1 unit.
- 三卖 (`CHAN_STRUCT_SELL_T3`) clears the whole position.
- `max_holding_bars` clears the whole position when enabled.

The strategy emits only the delta needed to move from current units to the target. If the target is equal to the current units, no signal is emitted.

## Parameters

Add constructor parameters to `ChanStructureStrategy`:

- `low_confidence_units: int = 1`
- `divergence_confirm_units: int = 2`
- `high_confidence_units: int = 3`
- `sell_confirm_units: int = 1`

Validation:

- `low_confidence_units` must be at least 1.
- `divergence_confirm_units` must be at least `low_confidence_units`.
- `high_confidence_units` must be at least `divergence_confirm_units`.
- `sell_confirm_units` must be non-negative and less than `high_confidence_units`.

The default `allowed_point_types` changes to `all` so 二买/二卖、三买/三卖 and divergence point types can participate in the default strategy.

## State And Compatibility

Replace the internal binary position model with integer `position_units`.

Keep `in_position` as a compatibility property:

- Reading `in_position` returns whether `position_units > 0`.
- Setting `in_position = True` sets `position_units = low_confidence_units`.
- Setting `in_position = False` clears `position_units`.

This preserves existing tests and callers that still use the old boolean field while letting the strategy manage partial add/reduce behavior.

## Filtering And Watch State

Existing signal score, mode, point-type, and level filters still apply before a trade is emitted.

Raw T1 divergence watch signals still arm only; they do not trade immediately. When an armed watch is later confirmed by an allowed same-direction T2/T3/confirmation signal:

- Buy confirmation uses the divergence-confirm target.
- Sell confirmation uses the sell-confirm target.
- The reason keeps the existing `ARMED_CONFIRM:<watch_kind>-><confirm_kind>` prefix.

## Fixed Benchmark Universe

Strategy changes must now run the fixed qfq benchmark over six local A-share fixtures:

- 中芯国际 `688981/SSE`
- 五粮液 `000858/SZSE`
- 中国平安 `601318/SSE`
- 江苏金租 `600901/SSE`
- 宝丰能源 `600989/SSE`
- 兆易创新 `603986/SSE`

The new four fixtures must be persisted under `data/market/a_share/{exchange}/{code}/` using the existing data manager layout before the benchmark is recorded.

## Tests

Add focused tests for:

- 二买 from flat opens exactly one unit.
- 三买 after a low-certainty unit adds up to the high-certainty target.
- Bottom divergence confirmation targets two units.
- 二卖 reduces one unit.
- Top divergence confirmation reduces to the sell-confirm target.
- 三卖 clears all units.
- `in_position` boolean setter remains compatible.
- Invalid unit configurations raise `ValueError`.
- Strategy parameter metadata exposes Chinese labels and tuning guidance for the new unit parameters.

Existing Chan Core V2 incremental analyzer tests should remain valid.

## Backtest Acceptance

Before final delivery:

- Run the Python test suite with `PYTHONPATH=src python -m pytest`.
- Run the fixed six-stock benchmark for `ChanStructureStrategy` over the persisted qfq fixtures.
- Record comparable results in `docs/qa/` with fixture metadata and interpretation.
- Update `docs/rules/strategy-benchmark-backtest.md` for the expanded fixed universe.
- Capture the React strategy surface after parameter metadata changes, or document a concrete blocker.

