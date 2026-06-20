# Automation Radar Maintenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an in-app automation business that starts with FastAPI, maintains STAR/watchlist data, produces a weekly STAR radar top10, and refreshes daily judgments for that top10.

**Architecture:** Add a focused `ai_trade_system.automation` package for models, JSON persistence, radar scoring, orchestration, and scheduler lifecycle. Expose the business through FastAPI routes and a React automation workspace while keeping runtime artifacts under ignored `data/automation/` and `logs/automation/`.

**Tech Stack:** Python 3, dataclasses, pathlib/json, FastAPI/TestClient, pytest, React/TypeScript/Vite, Vitest, Testing Library.

---

## File Structure

- Create `src/ai_trade_system/automation/__init__.py`: package exports.
- Create `src/ai_trade_system/automation/models.py`: dataclasses and conversion helpers for config, runs, scores, weekly result, daily judgment, and status.
- Create `src/ai_trade_system/automation/store.py`: deterministic JSON and JSONL persistence.
- Create `src/ai_trade_system/automation/radar.py`: full-universe local CSV radar scoring outside the API batch limit.
- Create `src/ai_trade_system/automation/service.py`: weekly maintenance, daily judgment, status, config update, and busy lock.
- Create `src/ai_trade_system/automation/scheduler.py`: due checks and background lifecycle.
- Modify `src/ai_trade_system/api/schemas.py`: automation config request schema if needed by API.
- Modify `src/ai_trade_system/api/service.py`: automation service accessors and route handlers.
- Modify `src/ai_trade_system/api/app.py`: lifespan/startup integration and automation routes.
- Create `tests/test_automation_store.py`: store defaults and round trips.
- Create `tests/test_automation_radar.py`: composite radar ranking from controlled CSVs.
- Create `tests/test_automation_service.py`: weekly and daily orchestration behavior.
- Create `tests/test_automation_scheduler.py`: due checks and re-entry behavior.
- Modify `tests/test_api_routes.py`: automation API route coverage.
- Modify `frontend/src/types.ts`: automation response/request types.
- Modify `frontend/src/api/client.ts`: automation client methods.
- Create `frontend/src/pages/AutomationPage.tsx`: management workspace.
- Create `frontend/src/pages/AutomationPage.test.tsx`: page behavior tests.
- Modify `frontend/src/shell/AppShell.tsx`: nav entry and page switch.
- Modify `frontend/src/styles.css`: compact automation page layout if existing styles do not cover it.
- Create `docs/qa/2026-06-20-automation-radar-maintenance-qa.md`: implementation verification record.

## Task 1: Automation Models And Store

**Files:**
- Create: `src/ai_trade_system/automation/__init__.py`
- Create: `src/ai_trade_system/automation/models.py`
- Create: `src/ai_trade_system/automation/store.py`
- Test: `tests/test_automation_store.py`

- [ ] **Step 1: Write failing store tests**

```python
from __future__ import annotations

from datetime import datetime

from ai_trade_system.automation.models import (
    AutomationConfig,
    AutomationRunRecord,
    DailyJudgment,
    RadarCandidateScore,
    WeeklyRadarResult,
)
from ai_trade_system.automation.store import AutomationStore


def test_automation_store_returns_defaults_when_files_are_missing(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")

    config = store.load_config()
    status = store.load_state()

    assert config.enabled is True
    assert config.weekly_weekday == 5
    assert config.top_n == 10
    assert config.volume_weight == 0.35
    assert status["last_weekly_run"] is None
    assert status["last_daily_run"] is None


def test_automation_store_round_trips_config_top10_judgments_and_runs(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    config = AutomationConfig(enabled=False, top_n=5, volume_weight=0.5)
    candidate = RadarCandidateScore(
        code="688001",
        name="华兴源创",
        exchange="SSE",
        rank=1,
        composite_score=70.1,
        chan_score=44.0,
        volume_score=74.7,
        latest_day="2026-06-18",
        latest_close=81.09,
        chan_signal_title="缠论三买",
        chan_signal_action="buy",
        volume_entry_ready=False,
        reason="三买结构，量能不足",
    )
    weekly = WeeklyRadarResult(
        run_id="weekly-1",
        generated_at="2026-06-20T09:30:00+08:00",
        status="success",
        total_candidates=1,
        scanned=1,
        missing=0,
        top=[candidate],
    )
    judgment = DailyJudgment(
        code="688001",
        name="华兴源创",
        exchange="SSE",
        judgment="watch_only",
        reason="三买结构仍在，量能未确认",
        current_score=70.1,
        baseline_score=70.1,
        latest_day="2026-06-23",
        latest_close=82.0,
        chan_signal_title="缠论三买",
        volume_entry_ready=False,
    )
    run = AutomationRunRecord(
        run_id="run-1",
        task="weekly",
        status="success",
        started_at="2026-06-20T09:30:00+08:00",
        finished_at="2026-06-20T09:31:00+08:00",
        message="ok",
    )

    store.save_config(config)
    store.save_weekly_result(weekly)
    store.save_daily_judgments("2026-06-23", [judgment])
    store.append_run(run)

    assert store.load_config().top_n == 5
    assert store.load_config().enabled is False
    assert store.load_weekly_result().top[0].code == "688001"
    assert store.load_daily_judgments("2026-06-23")[0].judgment == "watch_only"
    assert store.load_runs()[-1].task == "weekly"
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_store.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'ai_trade_system.automation'`.

