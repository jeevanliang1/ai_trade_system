# Chart And Backtest Depth QA

## Scope

- Strategy Workshop K-line and volume chart zoom synchronization.
- Buy/sell marker detail payloads for signal preview.
- Backtest metrics with benchmark return, excess return, annual volatility, Sharpe-like ratio, and profit factor.
- Result tabs for 回测结果, 交易明细, 持仓分析, 因子暴露, 风险分析, and 绩效归因.
- Dense strategy/cash/long-only comparison table.

## Verification

- `python -m pytest -q`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- Browser flow: `http://localhost:5173` -> run backtest -> open 交易明细, 风险分析, and 绩效归因 tabs.

## Evidence

- Browser interaction checks found no console `error` or `warn` entries.
- Headless Chrome screenshot: `/tmp/ai_trade_system_chart_backtest_depth.png`
- Screenshot dimensions: `1440 x 1024`

## Notes

- The Browser plugin completed DOM and interaction validation, but its screenshot capture path timed out on `Page.captureScreenshot`.
- The acceptance screenshot was captured with the project-documented headless Chrome command instead.
