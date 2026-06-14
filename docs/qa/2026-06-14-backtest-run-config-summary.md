# Backtest Run Configuration Summary QA

Date: 2026-06-14

## Scope

Completed the Backtest Center run configuration summary module.

## Evidence

- Added a result-side `回测运行配置` panel showing symbol/exchange, date range, selected run mode, selected strategy or portfolio vote mode, initial cash, commission, and slippage.
- Added Backtest Center test coverage for default single-strategy summary values and summary updates after switching to portfolio mode.
- Ran `npm test -- BacktestPage.test.tsx`: 3 tests passed.
- Ran `npm test`: 11 files and 34 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Ran `python -m pytest`: 56 tests passed.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; it verified page identity, nonblank content, no framework overlay, no console warnings/errors, and the interaction path `回测中心 -> 组合策略`.
- In-app Browser verified the summary text before mode switch: `000001 SZSE`, date range, `单策略`, `DualMovingAverageStrategy`, `100,000`, `0.03%`, and `0.01`.
- In-app Browser verified the summary text after mode switch: `组合策略` and `加权投票`.
- In-app Browser screenshot capture timed out on `Page.captureScreenshot`; the required PNG evidence was captured with system Chrome after repeating the same interaction.
- Acceptance screenshot: `docs/qa/screenshots/2026-06-14-backtest-run-config-summary.png`.

## Notes

The summary intentionally reflects the currently selected Backtest Center mode, not only the last completed response, so users can confirm the run setup before clicking `运行回测`.
