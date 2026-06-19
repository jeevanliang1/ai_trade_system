# Strategy Benchmark Backtest Rule

Every modification to an existing strategy, or addition of a new strategy, must include fixed-stock benchmark backtest evidence before final delivery.

## Required Fixtures

Use the persisted local qfq daily-bar fixtures:

- 中芯国际 `688981/SSE`: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- 五粮液 `000858/SZSE`: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- 中国平安 `601318/SSE`: `data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv`
- 江苏金租 `600901/SSE`: `data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv`
- 宝丰能源 `600989/SSE`: `data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv`
- 兆易创新 `603986/SSE`: `data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv`

The comparison window is the fixed three-year range represented by these fixtures:

- Start: `2023-06-19`
- End: `2026-06-18`
- Original requested key range: `20230619` to `20260619`
- Adjustment: `qfq`

Do not replace this benchmark dataset during ordinary strategy work. If data must be refreshed or regenerated, state that explicitly and record the new fixture metadata before comparing results. The fixture CSV files are local data artifacts and may be ignored by git; the benchmark documentation must still record their path, row count, and date range.

## When This Applies

Run this rule for:

- New built-in strategies.
- New user strategy templates intended for delivery.
- Any change to strategy signal logic, thresholds, exits, sizing, filters, or state handling.
- Any shared research signal module that changes strategy output.
- Any registry parameter default that changes how a strategy trades.

This rule is not required for docs-only changes, UI-only display changes, or test-only refactors that cannot affect strategy output. If skipped, final delivery must say why.

## Evidence To Record

Record benchmark results under the smallest relevant `docs/qa/` file. Include at minimum:

- Strategy name and parameter set.
- CSV path, row count, start date, and end date for both stocks.
- Initial cash, commission, slippage, order limit, and trade size assumptions.
- Final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.
- A short interpretation that distinguishes baseline validation from optimization.

Future strategy iterations should compare against the previous result recorded for the same fixture set.
