# Chan Signal Mode Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `ChanStructureStrategy.signal_mode` so confirmation, T2/T3 structure, and all Chan signals can be benchmarked independently while preserving the existing default strategy behavior.

**Architecture:** Keep `research.chan_structure` as the single analyzer and filter signal families inside the strategy wrapper. Expose the new constructor parameter through the existing registry inspection flow so React parameter forms receive the default and Chinese guidance automatically.

**Tech Stack:** Python strategy class, pytest, strategy registry metadata, fixed CSV backtests, React + FastAPI browser QA.

---

### Task 1: Failing Signal-Mode Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`
- Modify: `tests/test_strategy_registry.py`

- [ ] **Step 1: Add Chan structure mode tests**

Add tests that use existing deterministic Chan fixtures:

```python
def test_chan_structure_strategy_signal_mode_filters_structure_family():
    bars = [...]
    confirmation = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="confirmation",
    )
    structure = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="structure",
    )
    exploratory = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="all",
    )

    assert [signal for bar in bars for signal in confirmation.on_bar(bar)] == []
    assert structure_signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T2")
    assert all_signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T2")
```

Add a confirmation fixture check that `signal_mode="structure"` suppresses a `CHAN_STRUCT_SELL_CONFIRM` signal while `signal_mode="confirmation"` emits it.

- [ ] **Step 2: Add invalid mode test**

Add:

```python
try:
    ChanStructureStrategy("000001", signal_mode="unknown")
except ValueError as exc:
    assert "signal_mode" in str(exc)
else:
    raise AssertionError("unsupported signal_mode should raise ValueError")
```

- [ ] **Step 3: Add registry metadata expectations**

Extend Chan registry tests to assert:

```python
assert params["signal_mode"].display_name == "信号模式"
assert "confirmation" in params["signal_mode"].description
assert defaults["signal_mode"] == "all"
```

- [ ] **Step 4: Verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_signal_mode_filters_structure_family \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_signal_mode_filters_confirmation_family \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_signal_mode \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score \
  -q
```

Expected: failures because `ChanStructureStrategy.__init__` does not accept `signal_mode` and registry metadata does not expose it.

### Task 2: Minimal Strategy Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add mode constants**

Define allowed signal families near the strategy class:

```python
CHAN_CONFIRMATION_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T1_DIVERGENCE",
    "CHAN_STRUCT_SELL_T1_DIVERGENCE",
    "CHAN_STRUCT_BUY_CONFIRM",
    "CHAN_STRUCT_SELL_CONFIRM",
}
CHAN_STRUCTURE_SIGNAL_KINDS = {
    "CHAN_STRUCT_BUY_T2",
    "CHAN_STRUCT_SELL_T2",
    "CHAN_STRUCT_BUY_T3",
    "CHAN_STRUCT_SELL_T3",
}
CHAN_SIGNAL_MODES = {"confirmation", "structure", "all"}
```

- [ ] **Step 2: Add constructor parameter**

Add:

```python
signal_mode: str = "all",
```

Validate it after numeric checks:

```python
if signal_mode not in CHAN_SIGNAL_MODES:
    raise ValueError("signal_mode must be one of: all, confirmation, structure")
self.signal_mode = signal_mode
```

- [ ] **Step 3: Filter candidates**

Extend the candidate comprehension:

```python
if (
    signal.trading_day == bar.trading_day
    and abs(signal.score) >= self.min_signal_score
    and self._signal_mode_allows(signal.kind)
)
```

Add:

```python
def _signal_mode_allows(self, kind: str) -> bool:
    if self.signal_mode == "all":
        return True
    if self.signal_mode == "confirmation":
        return kind in CHAN_CONFIRMATION_SIGNAL_KINDS
    return kind in CHAN_STRUCTURE_SIGNAL_KINDS
```

- [ ] **Step 4: Verify GREEN**

Run the RED command again.

Expected: selected tests pass.

### Task 3: Registry Guidance

**Files:**
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] **Step 1: Add `signal_mode` guidance**

Add a `PARAMETER_GUIDANCE["signal_mode"]` entry with display name `信号模式`, plain-language description of `confirmation` / `structure` / `all`, and non-numeric increase/decrease copy.

- [ ] **Step 2: Run targeted registry tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py -q
```

Expected: all registry tests pass.

### Task 4: Verification, Benchmarks, Browser QA, and Docs

**Files:**
- Create: `docs/qa/2026-06-19-chan-signal-mode-controls-qa.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Run Python and frontend verification**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_research_signals.py -q
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] **Step 2: Run fixed benchmark backtests**

Run the fixed 中芯国际 and 五粮液 CSV fixtures with:

```text
signal_mode=all, min_signal_score=30.0
signal_mode=confirmation, min_signal_score=30.0
signal_mode=structure, min_signal_score=24.0
signal_mode=all, min_signal_score=24.0
```

Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, profit factor, and exposure.

- [ ] **Step 3: Browser QA**

Start `./scripts/run_app.sh`, open `http://127.0.0.1:5173/`, select `ChanStructureStrategy`, verify `信号模式` appears with default `confirmation`, and capture a screenshot.

- [ ] **Step 4: Update pending list and commit**

Remove the completed signal-family controls item, add the QA record to the completed baseline, keep exactly one next recommended feature, then run:

```bash
git diff --check
git add docs/context/pending-features.md docs/qa/2026-06-19-chan-signal-mode-controls-qa.md docs/superpowers/specs/2026-06-19-chan-signal-mode-controls-design.md docs/superpowers/plans/2026-06-19-chan-signal-mode-controls.md src/ai_trade_system/strategies/popular.py src/ai_trade_system/strategy_registry.py tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py
git commit -m "feat: add chan signal mode controls"
```