- [ ] **Step 3: Implement models and store**

Create `src/ai_trade_system/automation/models.py` with dataclasses using `asdict` and `from_dict` classmethods. Include defaults:

```python
@dataclass
class AutomationConfig:
    enabled: bool = True
    timezone: str = "Asia/Shanghai"
    weekly_weekday: int = 5
    weekly_time: str = "09:30"
    daily_time: str = "09:45"
    top_n: int = 10
    adjust: str = "qfq"
    min_bars: int = 60
    lookback: int = 120
    chan_weight: float = 1.0
    volume_weight: float = 0.35
```

Create `src/ai_trade_system/automation/store.py` with `AutomationStore`, `load_config`, `save_config`, `load_state`, `save_state`, `load_weekly_result`, `save_weekly_result`, `load_daily_judgments`, `save_daily_judgments`, `append_run`, and `load_runs`. Use `json.loads`, `json.dumps(payload, ensure_ascii=False, indent=2)`, and parent directory creation before writes.

Create `src/ai_trade_system/automation/__init__.py`:

```python
from ai_trade_system.automation.models import AutomationConfig, AutomationStatus, DailyJudgment, RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.automation.store import AutomationStore

__all__ = [
    "AutomationConfig",
    "AutomationStatus",
    "AutomationStore",
    "DailyJudgment",
    "RadarCandidateScore",
    "WeeklyRadarResult",
]
```

- [ ] **Step 4: Run store tests green**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_store.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Commit Task 1**

```bash
git add src/ai_trade_system/automation tests/test_automation_store.py
git commit -m "feat: add automation store"
```

## Task 2: Full-Universe Radar Scoring Wrapper

**Files:**
- Create: `src/ai_trade_system/automation/radar.py`
- Test: `tests/test_automation_radar.py`

- [ ] **Step 1: Write failing radar tests**

```python
from __future__ import annotations

from datetime import date, timedelta

from ai_trade_system.automation.models import AutomationConfig
from ai_trade_system.automation.radar import scan_star_radar_candidates
from ai_trade_system.data import write_bars_csv
from ai_trade_system.data_manager import data_file_for_stock
from ai_trade_system.market import Bar
from ai_trade_system.stock_catalog import StockInfo


def _bar(symbol: str, exchange: str, day: date, close: float, volume: float) -> Bar:
    return Bar(
        symbol=symbol,
        exchange=exchange,
        trading_day=day,
        open_price=close - 0.2,
        high_price=close + 0.4,
        low_price=close - 0.4,
        close_price=close,
        volume=volume,
        turnover=close * volume,
    )


def _write_stock(stock: StockInfo, closes: list[float], volumes: list[float]) -> None:
    start = date(2026, 1, 1)
    write_bars_csv(
        [_bar(stock.code, stock.exchange, start + timedelta(days=index), close, volumes[index]) for index, close in enumerate(closes)],
        data_file_for_stock(stock, adjust="qfq").latest_path,
    )


def test_scan_star_radar_candidates_ranks_by_chan_primary_volume_assist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    strong = StockInfo("688001", "强结构", "SSE")
    weak = StockInfo("688002", "弱结构", "SSE")
    missing = StockInfo("688003", "缺数据", "SSE")
    closes = ([10, 9, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15] * 4)
    _write_stock(strong, closes, [1000.0] * len(closes))
    _write_stock(weak, [10 + index * 0.05 for index in range(80)], [900.0] * 79 + [2500.0])

    result = scan_star_radar_candidates([weak, missing, strong], AutomationConfig(top_n=2, min_bars=60, lookback=120))

    assert result.total_candidates == 3
    assert result.scanned == 2
    assert result.missing == 1
    assert len(result.top) == 2
    assert result.top[0].rank == 1
    assert result.top[0].composite_score >= result.top[1].composite_score
    assert result.top[0].reason
```

