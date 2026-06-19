# Chan Signal Attribution Design

Date: 2026-06-19

## Goal

Add Chan strategy signal attribution so backtests can compare PnL, trade count, win rate, and realized drawdown contribution by T1/T2/T3/divergence/time-exit family.

## Scope

This change adds attribution and reporting only. It must not change strategy signal generation, order sizing, broker execution, equity calculation, or the existing six-stock benchmark returns.

The first implementation targets the shared backtest path used by the FastAPI and React workbench. It is useful for Chan strategies, but it classifies non-Chan strategy signals as `other` so the backtest API remains generic.

## Attribution Model

Each accepted backtest trade gets a parallel attribution record:

- executed trade fields: trading day, side, symbol, price, volume, commission
- signal reason: the originating `Signal.reason`
- signal family: normalized family id
- signal label: Chinese display label

Families:

| Family | Label | Detection |
| --- | --- | --- |
| `t1_divergence` | T1背驰 | `T1_DIVERGENCE` in signal reason |
| `t2` | T2二买二卖 | `_T2` or second-buy/second-sell reason |
| `t3` | T3三买三卖 | `_T3` or third-buy/third-sell reason |
| `divergence_confirm` | 背驰确认 | `BUY_CONFIRM`, `SELL_CONFIRM`, or `ARMED_CONFIRM` reason |
| `time_exit` | 时间退出 | `TIME_EXIT` or `time_exit` reason |
| `other` | 其他信号 | fallback |

Summary rows are grouped by family and include two realized-performance perspectives:

- Entry perspective: closed-lot PnL, win rate, profit factor, and realized drawdown attributed to the buy signal family.
- Exit perspective: the same closed-lot metrics attributed to the sell signal family.

This gives T2/T3 buy quality and time-exit sell quality without forcing a single ambiguous interpretation.

## Backend Design

Add backtest data structures in `src/ai_trade_system/backtest.py`:

- `TradeAttribution`: one accepted trade plus source signal family fields.
- `BacktestResult.trade_attributions`: a parallel list built only for accepted broker orders.

Add analytics helpers in `src/ai_trade_system/analytics.py`:

- `classify_signal_family(reason: str) -> tuple[str, str]`
- `calculate_signal_attribution(trade_attributions, initial_cash) -> list[SignalAttributionRow]`

The attribution calculator uses FIFO matching, consistent with existing trade outcome logic. Partial exits split lots proportionally. Closed-lot PnL subtracts both entry and exit commissions proportionally.

Realized drawdown is calculated from each family's cumulative realized PnL curve divided by initial cash. This is intentionally a realized contribution metric, not a causal mark-to-market attribution engine.

## API And Frontend Design

`run_backtest_request` adds:

- `trade_attributions`: detailed attributed trades
- `signal_attribution`: grouped rows for UI and QA

React `BacktestResponse` adds corresponding types. `BacktestResultPanel` renders a compact `信号归因` table before `交易明细`.

No new user controls are required. Attribution appears automatically after any backtest result.

## Tests

Backend tests must prove:

- `run_backtest` records source reason/family only for accepted trades.
- `classify_signal_family` covers Chan T1/T2/T3/confirmation/time-exit families.
- `calculate_signal_attribution` returns entry and exit PnL, win rate, and realized drawdown for FIFO closed lots.
- `/api/backtest` returns `trade_attributions` and `signal_attribution`.

Frontend tests must prove:

- `BacktestResultPanel` renders the `信号归因` table.
- The table shows family label, trade count, entry PnL, and exit PnL.

## Verification

Final delivery must run:

- `PYTHONPATH=src python -m pytest`
- `cd frontend && npm test -- --run`
- `cd frontend && npm run build`
- fixed six-stock ChanStructureStrategy benchmark using persisted qfq fixtures
- browser validation for the React backtest surface
- `git diff --check`

## Out Of Scope

- Optimizing Chan parameters.
- Changing Chan signal generation or broker execution.
- Causal intraday/mark-to-market attribution.
- Portfolio-level allocation attribution.
