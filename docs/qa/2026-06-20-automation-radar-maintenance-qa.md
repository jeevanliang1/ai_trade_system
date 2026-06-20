# Automation Radar Maintenance QA - 2026-06-20

## Scope

This QA pass covers the in-app automation business for STAR/watchlist data maintenance and radar follow-up:

- FastAPI starts and stops an `AutomationScheduler` with the app lifespan.
- `ai_trade_system.automation` persists config, weekly radar results, daily judgments, and run records under ignored runtime paths.
- Weekly automation updates STAR plus watchlist data, scans the STAR universe with Chan primary and volume-price assist scoring, and persists a Top N result.
- Daily automation refreshes judgment for the persisted Top N.
- React adds an `自动任务` workspace with status, config editing, weekly top list, daily judgments, and manual run controls.

This work does not modify strategy trading logic or add a new backtestable strategy, so the fixed six-stock strategy benchmark backtest rule was not triggered.

## Automated Verification

```bash
PYTHONPATH=src python -m pytest tests/test_automation_store.py tests/test_automation_radar.py tests/test_automation_service.py tests/test_automation_scheduler.py tests/test_api_routes.py -q
```

Result: `40 passed in 1.43s`.

```bash
PYTHONPATH=src python -m pytest
```

Result: `204 passed in 7.63s`.

```bash
cd frontend && npm test -- --run src/pages/AutomationPage.test.tsx
```

Result: `1 passed`, `2 passed`.

```bash
cd frontend && npm test
```

Result: `19 passed`, `94 passed`.

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite build completed successfully.

## Browser QA

Local app:

```bash
./scripts/run_app.sh
```

Target flow:

```text
http://127.0.0.1:5173/ -> 自动任务 -> edit Top N -> 保存配置
```

Browser checks:

| Check | Result |
| --- | --- |
| Page identity | `http://127.0.0.1:5173/`, title `AI量化平台` |
| Not blank | `自动任务管理` workspace rendered with status, config, empty top list, and empty daily judgment state |
| Framework overlay | None observed |
| Console health | 0 `error` / `warn` logs on desktop and mobile |
| Desktop interaction | `Top N 数量` changed to `9`, `保存配置` returned `自动任务配置已保存` |
| Mobile rendering | 390x844 viewport rendered wrapped navigation and the automation controls without horizontal overflow symptoms |

Screenshot evidence:

- Desktop: `docs/qa/screenshots/2026-06-20-automation-radar-maintenance-desktop.png`
- Mobile: `docs/qa/screenshots/2026-06-20-automation-radar-maintenance-mobile.png`

QA used a temporary ignored `data/automation/state.json` marking the current weekly and daily run as already complete, then removed `data/automation/` after the browser pass. This prevented the startup scheduler from launching a large STAR data maintenance run during UI validation while still exercising the real FastAPI and React surface.