- [ ] **Step 2: Run the failing radar test**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_radar.py -q
```

Expected: fail with `ModuleNotFoundError` or `ImportError` for `ai_trade_system.automation.radar`.

- [ ] **Step 3: Implement radar wrapper**

Create `scan_star_radar_candidates(stocks, config, generated_at=None) -> WeeklyRadarResult`:

```python
def scan_star_radar_candidates(stocks: Iterable[StockInfo], config: AutomationConfig, generated_at: str | None = None) -> WeeklyRadarResult:
    stock_list = list(stocks)
    rows: list[RadarCandidateScore] = []
    missing = 0
    for stock in stock_list:
        path = data_file_for_stock(stock, adjust=config.adjust).latest_path
        if not path.exists():
            missing += 1
            continue
        bars = read_bars_csv(path)
        chan_score, chan_latest, _chan_blockers, _chan_preview = _chan_structure_score(bars, config.min_bars, config.lookback)
        volume_score, _volume_latest, _volume_blockers, momentum = _volume_momentum_score(bars, config.min_bars)
        composite = round(max(0.0, float(chan_score.get("total_score", 0))) * config.chan_weight + float(volume_score.get("total_score", 0)) * config.volume_weight, 4)
        latest = bars[-1] if bars else None
        rows.append(
            RadarCandidateScore(
                code=stock.code,
                name=stock.name,
                exchange=stock.exchange,
                rank=0,
                composite_score=composite,
                chan_score=float(chan_score.get("total_score", 0)),
                volume_score=float(volume_score.get("total_score", 0)),
                latest_day=latest.trading_day.isoformat() if latest else None,
                latest_close=latest.close_price if latest else None,
                chan_signal_title=(chan_latest or {}).get("title"),
                chan_signal_action=(chan_latest or {}).get("action"),
                volume_entry_ready=bool(momentum.get("entry_ready")),
                reason=_radar_reason(chan_score, volume_score, chan_latest, momentum),
            )
        )
    rows.sort(key=lambda row: (-row.composite_score, -row.chan_score, -row.volume_score, row.code))
    top = [replace(row, rank=index) for index, row in enumerate(rows[: config.top_n], start=1)]
    return WeeklyRadarResult(
        run_id=f"weekly-{generated_at or datetime.now().isoformat()}",
        generated_at=generated_at or datetime.now().isoformat(),
        status="success" if top else "failed",
        total_candidates=len(stock_list),
        scanned=len(rows),
        missing=missing,
        top=top,
    )
```

Use helper functions for `reason` text and signal extraction so this file remains readable.

- [ ] **Step 4: Run radar tests green**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_radar.py tests/test_automation_store.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add src/ai_trade_system/automation/radar.py tests/test_automation_radar.py
git commit -m "feat: add automation radar scanner"
```

## Task 3: Automation Service Weekly And Daily Workflows

**Files:**
- Create: `src/ai_trade_system/automation/service.py`
- Test: `tests/test_automation_service.py`

- [ ] **Step 1: Write failing service tests**

