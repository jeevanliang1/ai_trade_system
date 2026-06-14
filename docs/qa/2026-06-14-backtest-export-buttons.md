# Backtest Export Buttons QA

Date: 2026-06-14

## Scope

Completed the Backtest Center export actions module.

## Evidence

- Added a `回测结果导出` panel in the Backtest Center result column.
- Added disabled export buttons before a backtest result exists: `导出交易`, `导出指标`, and `导出资金曲线`.
- Added client-side downloads for `backtest_trades.csv`, `backtest_metrics.json`, and `backtest_equity_curve.csv`.
- Added CSV escaping and header-only output support when an exported row set is empty.
- Added Backtest Center test coverage for disabled export state and generated trade, metrics, and equity-curve download content.
- Ran `npm test -- BacktestPage.test.tsx`: 5 tests passed.
- Ran `npm test`: 11 files and 36 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Ran `python -m pytest`: 56 tests passed.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; it verified page identity, nonblank content, no framework overlay, no console errors, disabled export buttons before a run, enabled export buttons after a real backtest run, and populated result metrics.
- In-app Browser screenshot capture timed out on `Page.captureScreenshot`; the required PNG evidence was captured with headless system Chrome after repeating the same interaction through Chrome DevTools Protocol.
- Acceptance screenshot: `docs/qa/screenshots/2026-06-14-backtest-export-buttons.png`.

## Notes

Exports are intentionally browser-local because all required result payloads are already present in the Backtest Center response.
