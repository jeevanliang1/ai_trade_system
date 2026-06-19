# Automation Radar Maintenance Design

## Goal

Add an in-project automation business area that starts with the FastAPI platform, keeps STAR-market and watchlist market data maintained, produces a weekly STAR top10 radar list, and refreshes the next-week daily judgment for those top10 stocks.

## Confirmed Scope

- Startup mode: option A. Automation starts only when the React + FastAPI platform is running through the normal app process.
- No machine-level `launchd`, cron, or systemd config is added in this slice.
- Automation is research/data maintenance only. It must not trigger paper trading, live trading, broker actions, or order placement.
- The first implementation manages STAR-market and watchlist workflows; it does not add arbitrary custom task scripting.

## Product Behavior

### Weekly Full Maintenance

When the automation service decides the weekly task is due, it should:

1. Load the local A-share catalog.
2. Select STAR-market candidates where `exchange == "SSE"` and `code.startswith("688")`.
3. Load the current watchlist from `config/watchlist.json`.
4. Update STAR-market and watchlist data through the existing `data_manager.update_stock_data` / batch helpers.
5. Reuse existing local CSVs when incremental provider data is unavailable but a usable latest CSV exists.
6. Run the full STAR radar scan using the established buy-oriented composite:

```text
composite_score = max(chan_score, 0) + volume_score * 0.35
```

7. Persist the top10 ranked results for the next week's daily tracking.

The task is called "weekly" because it is intended for Saturday. If the app was not running on Saturday, the next platform startup should detect the missed weekly task and run one catch-up pass.

### Daily Top10 Judgment

When the daily task is due, it should:

1. Read the latest persisted weekly STAR top10.
2. Update data for those top10 stocks.
3. Recalculate Chan structure, volume momentum, and the composite score for those same symbols.
4. Compare the current score and signal state with the weekly baseline.
5. Persist one daily judgment record per stock.

Initial judgment categories:

- `strong_follow`: Chan is T3 or confirmed buy, and volume momentum is entry-ready.
- `starter_follow`: Chan is T2 buy or weaker buy, and volume momentum is supportive or not harmful.
- `watch_only`: Chan is bullish but volume momentum is not confirmed.
- `risk_watch`: Chan turns bearish, latest structure is sell-side, or score drops materially from the weekly baseline.
- `insufficient_data`: the local CSV exists but does not meet minimum bar requirements.
- `missing_data`: no usable local CSV exists.

The daily output should include the underlying evidence, not only the label:

- latest trading day and close price
- current composite score
- weekly baseline score
- Chan score, direction, latest signal title, action, structure counts
- volume score, momentum percentage, volume ratio, trend pass, entry-ready flag
- concise Chinese reason text

## Architecture

Add a new backend package:

```text
src/ai_trade_system/automation/
  __init__.py
  models.py
  store.py
  radar.py
  service.py
  scheduler.py
```

### `models.py`

Owns dataclasses or Pydantic models for durable automation state:

- `AutomationConfig`
- `AutomationRunRecord`
- `RadarCandidateScore`
- `WeeklyRadarResult`
- `DailyJudgment`
- `AutomationStatus`

Default config:

```text
enabled = true
timezone = "Asia/Shanghai"
weekly_weekday = 5
weekly_time = "09:30"
daily_time = "09:45"
top_n = 10
adjust = "qfq"
min_bars = 60
lookback = 120
chan_weight = 1.0
volume_weight = 0.35
```

`weekly_weekday = 5` means Saturday using Python `date.weekday()` semantics.

### `store.py`

Owns JSON persistence under:

```text
data/automation/config.json
data/automation/state.json
data/automation/star_radar_top10.json
data/automation/daily_judgments/YYYY-MM-DD.json
logs/automation/runs.jsonl
```

The store should be small and deterministic:

- Create parent directories on write.
- Return sensible defaults when files are missing.
- Write JSON using UTF-8 and `ensure_ascii=False`.
- Avoid storing raw full 608-stock scan payloads in tracked files.

`data/automation/` and `logs/automation/` remain local runtime artifacts and should not be committed.

### `radar.py`

Owns reusable radar scoring outside FastAPI request limits.

It should reuse the existing project scoring semantics from `api.service` initially:

- `_chan_structure_score`
- `_volume_momentum_score`
- `read_bars_csv`
- `data_file_for_stock`

This wrapper exists so automation does not need to call FastAPI endpoints or work around the API batch limit of 300 candidates. It can scan all 608 STAR stocks directly from local CSVs.