```python
from __future__ import annotations

from datetime import datetime

from ai_trade_system.automation.models import AutomationConfig, RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.automation.service import AutomationService, BusyAutomationError
from ai_trade_system.automation.store import AutomationStore
from ai_trade_system.stock_catalog import StockInfo


class FakeCatalog:
    def __call__(self):
        return [
            StockInfo("688001", "华兴源创", "SSE"),
            StockInfo("688002", "睿创微纳", "SSE"),
            StockInfo("000858", "五粮液", "SZSE"),
        ]


class FakeWatchlist:
    def __call__(self):
        return [StockInfo("601318", "中国平安", "SSE")]


class FakeUpdater:
    def __init__(self):
        self.calls = []

    def __call__(self, stock, *, start_date, end_date, adjust, if_stale=True):
        self.calls.append((stock.code, start_date, end_date, adjust, if_stale))
        return {"status": "updated", "code": stock.code, "latest_rows": 80, "message": "ok"}


def test_weekly_full_maintenance_updates_star_and_watchlist_then_persists_top10(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    updater = FakeUpdater()

    def scan(stocks, config, generated_at=None):
        return WeeklyRadarResult(
            run_id="weekly-1",
            generated_at=generated_at or "2026-06-20T09:30:00+08:00",
            status="success",
            total_candidates=len(list(stocks)),
            scanned=2,
            missing=0,
            top=[
                RadarCandidateScore(
                    code="688001",
                    name="华兴源创",
                    exchange="SSE",
                    rank=1,
                    composite_score=70.1,
                    chan_score=44,
                    volume_score=74.7,
                    latest_day="2026-06-18",
                    latest_close=81.09,
                    chan_signal_title="缠论三买",
                    chan_signal_action="buy",
                    volume_entry_ready=False,
                    reason="三买结构，量能不足",
                )
            ],
        )

    service = AutomationService(store=store, load_catalog=FakeCatalog(), load_watchlist=FakeWatchlist(), update_stock_data=updater, scan_star_radar=scan)

    result = service.run_weekly_full_maintenance(now=datetime(2026, 6, 20, 9, 30))

    assert result.status == "success"
    assert store.load_weekly_result().top[0].code == "688001"
    assert {call[0] for call in updater.calls} == {"688001", "688002", "601318"}


def test_daily_top10_judgment_marks_strong_follow_and_risk_watch(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    store.save_weekly_result(WeeklyRadarResult(run_id="weekly-1", generated_at="2026-06-20T09:30:00+08:00", status="success", total_candidates=1, scanned=1, missing=0, top=[
        RadarCandidateScore(code="688001", name="华兴源创", exchange="SSE", rank=1, composite_score=70, chan_score=44, volume_score=74, latest_day="2026-06-18", latest_close=81, chan_signal_title="缠论三买", chan_signal_action="buy", volume_entry_ready=False, reason="baseline")
    ]))

    def score_top(stocks, config, generated_at=None):
        return WeeklyRadarResult(run_id="daily-1", generated_at="2026-06-23T09:45:00+08:00", status="success", total_candidates=1, scanned=1, missing=0, top=[
            RadarCandidateScore(code="688001", name="华兴源创", exchange="SSE", rank=1, composite_score=90, chan_score=44, volume_score=100, latest_day="2026-06-23", latest_close=84, chan_signal_title="缠论三买", chan_signal_action="buy", volume_entry_ready=True, reason="三买叠加量价确认")
        ])

    service = AutomationService(store=store, load_catalog=lambda: [], load_watchlist=lambda: [], update_stock_data=lambda *args, **kwargs: {"status": "skipped"}, scan_star_radar=score_top)

    judgments = service.run_daily_top10_judgment(now=datetime(2026, 6, 23, 9, 45))

    assert judgments[0].judgment == "strong_follow"
    assert "量价确认" in judgments[0].reason
    assert store.load_daily_judgments("2026-06-23")[0].code == "688001"


def test_manual_trigger_returns_busy_when_lock_is_held(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    service = AutomationService(store=store, load_catalog=lambda: [], load_watchlist=lambda: [], update_stock_data=lambda *args, **kwargs: {"status": "skipped"}, scan_star_radar=lambda stocks, config, generated_at=None: None)
    assert service._lock.acquire(blocking=False)
    try:
        try:
            service.run_weekly_full_maintenance(now=datetime(2026, 6, 20, 9, 30))
        except BusyAutomationError as exc:
            assert "automation task is already running" in str(exc)
        else:
            raise AssertionError("expected BusyAutomationError")
    finally:
        service._lock.release()
```

