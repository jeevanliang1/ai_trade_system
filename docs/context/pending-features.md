# Pending Features

Last updated: 2026-06-19

## Purpose

This file is the durable continuation handoff for broad product requests, replicated pages, feature sets, and "continue/next step" prompts. Keep it current before and after implementation work.

## Current Goal

Replicate the screenshot-style AI量化平台 desktop workbench with a React + FastAPI default interface, then continue into practical A-share strategy development. The current implementation is functional enough to start adding strategy templates that run through the existing strategy registry, backtest, paper trading, and React workbench surfaces.

## Completion Grain

Each pending item below should be small enough to finish in one focused implementation turn: edit code, run targeted tests/build, perform browser or screenshot validation when UI is affected, then remove the completed item from this file.

## Already Implemented Baseline

- React + TypeScript + Vite frontend with default `./scripts/run_app.sh` entry.
- FastAPI local API for bootstrap, data, strategies, signals, portfolio preview, backtest, AI research, paper run/events, and risk evaluation.
- Nine React workspaces exist: overview, data center, strategy workshop, portfolio lab, backtest center, signal radar, AI researcher, paper trading, and risk.
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
- AI Researcher evidence grouping is complete for current scope: generated technical evidence, information-side evidence, and risk warnings render as separate evidence groups with their own empty states.
- AI Researcher provider boundary copy is complete for current scope: the page states MockLLMProvider is research-only, never places orders, and cannot bypass risk or execution controls.
- Paper Trading run configuration and status are complete for current scope: the page shows symbol, date range, selected strategy or portfolio mode, cash, commission, slippage, log path, idle/running/complete status, and disables duplicate run clicks while a paper run is active.
- Paper Trading event timeline is complete for current scope: paper events render as a readable chronology with accepted, rejected, service, and equity event styling while retaining the dense order table.
- Paper Trading event filters are complete for current scope: event type, side, and symbol filters apply consistently to the event timeline and order table, with a clear/reset control and visible filtered count.
- Paper Trading log health and reload are complete for current scope: the page shows whether the configured log path is loaded, displays loaded event count and last-event summary, and can reload persisted events through `/api/paper/events`.
- Risk Workspace threshold editor is complete for current scope: the dedicated page mirrors the right inspector fields for risk enablement, drawdown, order cash, cash balance, position shares, and stop-loss mode while preserving `actions.setSettings` as the single update path.
- Risk Workspace deterministic examples are complete for current scope: the page shows an empty example state before backtests and, once metrics exist, renders stable API input rows for max drawdown, trade count, win rate, and risk enablement with the active drawdown threshold.
- Risk Workspace warning guidance is complete for current scope: frontend-only warning mapping adds high/medium/info severity labels plus remediation hints for drawdown, order cash, cash balance, position concentration, disabled, and no-warning states.
- Risk Workspace UI/API hardening is complete for current scope: focused tests cover RiskPage rendering, AppShell risk evaluation failure recovery, and `/api/risk/evaluate` valid plus invalid payload route behavior.
- Responsive platform collapse is complete for current scope: at 390px narrow width the shell uses natural scrolling, navigation wraps, content and inspector stack to one column, and Browser QA confirmed no horizontal overflow.
- Repeatable headless screenshots are complete for current scope: `scripts/capture_app_screenshots.mjs` captures desktop 1440x1024 and narrow 390x844 React platform PNGs after waiting for real app content, with usage documented in `docs/qa/headless-chrome-screenshots.md`.
- First-cut UI cleanup is complete for current scope: the React platform no longer shows nonfunctional top command buttons, fake Strategy Workshop mode tabs, strategy favorite stars, inactive week/month cycle buttons, the unused sidebar collapse control, or inactive right-inspector tabs.
- Strategy metadata localization is complete for current scope: built-in strategies expose Chinese display names and plain-language descriptions through the registry/API, custom strategies get a safe default description, and React strategy/backtest/portfolio/paper/status displays prefer the Chinese name while retaining English class names for source traceability.
- Workbench information architecture cleanup is complete for current scope: side navigation is grouped by workflow stage, the global top bar now summarizes context and navigates to the next workspace instead of running page-owned tasks, and Strategy Workshop focuses on strategy selection, signal preview, research preview, and source editing while Backtest Center remains the owner for full backtest execution and results.
- Strategy parameter guidance is complete for current scope: strategy parameters now expose Chinese labels, plain-language purpose, and simple increase/decrease tuning impact through the registry/API, and the shared React parameter form renders that guidance under each control.
- Stock Configuration Center is complete for current scope: FastAPI persists a local watchlist in `config/watchlist.json`, bootstrap exposes the watchlist and a dynamic two-year default data range, React adds a `股票配置` workspace, and shared watchlist dropdowns update the global stock target through one `selectStock` action.
- Watchlist Data Management is complete for current scope: `data_manager` owns canonical local market-data paths under `data/market/a_share/{exchange}/{code}/`, writes latest CSV plus dated increment CSV snapshots and manifest files, exposes API/CLI batch watchlist updates, and the React stock configuration center shows status plus update controls.
- Market Analysis Strategy Fusion first slice is complete for current scope: backend `ai_trade_system.research` modules generate lightweight Chan plus enhanced RSI previews, FastAPI exposes `/api/research/signals/preview`, and Strategy Workshop can request and render score, blockers, and signal rows.
- Market Analysis Strategy Fusion backtest wrapper is complete for current scope: `ChanRsiResearchStrategy` is a built-in `Strategy` that reuses the research preview semantics, appears in strategy discovery, emits backtestable `Signal` objects, and can run through the existing local backtest engine.
- Chan Structure Strategy first slice is complete for current scope: `research.chan_structure` normalizes contained K-lines, identifies fractals, strokes, simplified pivots, and T2/T3 signals, and `ChanStructureStrategy` exposes those signals as a built-in backtestable strategy with Chinese registry metadata and parameter guidance.
- One-shot React + FastAPI startup preflight is complete for current scope: `scripts/run_all.sh` checks Python/API dependencies, Node/npm/frontend dependencies, installs missing frontend packages, validates ports, reports clear `原因/建议` failures, and `scripts/run_app.sh` remains a compatibility wrapper.
- Signal Radar first slice is complete for current scope: FastAPI exposes `/api/research/signals/batch`, batch scanning ranks local CSV-backed catalog candidates with Chan/RSI research scores, marks missing CSV blockers, and React adds a dedicated `信号雷达` workspace with scan controls, summary metrics, score table, and detail cards.
- Signal Radar scan universe selection is complete for current scope: batch scans accept catalog, local-CSV-only, and current-symbol universes, the API response records the selected universe, and React submits plus displays the active scan range.
- Signal Radar missing-data handoff is complete for current scope: missing CSV result cards expose a prepare-data action that writes the candidate symbol, exchange, and CSV path into shared Data Center settings for follow-up download/load.
- Signal Radar scan history and export is complete for current scope: each successful scan records a compact recent-history row, and the current ranked result can be downloaded as CSV from the radar table header.
- Signal Radar volume-momentum ranking is complete for current scope: batch scans support a `research` / `volume_momentum` scoring mode, use managed A-share CSV paths under `data/market/a_share/{exchange}/{code}/`, render momentum/volume/trend diagnostics, and export the diagnostic fields.
- Signal Radar Chan-structure ranking is complete for current scope: batch scans support `chan_structure` scoring mode, reuse `research.chan_structure`, render fractal/stroke/pivot diagnostics, export structure fields, and preserve local managed CSV-only scanning.
- Strategy Workshop Chan-structure overlays are complete for current scope: `/api/research/signals/preview` returns chart-ready structure payloads, the K-line chart renders fractals, strokes, pivots, and T2/T3 structure markers, and the toolbar can hide or restore the overlay.
- Chan core deepening first slice is complete for current scope: `research.chan_structure` now builds simplified line segments, stroke/segment recursive pivots, segment-energy divergence records, and divergence/confirmation signals, while preview, batch diagnostics, chart overlays, and `ChanStructureStrategy` consume the expanded structure.
- Chan strict segment rules first slice is complete for current scope: `research.chan_structure` now builds non-overlapping stateful segments, extends active segments until confirmed breaks, records start/end/break stroke indexes, and preserves segment-level recursive pivots plus confirmation signals on explicit break/rebuild structures.
- Chan indicator divergence scoring first slice is complete for current scope: segment-level divergences now carry MACD pressure, volume participation, base score, and confirmation score evidence; divergence/confirmation signals use dynamic directional scores; API overlays and frontend types expose the evidence fields.
- Chan structure default threshold tuning is complete for current scope: `ChanStructureStrategy` now defaults `min_signal_score` to `30.0`, filtering lower-confidence 28-point T2/T3 churn while retaining higher-score structure/confirmation signals; fixed 中芯国际 and 五粮液 benchmarks are recorded in QA.
- Chan signal mode controls are complete for current scope: `ChanStructureStrategy` now accepts `signal_mode` values `all`, `confirmation`, and `structure`, exposes Chinese parameter guidance, preserves the default `all`/`30.0` benchmark behavior, and records fixed 中芯国际/五粮液 mode comparisons in QA.
- Chan confirmation lifecycle exits are complete for current scope: `ChanStructureStrategy` now accepts `max_holding_bars`, defaults it to `0` to preserve existing behavior, exits long positions on opposite confirmation signals or optional max-holding time exits, and records fixed 中芯国际/五粮液 benchmarks in QA.
- Chan core deepening second slice is complete for current scope: `research.chan_structure` now extends recursive stroke/segment pivots beyond fixed three-component windows, attaches nearest recursive-pivot context to divergence records and overlays, and marks unconfirmed bottom/top divergence signals as watchable until later repair or structural-break confirmation.
- Chan confirmation T3 consumption is complete for current scope: `ChanStructureStrategy` confirmation mode now admits three-buy/three-sell pivot-retest confirmation signals while keeping two-buy/two-sell in structure mode; fixed 中芯国际 and 五粮液 benchmarks no longer produce zero confirmation-mode trades.
- Chan watch-divergence arming is complete for current scope: `ChanStructureStrategy` now accepts `watch_confirm_bars`, stores qualifying T1 bottom/top divergence watch signals for bounded later confirmation by same-direction confirm/T2/T3 structures, exposes Chinese parameter guidance, and records fixed 中芯国际/五粮液 benchmarks plus disabled-arming comparison in QA.
- Chan same-level lineage is complete for current scope: `research.chan_structure` now assigns segment-level `level`/`sequence_index`/`lineage_id`, emits structured `ResearchSignal.metadata` for T1/T2/T3/confirmation point hierarchy and pivot relationships, exposes segment identity through overlays/frontend types, and records fixed 中芯国际/五粮液 benchmarks in QA.
- Chan point-family filters are complete for current scope: `ChanStructureStrategy` now accepts `allowed_point_types` and `allowed_levels` metadata filters, preserving default `all` behavior while allowing first/second/third buy-sell and segment/stroke/fractal sub-strategy benchmarks on the fixed 中芯国际/五粮液 fixtures.
- Strategy parameter enum controls are complete for current scope: registry/API parameter metadata now exposes allowed `options` plus `multiple`, and React renders `signal_mode` as a select plus `allowed_point_types`/`allowed_levels` as checkbox multi-select controls while preserving string-valued strategy params.
- Chan balanced parameter tuning is complete for current scope: `ChanStructureStrategy` defaults now use `min_signal_score=28.0`, `allowed_point_types=third-buy,third-sell`, and `max_holding_bars=15`, improving the fixed-fixture worst return and drawdown while recording the trade-off against the old higher-sum profile in QA.
- Frontend API error-state coverage is complete for current scope: AppShell task tests now cover failed `/api/data/load`, `/api/backtest`, and `/api/ai/research` flows with visible error copy and cleared busy/run state expectations.
- Core API route coverage is complete for current scope: route tests now pin strategy template creation, strategy source save/readback, paper run plus persisted event reload, and existing portfolio preview contracts.
- JSON error response documentation is complete for current scope: `docs/runbooks/web-console.md` now documents 400/502 string `detail`, 422 validation-list `detail`, and frontend troubleshooting expectations.
- PR delivery checklist documentation is complete for current scope: `docs/runbooks/web-console.md` now covers Python tests, frontend tests/build, API contract checks, pending-list updates, browser screenshots, and live-trading boundary review.
- Engineering hygiene stale-item cleanup is complete for current scope: current `git status` no longer shows `src/ai_trade_system/web/app.py` or `data/000001_daily.csv`, so the old Streamlit split and generated CSV removal reminders were cleared from the pending list.
- Reviewable commit split plan is complete for current scope: `docs/runbooks/reviewable-commit-plan.md` groups the current migration into backend API, React Signal Radar, frontend API failure tests, documentation/rules, and local automation commits with staging and verification commands.
- Signal Radar five-feature QA is complete for current scope: browser-visible acceptance evidence and screenshot path are recorded in `docs/qa/2026-06-14-signal-radar-five-feature-qa.md`.

## Pending

### AI Researcher

No current pending items.

### Paper Trading

No current pending items.

### Risk Workspace

No current pending items.

### Responsive And Visual QA

No current pending items.

### Market Analysis Strategy Fusion

No current pending items.

### API And Error Handling

No current pending items.

### Watchlist Data Management

No current pending items.

### Strategy Development

- Tune `VolumeConfirmedMomentumStrategy` thresholds and exit rules against the fixed 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` three-year benchmark fixtures, then document the comparison results.

### Engineering And Review Hygiene

- Execute the reviewable commit split from `docs/runbooks/reviewable-commit-plan.md` after confirming whether the local launchd automation files should be included in version control.

## Next Recommended Feature

Start with "Strategy Development - Tune `VolumeConfirmedMomentumStrategy` thresholds and exit rules against the fixed 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` three-year benchmark fixtures, then document the comparison results".

## Update Rules

- Add pending work here before starting newly discovered feature work.
- Remove an item from `Pending` after it is completed.
- Keep exactly one `Next Recommended Feature`.
- When the user asks "继续" or "下一步做什么", answer from `Next Recommended Feature` unless newer user instructions supersede it.