### `service.py`

Owns business orchestration:

- `run_weekly_full_maintenance(now=None) -> WeeklyRadarResult`
- `run_daily_top10_judgment(now=None) -> list[DailyJudgment]`
- `status(now=None) -> AutomationStatus`
- `update_config(patch) -> AutomationConfig`

The service should protect against re-entry with an in-process lock. If a task is already running, a manual trigger should return a busy status rather than starting another run.

### `scheduler.py`

Owns lifecycle and due-check behavior:

- Start when FastAPI starts.
- Stop when FastAPI shuts down.
- Check periodically, for example every 60 seconds in production and shorter intervals in tests through injection.
- Run at most one automation job at a time.
- Record run start, completion, duration, status, and error message.

Due-check behavior:

- Weekly task is due when no successful weekly run exists for the current weekly period and today is Saturday or a Saturday run was missed.
- Daily task is due when a weekly top10 exists and no successful daily judgment exists for the current local date.
- Startup should call the due-check soon after the scheduler starts; it should not wait until the next day.

## FastAPI Integration

Change `create_app()` to use FastAPI lifespan or startup/shutdown hooks:

- Instantiate the automation scheduler once per app.
- Start it if automation config is enabled.
- Stop it on shutdown.

Add API routes:

```text
GET  /api/automation/status
GET  /api/automation/radar/top10
GET  /api/automation/judgments
POST /api/automation/run-weekly
POST /api/automation/run-daily
PUT  /api/automation/config
```

Manual trigger routes should be useful for development and UI actions. They should run the corresponding task synchronously enough to return the result in local usage, unless the implementation needs to return an accepted/busy state for long-running production safety.

## React Integration

Add a new business workspace for automation management. The first UI should be operational, not decorative:

- Current automation enabled/disabled state.
- Last weekly run and status.
- Last daily run and status.
- Latest STAR top10 table.
- Latest daily judgments table.
- Manual "run weekly scan" and "run daily judgment" buttons.
- Basic config controls for enabled, topN, and weights if backend config supports them in the first implementation.

The UI should not imply broker execution. Labels should use research wording such as "自动研究任务", "数据维护", "雷达 Top10", and "每日判断".

## Error Handling

- Provider failures should be captured per stock when existing local CSVs are unavailable.
- A weekly task can complete as `partial` when some symbols fail but at least one ranked result exists.
- A weekly task should complete as `failed` only when no usable ranking can be produced.
- Daily judgment should mark missing or insufficient top10 symbols individually and still return judgments for the rest.
- JSON write errors should fail the task and surface in `/api/automation/status`.
- Scheduler exceptions must not crash FastAPI; they should be recorded as failed runs.

## Testing Requirements

Use TDD for implementation.

Backend tests:

- Store defaults when config/state files are missing.
- Store round-trips config, top10, daily judgments, and run records.
- Radar scanner ranks candidates by the composite score using controlled fake CSVs.
- Weekly service updates STAR and watchlist candidates, persists top10, and records success.
- Weekly service returns partial when some data updates fail but ranking remains usable.
- Daily service refreshes top10 symbols and emits judgment labels from score/signal combinations.
- Scheduler runs due weekly task on Saturday.
- Scheduler catches up a missed Saturday weekly task on next startup.
- Scheduler does not rerun weekly or daily tasks twice for the same period/date.
- Manual trigger returns busy when a task is already running.
- API routes expose status, top10, judgments, manual triggers, and config updates.

Frontend tests:

- Automation page renders status, latest top10, and latest daily judgments.
- Manual weekly and daily buttons call the correct API client methods.
- Busy or failed backend responses render actionable state, not a blank page.

Verification commands:

```bash
PYTHONPATH=src python -m pytest tests/test_automation*.py tests/test_api_routes.py -q
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run Automation
cd frontend && npm test -- --run
cd frontend && npm run build
```

Because this feature does not change strategy logic, the fixed six-stock benchmark is not required unless implementation changes strategy or radar scoring internals.

## Non-Goals

- No live broker gateway or real order execution.
- No machine-level recurring launch agent in this slice.
- No email, notification, WeChat, or push delivery in this slice.
- No backtesting triggered automatically by the scheduler.
- No arbitrary user-defined Python automation scripts.

## Open Follow-Ups

- Add notification channels after daily judgment is stable.
- Add machine-level deployment recipes only after the in-app automation business is proven.
- Add configurable universes beyond STAR and watchlist.
- Add browser-visible charts for score drift after enough daily judgment history exists.
