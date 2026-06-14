# Data Center Module QA

## Scope

- Stock search dropdown backed by `/api/stocks?query=` with code, name, and exchange results.
- Automatic symbol, exchange, and CSV-path selection from stock results.
- Date-range and CSV-path validation before load/download/demo data actions.
- Data target changes clear stale bars, summaries, signals, backtests, and paper output.
- CSV health panel with row count, coverage, missing values, latest close, current local path, and path status.
- Data request busy state plus download retry copy and demo-data fallback when a request fails.

## Verification

- `cd frontend && npm test`
- `cd frontend && npm run build`
- `python -m pytest`
- Browser flow: `http://127.0.0.1:5173` -> 数据中心 -> search `中国平安` -> select `601318 中国平安 SSE`.

## Evidence

- Browser DOM checks confirmed the React app title, Data Center controls, health panel, and no console `error` or `warn` entries.
- Headless Chrome screenshot: `/tmp/ai_trade_system_data_center_acceptance.png`
- Screenshot dimensions: `1440 x 937`
- Rendered proof after stock selection: symbol `601318`, exchange `SSE`, CSV path `data/601318_daily.csv`, health row count `0 行`, and empty table state `暂无数据`.

## Notes

- The Browser plugin completed page identity, DOM, and console validation. Its screenshot/input helpers later hit `Browser Use virtual clipboard is not installed`, so final interaction proof and screenshot capture used headless Chrome over CDP.
