# Signal Radar Volume Momentum Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Signal Radar scoring mode that ranks candidates by volume-price momentum while preserving the existing Chan/RSI research ranking as the default.

**Architecture:** Extend the existing `/api/research/signals/batch` request/response contract with `score_mode`, resolve all batch-scan CSVs through `data_manager.data_file_for_stock`, compute a compatible score payload for volume momentum rows, and add a React mode switch plus momentum diagnostics in the Signal Radar table/cards/export.

**Tech Stack:** Python 3, FastAPI/Pydantic, pytest, React + TypeScript + Vitest, existing managed market-data files under `data/market/a_share/{exchange}/{code}/`.

---

## File Structure

- Modify `src/ai_trade_system/api/schemas.py`: add `score_mode` to the batch request.
- Modify `src/ai_trade_system/api/service.py`: resolve canonical managed paths, branch batch scoring by mode, and add volume-momentum row diagnostics.
- Modify `tests/test_api_routes.py`: add failing backend contract/path/ranking tests.
- Modify `frontend/src/types.ts`: add score mode and optional momentum diagnostic types.
- Modify `frontend/src/api/client.ts`: submit `score_mode`.
- Modify `frontend/src/pages/SignalRadarPage.tsx`: add scoring-mode control, mode-specific copy, table/card diagnostics, and CSV fields.
- Modify `frontend/src/pages/SignalRadarPage.test.tsx`: add/update frontend tests for score mode and canonical handoff paths.
- Modify `docs/context/pending-features.md`: move this Signal Radar follow-up into implemented baseline and choose the next strategy iteration.
- Create `docs/qa/2026-06-19-signal-radar-volume-momentum-qa.md`: record verification commands and screenshot path.

## Task 1: Backend Failing Tests

**Files:**
- Modify: `tests/test_api_routes.py`

- [x] Add a test proving a default batch scan response includes `score_mode = "research"`.
- [x] Add a test that writes two catalog stocks to managed CSV paths and verifies `score_mode = "volume_momentum"` ranks the stronger volume-momentum row first.
- [x] Add a test that a missing candidate returns the managed CSV path under `data/market/a_share/{exchange}/{code}/`.
- [x] Add a test that `universe = "local_csv"` filters by managed CSV existence.
- [x] Run `PYTHONPATH=src python -m pytest tests/test_api_routes.py -q` and confirm RED because schemas/service do not yet support the new mode or canonical scan paths.

## Task 2: Backend Implementation

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`

- [x] Add `score_mode: Literal["research", "volume_momentum"] = "research"` to `ResearchSignalBatchRequest`.
- [x] Add a managed-path helper using `data_file_for_stock(stock, adjust=settings.adjust).latest_path`.
- [x] Replace legacy batch-scan path construction with the managed-path helper for scanned rows, missing rows, and local-CSV filtering.
- [x] Keep existing Chan/RSI scoring behavior for `research`.
- [x] Add a volume-momentum scorer with deterministic diagnostics and compatible `score` payload fields.
- [x] Rank volume-momentum scanned rows by `total_score` descending, then append missing rows.
- [x] Run `PYTHONPATH=src python -m pytest tests/test_api_routes.py -q` and confirm GREEN for the new backend tests.

## Task 3: Frontend Failing Tests

**Files:**
- Modify: `frontend/src/pages/SignalRadarPage.test.tsx`

- [x] Update the default scan test to expect `score_mode = "research"`.
- [x] Add a test that selects `量价动量`, submits `score_mode = "volume_momentum"`, and renders momentum/volume diagnostics.
- [x] Update missing-data handoff expectations to the canonical managed CSV path.
- [x] Add or update export coverage so momentum diagnostic CSV headers are present.
- [x] Run `npm test -- SignalRadarPage.test.tsx` from `frontend/` and confirm RED before implementation.

## Task 4: Frontend Implementation

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/SignalRadarPage.tsx`

- [x] Add TypeScript types for `ResearchSignalBatchScoreMode` and optional `momentum` diagnostics.
- [x] Add `score_mode` to `batchResearchSignals` options and payload.
- [x] Add the Signal Radar scoring-mode control with Chinese labels.
- [x] Submit `score_mode` on scan and preserve it in scan history.
- [x] Render `量价动量排行` and diagnostic table/card content when the result is in volume-momentum mode.
- [x] Include momentum diagnostic columns in CSV export.
- [x] Replace old static copy that mentioned `data/<代码>_daily.csv`.
- [x] Run `npm test -- SignalRadarPage.test.tsx` from `frontend/` and confirm GREEN.

## Task 5: Documentation And QA

**Files:**
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-19-signal-radar-volume-momentum-qa.md`

- [x] Add the completed Signal Radar volume-momentum ranking to the implemented baseline.
- [x] Remove the pending evaluation item that this feature resolves.
- [x] Set the next recommended strategy feature to threshold/exit tuning against the fixed 中芯国际 and 五粮液 benchmark fixtures.
- [x] Record test commands and browser screenshot path in QA docs.

## Task 6: Full Verification And Browser Acceptance

- [x] Run `PYTHONPATH=src python -m pytest`.
- [x] Run `npm test` from `frontend/`.
- [x] Run `npm run build` from `frontend/`.
- [x] Start the React + FastAPI app through `./scripts/run_app.sh` if it is not already running.
- [x] Capture a headless/browser screenshot of Signal Radar with the volume-momentum mode visible.
- [x] Run `git status --short` and confirm only intended files changed.
