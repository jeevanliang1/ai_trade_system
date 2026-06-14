# Backtest Busy State QA

Date: 2026-06-14

## Scope

Completed the Backtest Center progress/busy-state module.

## Evidence

- Added platform state for the active backtest mode while a run is pending.
- Added a shared task-runner guard so new tasks are ignored while another task is already busy.
- Added Backtest Center UI for `回测运行状态`, including active mode, idle/running copy, disabled mode buttons, and disabled duplicate run button.
- Added test coverage for Backtest Center busy rendering and AppShell duplicate-run protection.
- Ran `npm test -- BacktestPage.test.tsx`: 2 tests passed.
- Ran `npm test -- AppShell.tasks.test.tsx`: 3 tests passed.
- Ran `npm test`: 11 files and 33 tests passed.
- Ran `npm run build`: Vite production build succeeded.
- Ran `python -m pytest`: 56 tests passed.
- Browser QA used the in-app Browser at `http://127.0.0.1:5174/` because `5173` was occupied by an existing Vite process; it verified page identity, nonblank content, no framework overlay, no console warnings/errors, Backtest Center idle status, and a completed real backtest run.
- The real API completed too quickly to capture the transient pending state in the in-app Browser, so screenshot evidence used system Chrome with a delayed `/api/backtest` response against the same app surface.
- Delayed Chrome QA verified `单策略回测运行中`, disabled `运行中...`, exactly one `/api/backtest` request after a duplicate click attempt, and return to `等待运行` after completion.
- Acceptance screenshot: `docs/qa/screenshots/2026-06-14-backtest-busy-state.png`.

## Notes

The delayed screenshot uses a controlled API response only to keep the pending state visible long enough to inspect. Normal in-app Browser QA also exercised the live backend path and confirmed the completed-run state.
