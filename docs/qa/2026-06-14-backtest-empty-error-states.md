# Backtest Empty And Error States QA

Date: 2026-06-14

## Scope

Completed the Backtest Center empty/error-state module.

## Evidence

- Added a `回测准备状态` block in Backtest Center that lists run blockers before users click `运行回测`.
- Added a result-side `回测结果状态` empty/error block that explains why charts and tables cannot populate yet.
- Covered missing or unloaded CSV data with `缺少行情CSV` guidance and current CSV path.
- Covered missing single-strategy selection with `缺少回测策略` guidance.
- Covered invalid portfolio allocation with `组合分配无效` guidance for missing enabled positive-weight allocations or deleted strategies.
- Disabled the Backtest Center page run button while readiness blockers exist.
- Added focused Backtest Center tests for missing CSV data, missing strategy, and invalid portfolio allocation.
- Updated the AppShell duplicate-run test fixture so the busy-state workflow uses a truly runnable setup with loaded bars and a selected strategy.
- Ran `npm test -- BacktestPage.test.tsx`: 8 tests passed.
- Ran `npm test -- AppShell.tasks.test.tsx`: 3 tests passed.
- Ran `npm test`: 11 files and 39 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Ran `python -m pytest`: 56 tests passed.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; it verified page identity, nonblank content, no framework overlay, no console errors/warnings, ready Backtest Center state, and blocked state after changing the data target to `601318 SSE`.
- In-app Browser screenshot capture timed out on `Page.captureScreenshot`; the required PNG evidence was captured with headless system Chrome after repeating the same ready-to-blocked interaction through Chrome DevTools Protocol.
- Acceptance screenshot: `docs/qa/screenshots/2026-06-14-backtest-empty-error-states.png`.

## Notes

The readiness checks are intentionally client-side and conservative. They prevent obvious blocked runs while the API still remains the final authority for file existence, strategy lookup, and request validation.
