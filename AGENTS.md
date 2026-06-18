# AGENTS.md

## Project Overview

- This repository is a self-hosted A-share quantitative trading system scaffold.
- Current scope: public market data normalization, custom strategy interface, local backtesting, CSV replay paper trading, and future broker/vn.py gateway extension points.
- Do not add live trading behavior by default. Live A-share gateways remain opt-in until a broker interface and operational rules are explicitly defined.

## Key Documents

- `README.md`: project setup and CLI usage.
- `docs/architecture.md`: current module map, data flow, and vn.py migration direction.
- `strategies/README.md`: custom strategy placement and strategy-core guidance.
- `docs/README.md`: AI documentation index.
- `docs/auto-sedimentation-skill.md`: required task close-out documentation workflow.
- `docs/rules/auto-sedimentation-closeout.md`: mandatory sedimentation close-out rule.
- `docs/rules/feature-backlog-continuation.md`: mandatory feature decomposition and continuation backlog rule.
- `docs/rules/strategy-benchmark-backtest.md`: mandatory fixed-stock benchmark backtest rule for strategy changes.
- `docs/context/pending-features.md`: durable pending feature list and next recommended feature.
- `docs/qa/headless-chrome-screenshots.md`: required headless Chrome screenshot acceptance workflow.

## Product And Engineering Rules

- Keep the strategy core lightweight and pure Python unless a task explicitly targets a framework adapter.
- Preserve the direction: validate strategies with public data, backtests, and paper trading before any live broker integration.
- Treat risk controls, paper execution behavior, and event logs as user-facing trading-system behavior; update tests when changing them.
- Prefer extending `src/ai_trade_system` modules and existing CLI patterns over adding new top-level systems.
- Treat the React + FastAPI platform (`./scripts/run_app.sh`, `http://localhost:5173`) as the default browser surface. Streamlit (`./scripts/run_web.sh`, `http://localhost:8501`) is legacy unless a task explicitly targets it.
- Do not leave decorative or nonfunctional controls in the React platform. A visible button/tab/switch should either be wired to useful behavior, shown as read-only state, or removed until implemented.
- User-facing strategy displays should prefer Chinese `display_name` plus a plain-language description, while preserving the English class name where source traceability matters.
- User-facing strategy parameters should include a Chinese label, plain-language purpose, and simple tuning impact for increasing or decreasing the value when the parameter semantics allow it.
- Stock-aware React controls should use the shared watchlist selector and `selectStock` action so `symbol`, `exchange`, `csv_path`, strategy params, portfolio params, and stale market-derived results stay synchronized.
- Watchlist market-data workflows should use `src/ai_trade_system/data_manager.py` and canonical paths under `data/market/a_share/{exchange}/{code}/`; do not reintroduce ad hoc `data/{code}_daily.csv` defaults for stock-aware flows. Product code may expose CLI/API update hooks, but committing machine-local scheduling such as launchd still requires owner confirmation.
- Every strategy modification or new strategy must run fixed-stock benchmark backtests before final delivery, using local qfq fixtures for 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` over `20230619` to `20260619` under `data/market/a_share/{exchange}/{code}/`; record comparable results under `docs/qa/`.
- Global shell controls should summarize current context or navigate to the next workflow step; page-owned execution actions such as running backtests, scans, AI research, risk checks, or paper trading should live inside their responsible workspace.

## Required Context Before Development

- Read `README.md`, `docs/architecture.md`, and any relevant files under `docs/` before non-trivial changes.
- For strategy work, also read `strategies/README.md` and `src/ai_trade_system/strategy.py`.
- For CLI, data, backtest, paper trading, or gateway work, inspect the matching module under `src/ai_trade_system/` and existing tests under `tests/`.

## AI Coding Collaboration Rules

- Make small, scoped changes that follow existing module boundaries.
- Do not overwrite unrelated user changes.
- Run `python -m pytest` after code changes unless the task is docs-only or the user gives a narrower verification command.
- For docs-only changes, run lightweight file existence/non-empty checks relevant to the changed docs.
- Report any verification command that was not run and why.
- At task close-out, provide a headless Chrome screenshot for user acceptance whenever a browser-renderable project surface is available; if no such surface can be captured, report the exact reason.
- When the user gives a persona, requirement, page/function to replicate, or asks to continue broad product work, first decompose the work into concrete feature items and update `docs/context/pending-features.md`. Remove completed items from the pending list, add newly discovered pending work before starting it, and keep exactly one next recommended feature recorded there.
- When the user asks to "继续完成项目" or similar, follow `docs/rules/feature-backlog-continuation.md` five-feature continuation mode: complete five meaningful backlog features in sequence when feasible, update pending items after each feature, run targeted verification per feature, and run broader verification only after the batch.

## AI Auto Sedimentation Rules

- At every accepted task wrap-up, run the auto-sedimentation audit in `docs/auto-sedimentation-skill.md`.
- Capture durable project knowledge under the smallest appropriate `docs/` file; avoid duplicating facts already obvious from code.
- Any rule that changes future AI default behavior must be mirrored here in concise form.
- Close-out evidence should include a headless Chrome screenshot path or an explicit not-applicable/blocker note.
- For broad product/page/function work, sediment pending features in `docs/context/pending-features.md`; final responses must mention pending-list changes and the recorded next recommended feature.
- Final responses must include either `沉淀：已更新 ...` or `沉淀：无需新增文档，原因是 ...`.