- [ ] **Step 2: Run the failing service tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_service.py -q
```

Expected: fail because `ai_trade_system.automation.service` does not exist.

- [ ] **Step 3: Implement service**

Create `AutomationService` with injected dependencies:

```python
class AutomationService:
    def __init__(
        self,
        *,
        store: AutomationStore | None = None,
        load_catalog: Callable[[], list[StockInfo]] = load_stock_catalog,
        load_watchlist: Callable[[], list[StockInfo]] = load_watchlist,
        update_stock_data: Callable = update_stock_data,
        scan_star_radar: Callable = scan_star_radar_candidates,
    ):
        self.store = store or AutomationStore()
        self.load_catalog = load_catalog
        self.load_watchlist = load_watchlist
        self.update_stock_data = update_stock_data
        self.scan_star_radar = scan_star_radar
        self._lock = threading.Lock()
```

Implement `run_weekly_full_maintenance`, `run_daily_top10_judgment`, `status`, and `update_config`. Use `default_settings(now.date())` from API service or equivalent two-year date logic for start/end dates. Deduplicate STAR and watchlist updates by `(exchange, code)`.

- [ ] **Step 4: Run service tests green**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_store.py tests/test_automation_radar.py tests/test_automation_service.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add src/ai_trade_system/automation/service.py tests/test_automation_service.py
git commit -m "feat: add automation service workflows"
```

## Task 4: Scheduler Due Checks And FastAPI Lifecycle

**Files:**
- Create: `src/ai_trade_system/automation/scheduler.py`
- Modify: `src/ai_trade_system/api/app.py`
- Test: `tests/test_automation_scheduler.py`

- [ ] **Step 1: Write failing scheduler tests**

```python
from __future__ import annotations

from datetime import datetime

from ai_trade_system.automation.models import AutomationConfig, AutomationRunRecord
from ai_trade_system.automation.scheduler import AutomationScheduler
from ai_trade_system.automation.store import AutomationStore


class FakeService:
    def __init__(self, store):
        self.store = store
        self.weekly_calls = 0
        self.daily_calls = 0

    def run_weekly_full_maintenance(self, now=None):
        self.weekly_calls += 1
        self.store.save_state({"last_weekly_success_date": now.date().isoformat(), "last_daily_success_date": None, "last_weekly_run": None, "last_daily_run": None})

    def run_daily_top10_judgment(self, now=None):
        self.daily_calls += 1
        self.store.save_state({"last_weekly_success_date": "2026-06-20", "last_daily_success_date": now.date().isoformat(), "last_weekly_run": None, "last_daily_run": None})


def test_scheduler_runs_weekly_on_saturday_once(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 20, 10, 0))
    scheduler.run_due_tasks(now=datetime(2026, 6, 20, 10, 5))

    assert service.weekly_calls == 1


def test_scheduler_catches_up_missed_saturday_on_startup(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 22, 9, 0))

    assert service.weekly_calls == 1


def test_scheduler_runs_daily_when_weekly_top10_exists(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    store.save_state({"last_weekly_success_date": "2026-06-20", "last_daily_success_date": None, "last_weekly_run": None, "last_daily_run": None})
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 23, 10, 0))
    scheduler.run_due_tasks(now=datetime(2026, 6, 23, 10, 5))

    assert service.daily_calls == 1
```

- [ ] **Step 2: Run the failing scheduler tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_scheduler.py -q
```

Expected: fail because `ai_trade_system.automation.scheduler` does not exist.

- [ ] **Step 3: Implement scheduler**

Create `AutomationScheduler` with:

- `run_due_tasks(now=None)` for deterministic tests.
- `start()` that creates a daemon thread and calls `run_due_tasks` immediately, then sleeps for `check_interval_seconds`.
- `stop()` that sets an event and joins the thread.
- Weekly period logic based on the most recent Saturday for local dates.
- Daily logic based on `last_daily_success_date`.

Modify `src/ai_trade_system/api/app.py` to instantiate the scheduler during app creation and register startup/shutdown handlers:

```python
automation_service = service.get_automation_service()
automation_scheduler = service.get_automation_scheduler(automation_service)

