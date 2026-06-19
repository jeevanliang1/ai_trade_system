# Signal Radar STAR Auto Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class STAR Market scanning to Signal Radar with optional automatic local qfq data maintenance before scanning.

**Architecture:** Extend the existing research batch API instead of adding a new scan service. Candidate selection gains a `star` universe, data maintenance reuses `data_manager.update_stock_data`, and frontend Signal Radar sends `auto_update_data` plus renders returned update status. The implementation remains synchronous and bounded by a raised scan limit of 300.

**Tech Stack:** Python FastAPI/Pydantic, existing `data_manager`, pytest, React + TypeScript + Vite, Vitest.

---

## File Map

- Modify `src/ai_trade_system/api/schemas.py`: add `star` universe, `auto_update_data`, `if_stale`, optional `adjust`, and raise limit bound to 300.
- Modify `src/ai_trade_system/api/service.py`: add STAR candidate resolver, optional per-candidate data update before scanning, row-level `data_status`, and response-level `data_update`.
- Modify `frontend/src/types.ts`: add `star` universe and batch data update response types.
- Modify `frontend/src/api/client.ts`: send `auto_update_data`, `if_stale`, optional `adjust`.
- Modify `frontend/src/pages/SignalRadarPage.tsx`: add STAR range option, auto-update toggle, 300 limit, summary metrics, row/card/export data status.
- Modify `tests/test_api_routes.py`: backend API behavior tests.
- Modify `frontend/src/pages/SignalRadarPage.test.tsx` or nearest existing AppShell page tests: frontend request/render tests.
- Update docs/QA after implementation.

## Task 1: Backend STAR Universe

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Test: `tests/test_api_routes.py`

- [ ] **Step 1: Write failing tests**

Add tests that monkeypatch `service.load_stock_catalog` and call `/api/research/signals/batch` with `universe="star"`.

Expected behavior:

```python
def test_research_signal_batch_star_universe_filters_star_candidates(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        service,
        "load_stock_catalog",
        lambda: [
            StockInfo("688001", "华兴源创", "SSE"),
            StockInfo("688981", "中芯国际", "SSE"),
            StockInfo("600000", "浦发银行", "SSE"),
            StockInfo("300750", "宁德时代", "SZSE"),
        ],
    )

    response = client.post("/api/research/signals/batch", json={
        "settings": _settings_payload(tmp_path),
        "query": "",
        "limit": 100,
        "min_bars": 60,
        "lookback": 120,
        "universe": "star",
        "score_mode": "volume_momentum",
    })

    assert response.status_code == 200
    payload = response.json()
    assert [row["code"] for row in payload["rows"]] == ["688001", "688981"]
    assert payload["scanned"] == 2
```

Also add a query narrowing test:

```python
def test_research_signal_batch_star_universe_honors_query(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(service, "load_stock_catalog", lambda: [
        StockInfo("688001", "华兴源创", "SSE"),
        StockInfo("688981", "中芯国际", "SSE"),
    ])

    response = client.post("/api/research/signals/batch", json={
        "settings": _settings_payload(tmp_path),
        "query": "68898",
        "limit": 100,
        "min_bars": 60,
        "lookback": 120,
        "universe": "star",
        "score_mode": "volume_momentum",
    })

    assert response.status_code == 200
    assert [row["code"] for row in response.json()["rows"]] == ["688981"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_research_signal_batch_star_universe_filters_star_candidates tests/test_api_routes.py::test_research_signal_batch_star_universe_honors_query -q
```

Expected: fails because `star` is not a valid universe.

- [ ] **Step 3: Implement minimal backend universe support**

In `schemas.py`, update:

```python
limit: int = Field(default=20, ge=1, le=300)
universe: Literal["catalog", "local_csv", "current", "star"] = "catalog"
```

In `service.py`, update `_research_batch_candidates`:

