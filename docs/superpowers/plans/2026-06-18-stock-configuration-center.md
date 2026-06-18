# Stock Configuration Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local stock configuration center so the user can maintain watchlist stocks and quickly select them anywhere stock-aware workflows use the current platform symbol.

**Architecture:** Persist the watchlist in a local JSON file behind FastAPI endpoints, hydrate it into `PlatformState`, and expose a single `selectStock` action that updates `symbol`, `exchange`, `csv_path`, strategy params, and clears stale market-derived results. Add a focused React `StockConfigPage` plus a reusable `StockQuickSelect` component used in the top bar and Data Center. Use a dynamic two-year default date range in both backend bootstrap settings and frontend fallback settings.

**Tech Stack:** Python, FastAPI, React, TypeScript, Vite, Vitest, Testing Library, existing CSS.

---

### Task 1: Backend Watchlist And Dynamic Defaults

**Files:**
- Create: `src/ai_trade_system/watchlist.py`
- Modify: `src/ai_trade_system/api/app.py`
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `tests/test_api_routes.py`

- [x] Add failing tests for `GET /api/watchlist`, `PUT /api/watchlist`, bootstrap `watchlist`, and `default_settings(date(2026, 6, 18))`.
- [x] Implement JSON persistence at `config/watchlist.json`, de-dupe by exchange/code, normalize stock fields, and expose service helpers.
- [x] Add FastAPI routes and request schema.
- [x] Verify with `PYTHONPATH=src python -m pytest tests/test_api_routes.py`.

### Task 2: Frontend Shared State And Components

**Files:**
- Create: `frontend/src/components/StockQuickSelect.tsx`
- Create: `frontend/src/components/StockQuickSelect.test.tsx`
- Create: `frontend/src/pages/StockConfigPage.tsx`
- Create: `frontend/src/pages/StockConfigPage.test.tsx`
- Create: `frontend/src/utils/dateRange.ts`
- Create: `frontend/src/utils/dateRange.test.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/pageTypes.ts`
- Modify: `frontend/src/shell/AppShell.tsx`
- Modify: `frontend/src/shell/AppShell.test.tsx`
- Modify: `frontend/src/shell/AppShell.tasks.test.tsx`
- Modify: `frontend/src/pages/DataPage.tsx`
- Modify: `frontend/src/pages/DataPage.test.tsx`
- Modify: `frontend/src/styles.css`

- [x] Add failing tests for dynamic frontend date range, stock config navigation, watchlist add/remove/select behavior, and Data Center watchlist dropdown.
- [x] Add API client methods and state fields for `watchlist`, `setWatchlist`, and `selectStock`.
- [x] Implement `StockQuickSelect` as the shared dropdown.
- [x] Implement `StockConfigPage` with search, add, remove, and set-current actions.
- [x] Wire navigation, top bar dropdown, Data Center dropdown, and stale data clearing through `selectStock`.
- [x] Verify with targeted frontend tests.

### Task 3: Documentation, Verification, And Browser QA

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/context/pending-features.md`

- [x] Record the durable rule that stock-aware controls should use the shared watchlist selector and `selectStock` action.
- [x] Move the pending item into the implemented baseline and restore the reviewable commit split as the next recommended feature.
- [x] Run `PYTHONPATH=src python -m pytest`, `npm test -- --run`, `npm run build`, `./scripts/run_all.sh --check`, and `git diff --check`.
- [x] Capture desktop/mobile screenshots and Browser QA for watchlist add/select behavior plus console health.