@app.on_event("startup")
def start_automation() -> None:
    automation_scheduler.start()

@app.on_event("shutdown")
def stop_automation() -> None:
    automation_scheduler.stop()
```

If TestClient startup would run real background work, use service-level config to keep checks safe and non-networked in tests, or inject a disabled scheduler in API tests.

- [ ] **Step 4: Run scheduler tests green**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_scheduler.py tests/test_automation_service.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add src/ai_trade_system/automation/scheduler.py src/ai_trade_system/api/app.py tests/test_automation_scheduler.py
git commit -m "feat: start automation scheduler with api"
```

## Task 5: Automation API Routes

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `src/ai_trade_system/api/app.py`
- Modify: `tests/test_api_routes.py`

- [ ] **Step 1: Write failing API route tests**

Append to `tests/test_api_routes.py`:

```python
def test_automation_status_route_returns_config_and_runs(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/automation/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["config"]["enabled"] is True
    assert payload["weekly_top10_count"] == 0
    assert payload["latest_daily_judgment_count"] == 0


def test_automation_config_route_updates_enabled_and_weights(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.put("/api/automation/config", json={"enabled": False, "top_n": 8, "volume_weight": 0.5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["top_n"] == 8
    assert payload["volume_weight"] == 0.5


def test_automation_top10_and_judgments_routes_return_empty_defaults(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    top10 = client.get("/api/automation/radar/top10")
    judgments = client.get("/api/automation/judgments")

    assert top10.status_code == 200
    assert top10.json()["top"] == []
    assert judgments.status_code == 200
    assert judgments.json()["judgments"] == []
```

- [ ] **Step 2: Run failing API tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_automation_status_route_returns_config_and_runs tests/test_api_routes.py::test_automation_config_route_updates_enabled_and_weights tests/test_api_routes.py::test_automation_top10_and_judgments_routes_return_empty_defaults -q
```

Expected: fail with `404 Not Found` for `/api/automation/status`.

- [ ] **Step 3: Implement service handlers and routes**

Add request schema:

```python
class AutomationConfigRequest(BaseModel):
    enabled: bool | None = None
    top_n: int | None = Field(default=None, ge=1, le=50)
    chan_weight: float | None = Field(default=None, ge=0, le=5)
    volume_weight: float | None = Field(default=None, ge=0, le=5)
```

Add service functions:

```python
_AUTOMATION_SERVICE: AutomationService | None = None

def get_automation_service() -> AutomationService:
    global _AUTOMATION_SERVICE
    if _AUTOMATION_SERVICE is None:
        _AUTOMATION_SERVICE = AutomationService()
    return _AUTOMATION_SERVICE

def automation_status() -> dict[str, Any]:
    return get_automation_service().status().as_dict()
```

Add routes in `create_app()`:

```python
@app.get("/api/automation/status")
def automation_status() -> dict[str, Any]:
    return _handle(service.automation_status)
```

Add equivalent routes for top10, judgments, manual weekly, manual daily, and config update.

- [ ] **Step 4: Run API tests green**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_automation_status_route_returns_config_and_runs tests/test_api_routes.py::test_automation_config_route_updates_enabled_and_weights tests/test_api_routes.py::test_automation_top10_and_judgments_routes_return_empty_defaults -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit Task 5**

```bash
git add src/ai_trade_system/api/schemas.py src/ai_trade_system/api/service.py src/ai_trade_system/api/app.py tests/test_api_routes.py
git commit -m "feat: expose automation api"
```

## Task 6: React Automation Workspace

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Create: `frontend/src/pages/AutomationPage.tsx`
- Create: `frontend/src/pages/AutomationPage.test.tsx`
- Modify: `frontend/src/shell/AppShell.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Write failing React page tests**

