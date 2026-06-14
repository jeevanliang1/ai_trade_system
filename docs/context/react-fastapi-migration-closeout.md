# React FastAPI Migration Closeout

Date: 2026-06-13

## Purpose

This note captures the recommended commit boundary for the React + FastAPI migration so the large UI/API change can be reviewed without accidentally mixing unrelated local work.

## Recommended Commit Scope

Include these areas together because they form one working platform surface:

- FastAPI API: `src/ai_trade_system/api/` and `tests/test_api_routes.py`.
- React frontend: `frontend/`.
- Runtime scripts: `scripts/run_api.sh`, `scripts/run_frontend.sh`, `scripts/run_app.sh`, and the `.venv` fallback in `scripts/run_web.sh`.
- Python dependencies: `pyproject.toml` API optional dependencies.
- Core modules used by the API and Web surfaces: `analytics`, `indicators`, `llm`, `portfolio`, `risk`, `stock_catalog`, and Web view-model helpers.
- Stock catalog fixture: `data/a_share_stocks.csv`.
- Documentation and AI close-out rules that define React as the default surface: `README.md`, `docs/architecture.md`, `docs/runbooks/web-console.md`, `docs/context/current-system-state.md`, `docs/qa/headless-chrome-screenshots.md`, and `AGENTS.md`.

## Review Before Including

Review these separately before staging if the goal is a minimal migration commit:

- `docs/superpowers/`: planning artifacts and generated design references; useful for process history, not required at runtime.
- Large Streamlit changes under `src/ai_trade_system/web/app.py`: split into a separate commit unless the PR intentionally includes the legacy console upgrade. The React + FastAPI migration only needs shared helpers such as `src/ai_trade_system/web/view_models.py`.
- Sedimentation-rule edits under `docs/auto-sedimentation-skill.md` and `docs/rules/auto-sedimentation-closeout.md`: keep if the repo should permanently require headless Chrome screenshots at close-out.

## Dependency Cleanup

- `MockLLMProvider` now uses timezone-aware UTC timestamps and preserves the existing `Z` suffix response shape.
- Frontend dev tooling was upgraded to Vite 8 and `@vitejs/plugin-react` 6 to clear the `esbuild` audit finding.
- Vite 8 requires function-form `manualChunks`; object-form chunk maps fail during production builds.

## Fresh Verification

The following checks passed on this workspace:

- `python -m pytest`: 50 passed.
- `npm --prefix frontend test`: 5 passed.
- `npm --prefix frontend run build`: passed.
- `npm --prefix frontend audit --audit-level=high`: 0 vulnerabilities.
