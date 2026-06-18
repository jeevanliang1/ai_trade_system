# Chan Structure Default Threshold Tuning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the default `ChanStructureStrategy.min_signal_score` to the benchmark-selected threshold and verify the new default through tests and fixed-stock backtests.

**Architecture:** Keep the existing strategy class and registry flow. Change only the constructor default and add tests that pin the default threshold behavior and registry metadata.

**Tech Stack:** Python strategy class, strategy registry parameter inspection, pytest, existing backtest and analytics modules.

---

### Task 1: Failing Default-Threshold Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`
- Modify: `tests/test_strategy_registry.py`

- [ ] **Step 1: Add strategy default test**

Add a test that instantiates `ChanStructureStrategy("000001")` and asserts:

```python
assert strategy.min_signal_score == 30.0
```

Also run a weak structural fixture and assert the default emits no trades while `min_signal_score=24.0` still emits the previous lower-confidence signal.

- [ ] **Step 2: Add registry default test**

Find the `ChanStructureStrategy` spec from `discover_strategies(...)`, inspect parameters, and assert:

```python
assert defaults["min_signal_score"] == 30.0
```

- [ ] **Step 3: Verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_filters_low_confidence_structure_signals tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score -q
```

Expected: fail because the current default is still `24.0`.

### Task 2: Minimal Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Change constructor default**

Update:

```python
min_signal_score: float = 24.0
```

to:

```python
min_signal_score: float = 30.0
```

- [ ] **Step 2: Verify GREEN**

Run the RED command again.

Expected: both tests pass.

### Task 3: Regression and Benchmark Verification

**Files:**
- Create: `docs/qa/2026-06-19-chan-structure-default-threshold-tuning-qa.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Run test suites**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_research_signals.py -q
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] **Step 2: Run fixed benchmark backtests**

Run `ChanStructureStrategy` default parameters on:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
```

Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.

- [ ] **Step 3: Browser QA**

Start `./scripts/run_app.sh`, open `http://127.0.0.1:5173/`, verify Strategy Workshop renders and `ChanStructureStrategy` parameter defaults show the tuned score, then capture a screenshot.

- [ ] **Step 4: Commit**

Run `git diff --check`, then commit:

```bash
git add docs/context/pending-features.md docs/qa/2026-06-19-chan-structure-default-threshold-tuning-qa.md src/ai_trade_system/strategies/popular.py tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py
git commit -m "tune chan structure default threshold"
```