Create `frontend/src/pages/AutomationPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { AutomationPage } from "./AutomationPage";

vi.mock("../api/client", () => ({
  api: {
    automationStatus: vi.fn(),
    automationTop10: vi.fn(),
    automationJudgments: vi.fn(),
    runAutomationWeekly: vi.fn(),
    runAutomationDaily: vi.fn(),
    updateAutomationConfig: vi.fn()
  }
}));

function mockAutomationApi() {
  vi.mocked(api.automationStatus).mockResolvedValue({
    config: { enabled: true, top_n: 10, chan_weight: 1, volume_weight: 0.35, weekly_weekday: 5, weekly_time: "09:30", daily_time: "09:45", adjust: "qfq", min_bars: 60, lookback: 120, timezone: "Asia/Shanghai" },
    running: false,
    last_weekly_run: null,
    last_daily_run: null,
    weekly_top10_count: 1,
    latest_daily_judgment_count: 1,
    next_weekly_run: "2026-06-27 09:30",
    next_daily_run: "2026-06-23 09:45"
  });
  vi.mocked(api.automationTop10).mockResolvedValue({
    status: "success",
    generated_at: "2026-06-20T09:30:00+08:00",
    top: [{ rank: 1, code: "688001", name: "华兴源创", exchange: "SSE", composite_score: 70.1, chan_score: 44, volume_score: 74.7, latest_day: "2026-06-18", latest_close: 81.09, chan_signal_title: "缠论三买", chan_signal_action: "buy", volume_entry_ready: false, reason: "三买结构，量能不足" }]
  });
  vi.mocked(api.automationJudgments).mockResolvedValue({
    date: "2026-06-23",
    judgments: [{ code: "688001", name: "华兴源创", exchange: "SSE", judgment: "watch_only", reason: "三买结构仍在，量能未确认", current_score: 70.1, baseline_score: 70.1, latest_day: "2026-06-23", latest_close: 82, chan_signal_title: "缠论三买", volume_entry_ready: false }]
  });
}

test("AutomationPage renders status top10 and daily judgments", async () => {
  mockAutomationApi();

  render(<AutomationPage />);

  expect(await screen.findByText("自动研究任务")).toBeInTheDocument();
  expect(await screen.findByText("688001 华兴源创")).toBeInTheDocument();
  expect(await screen.findByText("三买结构仍在，量能未确认")).toBeInTheDocument();
});

test("AutomationPage manual weekly and daily buttons call automation APIs", async () => {
  const user = userEvent.setup();
  mockAutomationApi();
  vi.mocked(api.runAutomationWeekly).mockResolvedValue({ status: "success", top: [] });
  vi.mocked(api.runAutomationDaily).mockResolvedValue({ judgments: [] });

  render(<AutomationPage />);

  await user.click(await screen.findByRole("button", { name: "手动周扫描" }));
  await user.click(await screen.findByRole("button", { name: "刷新每日判断" }));

  expect(api.runAutomationWeekly).toHaveBeenCalled();
  expect(api.runAutomationDaily).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run failing React tests**

Run:

```bash
cd frontend && npm test -- --run AutomationPage
```

Expected: fail because `AutomationPage` and new API client methods do not exist.

- [ ] **Step 3: Add frontend types and API methods**

Add automation types to `frontend/src/types.ts`:

```ts
export type AutomationConfig = {
  enabled: boolean;
  timezone: string;
  weekly_weekday: number;
  weekly_time: string;
  daily_time: string;
  top_n: number;
  adjust: string;
  min_bars: number;
  lookback: number;
  chan_weight: number;
  volume_weight: number;
};
```

Add `AutomationStatus`, `AutomationRunRecord`, `AutomationRadarCandidate`, `AutomationTop10Response`, and `AutomationJudgmentsResponse` matching backend keys used in the tests.

Add methods in `frontend/src/api/client.ts`:

```ts
automationStatus: () => apiRequest<AutomationStatus>("/api/automation/status"),
automationTop10: () => apiRequest<AutomationTop10Response>("/api/automation/radar/top10"),
automationJudgments: () => apiRequest<AutomationJudgmentsResponse>("/api/automation/judgments"),
runAutomationWeekly: () => apiRequest<AutomationTop10Response>("/api/automation/run-weekly", { method: "POST" }),
runAutomationDaily: () => apiRequest<AutomationJudgmentsResponse>("/api/automation/run-daily", { method: "POST" }),
updateAutomationConfig: (request: Partial<Pick<AutomationConfig, "enabled" | "top_n" | "chan_weight" | "volume_weight">>) =>
  apiRequest<AutomationConfig>("/api/automation/config", { method: "PUT", body: JSON.stringify(request) }),
