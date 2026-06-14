# Pending Features

Last updated: 2026-06-14

## Purpose

This file is the durable continuation handoff for broad product requests, replicated pages, feature sets, and "continue/next step" prompts. Keep it current before and after implementation work.

## Current Goal

Replicate the screenshot-style AI量化平台 desktop workbench with a React + FastAPI default interface. The current implementation is functional but still below the screenshot target in density, workflow depth, right-side AI/risk behavior, result tables, and end-to-end polish.

## Completion Grain

Each pending item below should be small enough to finish in one focused implementation turn: edit code, run targeted tests/build, perform browser or screenshot validation when UI is affected, then remove the completed item from this file.

## Already Implemented Baseline

- React + TypeScript + Vite frontend with default `./scripts/run_app.sh` entry.
- FastAPI local API for bootstrap, data, strategies, signals, portfolio preview, backtest, AI research, paper run/events, and risk evaluation.
- Eight React workspaces exist: overview, data center, strategy workshop, portfolio lab, backtest center, AI researcher, paper trading, and risk.
- Screenshot-like shell exists with left navigation, top command bar, center work area, right inspector, and bottom status bar.
- Strategy workshop has strategy list, parameter form, signal preview, K-line, volume, basic result metrics, and source editor state.
- K-line chart has red-rise/green-fall candlesticks, MA20/MA60 overlays, visible volume bars, and no initial chart animation flicker.
- Strategy Workshop screenshot-fidelity pass has a denser command/status shell, strategy/组合/回测 segmented mode state, searchable compact strategy list, grouped parameter sections with AI/risk/trade controls, K-line toolbar, drawdown chart, and metrics comparison table.
- Right AI and risk inspector now has information-side summary rows, waiting/bullish/bearish/neutral AI opinion states, an AI scoring toggle bound to portfolio scoring, editable risk thresholds, stop-loss mode, risk enablement, and a pass/fail status footer.
- Chart and backtest depth is complete for Strategy Workshop: K-line and volume charts share an ECharts zoom group, buy/sell signal markers carry tooltip detail payloads, backtest metrics include benchmark return, excess return, annual volatility, Sharpe-like ratio, and profit factor, and the result area has six interactive tabs plus a dense strategy/cash/long-only comparison table.
- Data Center module is complete for current scope: `/api/stocks?query=` search dropdown, automatic symbol/exchange/CSV-path selection, date and CSV-path validation, stale data clearing when the data target changes, CSV health metrics, load/download busy state, retry copy, and demo-data fallback.
- Strategy Editing module is complete for current scope: user strategies render in a safer line-numbered source editor, template creation refreshes and selects the new strategy, create/save failures appear inline in Strategy Workshop, and numeric parameter drafts reject empty/invalid values before preview/API calls.
- Portfolio Lab allocation editing is complete for current scope: allocation rows can be added, removed, enabled/disabled, assigned to a strategy, edited with raw weights, and summarized as normalized enabled weights.
- Portfolio Lab mode explanations are complete for current scope: weighted vote, equal vote, and first active modes show concise semantics, best-fit usage guidance, and active-mode detail that updates when mode buttons change.
- Portfolio Lab signal breakdown is complete for current scope: portfolio preview responses expose per-allocation contribution rows, and the React page shows score totals plus each strategy's action, contribution score, adoption state, weight, volume, and reason after preview.
- Portfolio Lab AI-adjust preview is complete for current scope: portfolio preview responses expose AI adjustment metadata plus per-allocation base/adjusted weights, and the React page shows before/after weight deltas when AI scoring is enabled.
- Backtest Center progress state is complete for current scope: backtest runs track the active mode, disable duplicate run clicks while pending, and show a running/idle status strip in the Backtest Center panel.
- Backtest Center run configuration summary is complete for current scope: the results column shows symbol/exchange, date range, selected run mode, selected strategy or portfolio vote mode, initial cash, commission, and slippage.
- Backtest Center export actions are complete for current scope: trades, metrics, and equity curve can be downloaded from the result column after a backtest result exists.
- Backtest Center empty/error states are complete for current scope: missing CSV or unloaded行情, missing single-strategy selection, and invalid portfolio allocation now show explicit blockers, disable the page run button, and explain the result empty state.
- AI Researcher information note editor is complete for current scope: the single plain note area is now multiple editable recent-note rows with add/remove controls, and research generation submits only non-empty trimmed notes.
- AI Researcher prompt snapshot is complete for current scope: successful research responses persist the generated prompt in platform state, and the AI Researcher page shows it in a collapsible audit panel.

## Pending

### AI Researcher

- Show AI evidence grouped into technical, information-side, and risk warnings.
- Add provider boundary copy that clearly states MockLLMProvider is research-only and never places orders.

### Paper Trading

- Add paper run configuration summary and busy/complete status.
- Add paper event timeline with accepted/rejected order styling.
- Add filters for event type, side, and symbol.
- Add log file path health check and "load latest events" action.

### Risk Workspace

- Add a full risk threshold editor page mirroring the right inspector fields.
- Add deterministic risk evaluation examples using current backtest metrics.
- Add risk warning severity levels and remediation hints.
- Add tests for risk UI rendering and API error handling.

### Responsive And Visual QA

- Fix narrow viewport behavior for the three-column platform: nav, center chart, and inspector should collapse predictably without overlapping.
- Add a repeatable headless screenshot script for desktop 1440x1024 and narrow mobile width.
- Add visual regression notes or baseline screenshots under `docs/qa/` after each major fidelity pass.

### API And Error Handling

- Add frontend error-state tests for failed `/api/data/load`, `/api/backtest`, and `/api/ai/research`.
- Add API tests for strategy template creation, strategy source save, paper run/events, and portfolio preview.
- Add JSON error response shape documentation in `docs/runbooks/web-console.md`.

### Engineering And Review Hygiene

- Split the current large migration into reviewable commits: core capability/API, React frontend, docs/rules, and Streamlit legacy changes.
- Decide whether the large `src/ai_trade_system/web/app.py` Streamlit changes belong in this migration or should be split into a legacy-console commit.
- Remove generated `data/000001_daily.csv` from the intended commit unless the PR explicitly wants a demo CSV fixture.
- Add a short PR checklist covering Python tests, frontend tests, build, audit, Browser QA, and headless screenshot path.

## Next Recommended Feature

Start with "AI Researcher - Show AI evidence grouped into technical, information-side, and risk warnings". This is the best next task because prompt auditability is now visible, and grouped evidence is the next step for making the AI research output easier to inspect and trust.

## Update Rules

- Add pending work here before starting newly discovered feature work.
- Remove an item from `Pending` after it is completed.
- Keep exactly one `Next Recommended Feature`.
- When the user asks "继续" or "下一步做什么", answer from `Next Recommended Feature` unless newer user instructions supersede it.
