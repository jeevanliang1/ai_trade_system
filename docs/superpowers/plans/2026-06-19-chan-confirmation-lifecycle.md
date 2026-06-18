# Chan Confirmation Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add optional time-based exits to `ChanStructureStrategy` so confirmation-mode entries can complete through opposite confirmation signals or max-holding exits.

**Architecture:** Keep `research.chan_structure` unchanged. Add lifecycle state inside `ChanStructureStrategy`: track held bars, reset on entry/exit, and emit a deterministic time-exit signal only when `max_holding_bars > 0`. Registry inspection automatically exposes the new constructor parameter.

**Tech Stack:** Python strategy class, pytest, strategy registry metadata, fixed CSV backtests, React + FastAPI browser QA.

---

### Task 1: Failing Lifecycle Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`
- Modify: `tests/test_strategy_registry.py`

- [ ] **Step 1: Add fake Chan scan helper**

Add a local helper that monkeypatches `ai_trade_system.strategies.popular.scan_chan_structure` and returns `types.SimpleNamespace(signals=[...])` based on the current bar date.

- [ ] **Step 2: Add confirmation opposite-signal lifecycle test**

Use fake `ResearchSignal` rows:

```python
buy = ResearchSignal(... kind="CHAN_STRUCT_BUY_CONFIRM", action="buy", score=70.0 ...)
sell = ResearchSignal(... kind="CHAN_STRUCT_SELL_CONFIRM", action="sell", score=-65.0 ...)
```

Assert a `ChanStructureStrategy(... signal_mode="confirmation", max_holding_bars=0)` emits `["buy", "sell"]` and reasons start with `chan_structure:CHAN_STRUCT_BUY_CONFIRM` and `chan_structure:CHAN_STRUCT_SELL_CONFIRM`.

- [ ] **Step 3: Add confirmation time-exit test**

Use a fake buy confirmation on the first tradable bar and no later signals. Instantiate:

```python
ChanStructureStrategy(
    "000001",
    min_bars=3,
    lookback=5,
    min_signal_score=30.0,
    signal_mode="confirmation",
    max_holding_bars=2,
)
```

Assert emitted actions are `["buy", "sell"]` and the sell reason equals `chan_structure:TIME_EXIT:max_holding_bars=2`.

- [ ] **Step 4: Add validation and registry expectations**

Assert negative `max_holding_bars` raises `ValueError`, and registry defaults expose:

```python
assert defaults["max_holding_bars"] == 0
assert "0" in params["max_holding_bars"].description
```

- [ ] **Step 5: Verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_confirmation_mode_exits_on_opposite_signal \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_confirmation_mode_exits_after_max_holding_bars \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_negative_max_holding_bars \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score \
  -q
```

Expected: failures because `max_holding_bars` is not a supported constructor parameter yet.

### Task 2: Minimal Strategy Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add constructor parameter and validation**

Add:

```python
max_holding_bars: int = 0,
```

Validate:

```python
if max_holding_bars < 0:
    raise ValueError("max_holding_bars must be non-negative")
```

Store `self.max_holding_bars` and initialize `self.holding_bars = 0`.

- [ ] **Step 2: Reset holding state on normal entries/exits**

Set `self.holding_bars = 0` on every buy and sell branch.

- [ ] **Step 3: Add time exit after candidate processing**

At the start of `on_bar`, increment `holding_bars` when already in position. After candidate processing returns no signal, emit:

```python
if self.in_position and self.max_holding_bars > 0 and self.holding_bars >= self.max_holding_bars:
    self.in_position = False
    self.holding_bars = 0
    return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, f"chan_structure:TIME_EXIT:max_holding_bars={self.max_holding_bars}")]
```

- [ ] **Step 4: Verify GREEN**

Run the RED command again.

Expected: selected tests pass.

### Task 3: Registry Guidance and Regressions

**Files:**
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] **Step 1: Update `max_holding_bars` guidance**

Mention that `0` disables time exits for strategies that support that convention.

- [ ] **Step 2: Run targeted regression**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_research_signals.py -q
```

Expected: all selected tests pass.

### Task 4: Verification, Benchmarks, Browser QA, and Docs

**Files:**
- Create: `docs/qa/2026-06-19-chan-confirmation-lifecycle-qa.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] **Step 2: Run fixed benchmark backtests**

Run 中芯国际 and 五粮液 fixtures with:

```text
signal_mode=all, min_signal_score=30.0, max_holding_bars=0
signal_mode=confirmation, min_signal_score=30.0, max_holding_bars=20
signal_mode=structure, min_signal_score=24.0, max_holding_bars=20
```

Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, profit factor, and exposure.

- [ ] **Step 3: Browser QA**

Start `./scripts/run_app.sh`, open `http://127.0.0.1:5173/`, select `ChanStructureStrategy`, verify `最大持仓天数` appears with default `0`, and capture a screenshot.

- [ ] **Step 4: Commit**

Run `git diff --check`, then:

```bash
git add docs/context/pending-features.md docs/qa/2026-06-19-chan-confirmation-lifecycle-qa.md docs/superpowers/specs/2026-06-19-chan-confirmation-lifecycle-design.md docs/superpowers/plans/2026-06-19-chan-confirmation-lifecycle.md src/ai_trade_system/strategies/popular.py src/ai_trade_system/strategy_registry.py tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py
git commit -m "feat: add chan confirmation lifecycle exits"
```
