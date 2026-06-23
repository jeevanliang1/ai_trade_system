# 2026-06-20 Automation Run History Diagnostics QA

## Scope

- Backend status payload now includes `recent_runs` and `diagnostics` for automation weekly/daily jobs.
- React `自动任务` workspace now renders `运行诊断` and `最近运行` panels.
- No strategy logic changed; fixed-stock strategy benchmark backtests were not applicable.

## Verification

```bash
PYTHONPATH=src python -m pytest
```

Result: 220 passed.

```bash
cd frontend && npm test
```

Result: 20 test files passed, 97 tests passed.

```bash
cd frontend && npm run build
```

Result: TypeScript compile and Vite production build completed successfully.

## Browser Acceptance

Started the default React + FastAPI surface with:

```bash
./scripts/run_app.sh
```

Validated `http://127.0.0.1:5173` on the `自动任务` workspace:

- Desktop 1440px: `运行诊断` and `最近运行` visible, no horizontal overflow, console error log empty.
- Mobile 390px: `运行诊断` and `最近运行` present in the page, mobile viewport screenshot scrolled to the diagnostic cards, no horizontal overflow.

Screenshots:

- `docs/qa/screenshots/2026-06-20-automation-run-history-diagnostics_desktop_1440.png`
- `docs/qa/screenshots/2026-06-20-automation-run-history-diagnostics_mobile_390.png`
