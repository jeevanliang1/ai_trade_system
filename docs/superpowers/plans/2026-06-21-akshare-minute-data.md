# AKShare Minute Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AKShare minute-bar data support across backend data ingestion, managed storage, API/CLI requests, React controls, and existing strategy execution flows.

**Architecture:** Keep `Bar` as the single market-data model and add optional intraday metadata. Make all file and request paths timeframe-aware while preserving `daily` as the default for existing CSVs, fixtures, strategies, and automation.

**Tech Stack:** Python 3.10+, pandas, AKShare optional dependency, FastAPI/Pydantic, React + TypeScript + Vite.

---

### Task 1: Timeframe-Aware Data Model And CSV

**Files:**
- Modify: `src/ai_trade_system/market.py`
- Modify: `src/ai_trade_system/data.py`
- Test: `tests/test_market_data.py`

- [ ] Add failing tests for minute normalization, old CSV compatibility, and new CSV timestamp/timeframe columns.
- [ ] Implement optional `Bar.timestamp` and `Bar.timeframe`.
- [ ] Update CSV read/write to preserve minute metadata and infer `daily` for legacy files.
- [ ] Run `python -m pytest tests/test_market_data.py -q`.

### Task 2: AKShare Minute Fetch And Managed Storage

**Files:**
- Modify: `src/ai_trade_system/data.py`
- Modify: `src/ai_trade_system/data_manager.py`
- Test: `tests/test_data_manager.py`

- [ ] Add failing tests for `1m/5m/15m/30m/60m` fetch routing and timeframe-specific managed paths.
- [ ] Implement `fetch_akshare_bars()` and `fetch_akshare_minute_bars()`.
- [ ] Add `timeframe` to `ManagedDataFile`, `DataUpdateResult`, manifest payloads, status keys, and merge logic.
- [ ] Run `python -m pytest tests/test_market_data.py tests/test_data_manager.py -q`.

### Task 3: API And CLI Plumbing

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `src/ai_trade_system/cli.py`
- Test: `tests/test_api_routes.py`

- [ ] Add failing API tests for downloading minute data and returning timeframe in summaries/managed status.
- [ ] Add `timeframe` to platform settings and watchlist update requests.
- [ ] Route data downloads and managed data updates through `fetch_akshare_bars()`.
- [ ] Add CLI `--timeframe` options to `download` and `data update-watchlist`.
- [ ] Run `python -m pytest tests/test_api_routes.py tests/test_market_data.py tests/test_data_manager.py -q`.

### Task 4: React Minute Controls

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/shell/AppShell.tsx`
- Modify: `frontend/src/pages/DataPage.tsx`
- Modify: `frontend/src/pages/StockConfigPage.tsx`
- Test: `frontend/src/pages/DataPage.test.tsx`
- Test: `frontend/src/shell/AppShell.test.tsx`

- [ ] Add failing frontend tests for selecting `5m` and seeing timeframe-aware CSV paths/buttons.
- [ ] Add `timeframe` to TypeScript settings, bar, data summary, managed file, and update request types.
- [ ] Add a Data Center timeframe selector and update download/status labels.
- [ ] Update managed CSV path helpers and managed-data merge keys to include timeframe.
- [ ] Run frontend targeted tests and build if available.

### Task 5: Docs, Backlog, And Acceptance

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-21-akshare-minute-data.md`

- [ ] Document minute data commands, file shape, and AKShare limitations.
- [ ] Update backlog status and next recommended feature.
- [ ] Run `python -m pytest`.
- [ ] Start the React platform and capture headless Chrome acceptance screenshots.
