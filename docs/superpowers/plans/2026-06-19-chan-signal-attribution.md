# Chan Signal Attribution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add backtest signal attribution by Chan family without changing trading outcomes.

**Architecture:** Backtest records accepted-trade attribution beside existing `Trade` records. Analytics groups attributed trades into entry and exit family summaries, and the API/frontend expose those summaries on the existing backtest result surface.

**Tech Stack:** Python dataclasses, pytest, FastAPI TestClient, React + TypeScript, Vitest.

---

### Task 1: Backtest Attribution Records

**Files:**
- Modify: `src/ai_trade_system/backtest.py`
- Test: `tests/test_backtest_and_paper.py`

- [ ] **Step 1: Write failing test**

Add a local strategy in `tests/test_backtest_and_paper.py` that emits one buy and one sell with Chan-style reasons. Assert `result.trade_attributions` contains both accepted trades with `signal_reason`, `signal_family`, and `signal_label`.

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python -m pytest tests/test_backtest_and_paper.py::test_backtest_records_signal_attribution_for_accepted_trades -q`

Expected: fail because `BacktestResult` has no `trade_attributions`.

- [ ] **Step 3: Implement minimal backtest support**

Add `TradeAttribution` and `BacktestResult.trade_attributions`. In `run_backtest`, call the broker, check `OrderResult.accepted`, read the appended `Trade`, classify the source signal reason, and append a `TradeAttribution`.

- [ ] **Step 4: Run green test**

Run: `PYTHONPATH=src python -m pytest tests/test_backtest_and_paper.py::test_backtest_records_signal_attribution_for_accepted_trades -q`

Expected: pass.

### Task 2: Attribution Analytics

**Files:**
- Modify: `src/ai_trade_system/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write failing classifier and calculator tests**

Assert Chan reason strings classify into `t1_divergence`, `t2`, `t3`, `divergence_confirm`, `time_exit`, and `other`. Build attributed buy/sell trades and assert grouped summary entry/exit PnL, win rate, profit factor, and realized drawdown.

- [ ] **Step 2: Run red tests**

Run: `PYTHONPATH=src python -m pytest tests/test_analytics.py -q`

Expected: fail because the analytics helpers do not exist.

- [ ] **Step 3: Implement analytics helpers**

Add `SignalAttributionRow`, `classify_signal_family`, `calculate_signal_attribution`, FIFO closed-lot matching, proportional commission allocation, and cumulative realized drawdown calculation.

- [ ] **Step 4: Run green tests**

Run: `PYTHONPATH=src python -m pytest tests/test_analytics.py -q`

Expected: pass.

### Task 3: API Contract

**Files:**
- Modify: `src/ai_trade_system/api/service.py`
- Test: `tests/test_api_routes.py`

- [ ] **Step 1: Write failing API test**

Extend the demo backtest route test to assert `trade_attributions` and `signal_attribution` exist and contain family labels.

- [ ] **Step 2: Run red test**

Run: `PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_demo_data_backtest_ai_and_risk_flow -q`

Expected: fail because the fields are absent.

- [ ] **Step 3: Implement API serialization**

Import `calculate_signal_attribution` and include serialized `result.trade_attributions` plus grouped `signal_attribution` in `run_backtest_request`.

- [ ] **Step 4: Run green test**

Run: `PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_demo_data_backtest_ai_and_risk_flow -q`

Expected: pass.

### Task 4: React Backtest Attribution Table

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/BacktestPage.tsx`
- Test: `frontend/src/pages/BacktestPage.test.tsx`

- [ ] **Step 1: Write failing frontend test**

Add `signal_attribution` and `trade_attributions` to fixture `BacktestResponse`, render `BacktestResultPanel`, and assert `信号归因`, `T3三买三卖`, and numeric PnL values are visible.

- [ ] **Step 2: Run red test**

Run: `cd frontend && npm test -- --run BacktestPage.test.tsx`

Expected: fail because the panel is missing.

- [ ] **Step 3: Implement frontend table**

Add TypeScript types and render a `信号归因` panel with `DataTable`, using explicit columns for label, trade counts, entry metrics, and exit metrics.

- [ ] **Step 4: Run green test**

Run: `cd frontend && npm test -- --run BacktestPage.test.tsx`

Expected: pass.

### Task 5: QA, Docs, And Benchmark

**Files:**
- Create: `docs/qa/2026-06-19-chan-signal-attribution-qa.md`
- Modify: `docs/context/pending-features.md`
- Modify as needed: `README.md`, `docs/architecture.md`

- [ ] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
git diff --check
```

- [ ] **Step 2: Run fixed six-stock benchmark**

Run the persisted qfq fixture benchmark for `ChanStructureStrategy` over the six required stocks and include attribution aggregates in the QA document.

- [ ] **Step 3: Browser validation**

Start `./scripts/run_app.sh`, open `http://127.0.0.1:5173/`, run a visible backtest result flow, confirm `信号归因` renders, check console health, and save desktop/mobile screenshots under `/tmp/`.

- [ ] **Step 4: Commit**

Commit implementation and docs with a message such as `feat: attribute chan backtest signals`.
