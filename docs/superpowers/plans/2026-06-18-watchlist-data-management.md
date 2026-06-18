# Watchlist Data Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add local file-system data management for self-selected stocks so watchlist data can be updated in batches, stored with stable CSV naming, and inspected from the React stock configuration center.

**Architecture:** Create a focused backend `data_manager` module that owns canonical CSV paths, increment snapshot paths, manifest JSON, stale checks, and update orchestration. FastAPI and CLI call this module; React only displays status and triggers batch updates through API methods. The first version supports application-level daily refresh and CLI automation hooks but does not commit machine-local scheduler files.

**Tech Stack:** Python, FastAPI, AKShare-backed data fetcher abstraction, CSV/JSON files, React, TypeScript, Vitest, Testing Library, existing shell scripts and browser screenshot tooling.

---

### Task 1: Backend Managed Data Files

**Files:**
- Create: `src/ai_trade_system/data_manager.py`
- Create: `tests/test_data_manager.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `tests/test_api_routes.py`

- [x] Add failing tests for canonical paths, increment snapshot paths, manifest contents, merge-by-trading-day behavior, stale watchlist status, and batch watchlist update results.
- [x] Implement `ManagedDataFile`, `DataUpdateResult`, `data_file_for_stock`, `load_manifest`, `list_watchlist_data_status`, and `update_watchlist_data`.
- [x] Refactor service data download to return data-management metadata when available.
- [x] Verify with `PYTHONPATH=src python -m pytest tests/test_data_manager.py tests/test_api_routes.py`.

### Task 2: API And CLI Entry Points

**Files:**
- Modify: `src/ai_trade_system/api/app.py`
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/cli.py`
- Modify: `tests/test_api_routes.py`
- Modify: `tests/test_cli_stocks.py`

- [x] Add failing route tests for `GET /api/data/managed` and `POST /api/data/update-watchlist`.
- [x] Add failing CLI test for `ai-trade data update-watchlist --end 20260618 --if-stale`.
- [x] Implement schema, API routes, and CLI output with per-stock status lines.
- [x] Verify targeted API and CLI tests.

### Task 3: React Stock Configuration Data Controls

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/pageTypes.ts`
- Modify: `frontend/src/shell/AppShell.tsx`
- Modify: `frontend/src/pages/StockConfigPage.tsx`
- Modify: `frontend/src/pages/StockConfigPage.test.tsx`
- Modify: `frontend/src/shell/AppShell.tasks.test.tsx`
- Modify: `frontend/src/styles.css`

- [x] Add failing tests for data-status hydration, stock configuration status rendering, update-all action, and canonical CSV path selection.
- [x] Add API methods and state fields for managed data files.
- [x] Wire `selectStock` to `data/market/a_share/{exchange}/{code}/{code}_{exchange}_daily_{adjust}_latest.csv`.
- [x] Render data status cards and an update-all button in Stock Configuration Center.
- [x] Verify targeted frontend tests.

### Task 4: Documentation, Verification, And Browser QA

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `AGENTS.md`
- Modify: `docs/context/pending-features.md`

- [ ] Document managed data directory and update command.
- [ ] Move the pending item into the implemented baseline and restore the reviewable commit split as the next recommended feature.
- [ ] Run `PYTHONPATH=src python -m pytest`, `cd frontend && npm test -- --run`, `cd frontend && npm run build`, `./scripts/run_all.sh --check`, and `git diff --check`.
- [ ] Capture browser-visible Stock Configuration Center QA plus repeatable desktop/mobile screenshots.