```

- [ ] **Step 4: Implement AutomationPage and nav**

Create a dense operational page:

- Left panel: enabled switch, topN, chan weight, volume weight, save config button.
- Top metrics: enabled, top10 count, judgment count, running.
- Manual buttons: "手动周扫描" and "刷新每日判断".
- Tables/cards: latest top10 and daily judgments.
- Error state: inline alert with backend message.

Modify `AppShell.tsx`:

- Import `AutomationPage`.
- Import an icon such as `TimerReset` from `lucide-react`.
- Add `{ id: "automation", label: "自动任务", icon: TimerReset }` to the "准备" or "辅助" nav group.
- Render `<AutomationPage />` when `activePage === "automation"`.
- Add `nextStepFor("automation")` to route to `"radar"` or `"data"`.

- [ ] **Step 5: Run React tests green**

Run:

```bash
cd frontend && npm test -- --run AutomationPage
```

Expected: AutomationPage tests pass.

- [ ] **Step 6: Commit Task 6**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts frontend/src/pages/AutomationPage.tsx frontend/src/pages/AutomationPage.test.tsx frontend/src/shell/AppShell.tsx frontend/src/styles.css
git commit -m "feat: add automation workspace"
```

## Task 7: Verification, Browser QA, And Documentation

**Files:**
- Create: `docs/qa/2026-06-20-automation-radar-maintenance-qa.md`
- Modify: `docs/context/pending-features.md` if the pending list mentions this automation slice or needs next-feature handoff.

- [ ] **Step 1: Run targeted backend tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_automation_store.py tests/test_automation_radar.py tests/test_automation_service.py tests/test_automation_scheduler.py tests/test_api_routes.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full backend tests**

Run:

```bash
PYTHONPATH=src python -m pytest
```

Expected: full Python suite passes.

- [ ] **Step 3: Run frontend tests and build**

Run:

```bash
cd frontend && npm test -- --run AutomationPage
cd frontend && npm test -- --run
cd frontend && npm run build
```

Expected: AutomationPage tests, full Vitest suite, and Vite build pass.

- [ ] **Step 4: Browser QA**

Run the app:

```bash
./scripts/run_app.sh
```

Open `http://127.0.0.1:5173`, navigate to `自动任务`, verify:

- Page title and controls render.
- Console has no errors.
- Manual weekly button reaches a clear busy/success/failure state.
- Manual daily button reaches a clear state.
- Top10 and daily judgment tables are visible when backend returns data.
- Mobile viewport has no horizontal overflow.

Save screenshots under:

```text
docs/qa/screenshots/2026-06-20-automation-radar-maintenance-desktop.png
docs/qa/screenshots/2026-06-20-automation-radar-maintenance-mobile.png
```

- [ ] **Step 5: Write QA sedimentation**

Create `docs/qa/2026-06-20-automation-radar-maintenance-qa.md` with:

- Scope and non-goals.
- Commands and pass/fail results.
- Browser screenshot paths or blocker.
- Note that fixed six-stock strategy benchmark was not run because strategy logic did not change.
- Current next recommended follow-up if any.

- [ ] **Step 6: Commit Task 7**

```bash
git add docs/qa/2026-06-20-automation-radar-maintenance-qa.md docs/qa/screenshots docs/context/pending-features.md
git commit -m "docs: record automation radar maintenance qa"
```

## Self-Review

- Spec coverage: Tasks cover models, persistence, full STAR radar scoring, weekly maintenance, daily judgment, scheduler lifecycle, FastAPI routes, React workspace, verification, and QA sedimentation.
- Scope control: No machine-level launch agent, no trading execution, no notifications, and no automatic backtesting are included.
- TDD coverage: Every production module starts with a failing test before implementation.
- Type consistency: The plan consistently uses `AutomationConfig`, `RadarCandidateScore`, `WeeklyRadarResult`, `DailyJudgment`, `AutomationStore`, `AutomationService`, and `AutomationScheduler`.
- Strategy benchmark: The plan states no fixed six-stock benchmark unless implementation changes strategy or radar scoring internals.