```python
if request.universe == "star":
    catalog = load_stock_catalog()
    star_candidates = [stock for stock in catalog if stock.exchange == "SSE" and stock.code.startswith("688")]
    return search_stock_catalog(star_candidates, request.query, request.limit)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run the same pytest command. Expected: both tests pass.

## Task 2: Backend Auto Data Maintenance

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Test: `tests/test_api_routes.py`

- [ ] **Step 1: Write failing tests**

Add tests that monkeypatch `service.update_stock_data` and verify request/response behavior.

Expected behavior:

```python
def test_research_signal_batch_auto_updates_star_data_before_scan(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    csv_path = tmp_path / "data" / "market" / "a_share" / "SSE" / "688001" / "688001_SSE_daily_qfq_latest.csv"
    monkeypatch.setattr(service, "load_stock_catalog", lambda: [StockInfo("688001", "华兴源创", "SSE")])

    def fake_update(stock, *, start_date, end_date, adjust, if_stale, root=None, fetcher=None):
        bars = _sample_bars("688001", "SSE", count=80)
        write_bars_csv(bars, csv_path)
        return DataUpdateResult(
            code="688001",
            name="华兴源创",
            exchange="SSE",
            adjust=adjust,
            status="updated",
            requested_start=start_date,
            requested_end=end_date,
            fetched_start=start_date,
            fetched_end=end_date,
            fetched_rows=len(bars),
            latest_rows=len(bars),
            latest_start=bars[0].trading_day.isoformat(),
            latest_end=bars[-1].trading_day.isoformat(),
            latest_path=csv_path.as_posix(),
            increment_path=None,
            message="updated 80 bars",
        )

    monkeypatch.setattr(service, "update_stock_data", fake_update)

    response = client.post("/api/research/signals/batch", json={
        "settings": _settings_payload(tmp_path),
        "query": "",
        "limit": 100,
        "min_bars": 20,
        "lookback": 60,
        "universe": "star",
        "score_mode": "volume_momentum",
        "auto_update_data": True,
        "if_stale": True,
    })

    payload = response.json()
    assert response.status_code == 200
    assert payload["data_update"]["enabled"] is True
    assert payload["data_update"]["updated"] == 1
    assert payload["rows"][0]["data_status"]["status"] == "updated"
    assert payload["rows"][0]["status"] == "scanned"
```

Add failure path:

```python
def test_research_signal_batch_auto_update_failure_returns_blocker(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(service, "load_stock_catalog", lambda: [StockInfo("688001", "华兴源创", "SSE")])
    monkeypatch.setattr(service, "update_stock_data", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("network down")))

    response = client.post("/api/research/signals/batch", json={
        "settings": _settings_payload(tmp_path),
        "query": "",
        "limit": 100,
        "min_bars": 20,
        "lookback": 60,
        "universe": "star",
        "score_mode": "volume_momentum",
        "auto_update_data": True,
    })

    payload = response.json()
    assert response.status_code == 200
    assert payload["data_update"]["failed"] == 1
    assert payload["rows"][0]["status"] == "missing_data"
    assert payload["rows"][0]["data_status"]["status"] == "failed"
    assert any(blocker["code"] == "DATA_UPDATE_FAILED" for blocker in payload["rows"][0]["blockers"])
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_research_signal_batch_auto_updates_star_data_before_scan tests/test_api_routes.py::test_research_signal_batch_auto_update_failure_returns_blocker -q
```

Expected: fails because request fields and response data update metadata do not exist.

- [ ] **Step 3: Implement data update support**

In `schemas.py`, add:

```python
auto_update_data: bool = False
if_stale: bool = True
adjust: str | None = None
```

In `service.py`, import `DataUpdateResult` and `update_stock_data` from `data_manager`.

Add helper:

```python
def _update_batch_candidate_data(request: ResearchSignalBatchRequest, candidates: list[StockInfo]) -> dict[str, Any]:
    adjust = request.adjust or request.settings.adjust
    files = []
    updated = skipped = failed = 0
    statuses = {}
    for stock in candidates:
        try:
            result = update_stock_data(
                stock,
                start_date=request.settings.start_date,
                end_date=request.settings.end_date,
                adjust=adjust,
                if_stale=request.if_stale,
            )
            payload = result.as_dict()
        except Exception as exc:
            data_file = data_file_for_stock(stock, adjust=adjust)
            payload = {
                "code": stock.code,
                "name": stock.name,
                "exchange": stock.exchange,
                "adjust": adjust,
                "status": "failed",
                "requested_start": request.settings.start_date,
                "requested_end": request.settings.end_date,
                "latest_path": data_file.latest_path.as_posix(),
                "latest_rows": 0,
                "latest_start": None,
                "latest_end": None,
                "message": str(exc),
            }
        files.append(payload)
        statuses[payload["code"]] = _batch_data_status(payload)
        if payload["status"] == "updated":
            updated += 1
        elif payload["status"] == "skipped":
            skipped += 1
        else:
            failed += 1
    return {
        "summary": {
            "enabled": True,
            "total": len(candidates),
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "adjust": adjust,
            "start_date": request.settings.start_date,
            "end_date": request.settings.end_date,
        },
        "statuses": statuses,
        "files": files,
    }
```

Attach `data_status` to every row. If update failed, add blocker `DATA_UPDATE_FAILED`.

- [ ] **Step 4: Run tests to verify GREEN**

Run the same pytest command. Expected: both tests pass.

## Task 3: Frontend STAR Controls

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/SignalRadarPage.tsx`
- Test: existing frontend page test file for Signal Radar or AppShell

- [ ] **Step 1: Write failing frontend tests**

Add a test that renders Signal Radar, selects `科创板`, enables auto update, runs scan, and asserts the request body includes:

```json
{
  "universe": "star",
  "auto_update_data": true,
  "if_stale": true
}
```

Add a render test with mocked response:

```json
{
  "data_update": {
    "enabled": true,
    "total": 2,
    "updated": 1,
    "skipped": 1,
    "failed": 0,
    "adjust": "qfq",
    "start_date": "20230620",
    "end_date": "20260620"
  }
}
```

Assert the page shows updated/skipped/failed metrics.

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
cd frontend && npm test -- --run SignalRadarPage
```

Expected: fails because the new option/toggle/status UI is absent.

- [ ] **Step 3: Implement frontend controls and render state**

In `types.ts`, update universe union and response types.

In `api/client.ts`, extend `batchResearchSignals` options.

In `SignalRadarPage.tsx`:

- Add `const [autoUpdateData, setAutoUpdateData] = useState(false);`
- Add `<option value="star">科创板</option>`
- Change scan number clamp max from 50 to 300.
- Add a switch or checkbox for `扫描前自动更新数据`.
- Include `auto_update_data: autoUpdateData, if_stale: true` in API call.
- Render update metrics if `result.data_update?.enabled`.
- Render `row.data_status` in detail cards and CSV export.

- [ ] **Step 4: Run frontend tests to verify GREEN**

Run:

```bash
cd frontend && npm test -- --run SignalRadarPage
```

Expected: tests pass.

## Task 4: QA, Docs, and Full Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-20-signal-radar-star-auto-data.md`

- [ ] **Step 1: Update docs**

Document:

- Signal Radar now supports STAR Market scope.
- Auto update uses managed qfq paths and manifest/increment storage.
- Scan limit is 300.
- No live trading behavior is added.

- [ ] **Step 2: Run backend verification**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py tests/test_data_manager.py tests/test_stock_catalog.py -q
PYTHONPATH=src python -m pytest
```

Expected: all pass.

- [ ] **Step 3: Run frontend verification**

Run:

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

Expected: all pass and build succeeds.

- [ ] **Step 4: Browser QA**

Start app:

```bash
./scripts/run_app.sh
```

Capture Signal Radar screenshots after selecting `科创板` and showing `扫描前自动更新数据`.

Save:

- `docs/qa/screenshots/2026-06-20-signal-radar-star-auto-data_desktop_1440.png`
- `docs/qa/screenshots/2026-06-20-signal-radar-star-auto-data_mobile_390.png`

- [ ] **Step 5: Write QA record**

Create `docs/qa/2026-06-20-signal-radar-star-auto-data.md` with commands, results, API/UI behavior, and screenshot paths.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/architecture.md docs/context/pending-features.md docs/qa/2026-06-20-signal-radar-star-auto-data.md docs/qa/screenshots/2026-06-20-signal-radar-star-auto-data_*.png frontend/src src tests
git commit -m "feat: add star signal radar auto data"
```
