# Chan Structure Position Sizing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ChanStructureStrategy` size positions by Chan signal certainty and expand the fixed strategy benchmark universe to six A-share fixtures.

**Architecture:** Keep signal generation in `research/chan_structure.py` unchanged. Convert `ChanStructureStrategy` from boolean position state to target unit state, emitting buy/sell deltas against the current unit count. Expose the new sizing knobs through the existing strategy registry metadata path.

**Tech Stack:** Python strategy core, pytest, existing `data_manager` local qfq CSV layout, existing docs/QA close-out workflow.

---

### Task 1: Add Failing Tests For Position Units

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`
- Modify: `tests/test_strategy_registry.py`

- [ ] **Step 1: Add unit sizing behavior tests**

Add these tests near the existing Chan structure strategy tests:

```python
def test_chan_structure_strategy_sizes_position_by_chan_certainty(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(8)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                30.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            ),
            make_research_signal(
                bars[3].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                44.0,
                bars[3].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_SELL_T2",
                "sell",
                -30.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-sell"),
                metadata={"point_type": "second-sell", "level": "fractal"},
            ),
            make_research_signal(
                bars[5].trading_day,
                "CHAN_STRUCT_SELL_CONFIRM",
                "sell",
                -60.0,
                bars[5].close_price,
                metadata={"point_type": "first-sell", "level": "segment"},
            ),
            make_research_signal(
                bars[6].trading_day,
                "CHAN_STRUCT_SELL_T3",
                "sell",
                -44.0,
                bars[6].close_price,
                tags=("chan", "structure", "third-sell"),
                metadata={"point_type": "third-sell", "level": "stroke"},
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=8,
        min_signal_score=20.0,
        allowed_point_types="all",
        max_holding_bars=0,
        trade_size=100,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [
        ("buy", 100),
        ("buy", 200),
        ("sell", 100),
        ("sell", 100),
        ("sell", 100),
    ]
    assert strategy.position_units == 0
```

Add a second focused confirmation test:

```python
def test_chan_structure_strategy_divergence_confirmation_targets_middle_units(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_CONFIRM",
                "buy",
                60.0,
                bars[2].close_price,
                metadata={"point_type": "first-buy", "level": "segment"},
            )
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=30.0,
        allowed_point_types="all",
        max_holding_bars=0,
        trade_size=100,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 200)]
    assert strategy.position_units == 2
```

Add compatibility and validation tests:

```python
def test_chan_structure_strategy_in_position_property_remains_compatible():
    strategy = ChanStructureStrategy("000001")

    strategy.in_position = True
    assert strategy.in_position is True
    assert strategy.position_units == 1

    strategy.in_position = False
    assert strategy.in_position is False
    assert strategy.position_units == 0


def test_chan_structure_strategy_rejects_invalid_unit_configuration():
    invalid_kwargs = [
        {"low_confidence_units": 0},
        {"low_confidence_units": 2, "divergence_confirm_units": 1},
        {"divergence_confirm_units": 3, "high_confidence_units": 2},
        {"high_confidence_units": 3, "sell_confirm_units": 3},
        {"sell_confirm_units": -1},
    ]

    for kwargs in invalid_kwargs:
        try:
            ChanStructureStrategy("000001", **kwargs)
        except ValueError as exc:
            assert "units" in str(exc)
        else:
            raise AssertionError(f"invalid units should raise ValueError: {kwargs}")
```

- [ ] **Step 2: Update existing expectation tests to describe new defaults**

Change the default filter assertions to:

```python
assert tuned_default.allowed_point_types == "all"
assert [signal.action for signal in tuned_signals] == ["buy"]
assert tuned_signals[0].volume == 100
```

Change `test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults` to assert:

```python
assert defaults["allowed_point_types"] == "all"
assert defaults["low_confidence_units"] == 1
assert defaults["divergence_confirm_units"] == 2
assert defaults["high_confidence_units"] == 3
assert defaults["sell_confirm_units"] == 1
```

Extend `test_chan_structure_strategy_metadata_and_parameter_guidance` with:

```python
assert params["low_confidence_units"].display_name == "低确定性目标仓位"
assert "二买" in params["low_confidence_units"].description
assert params["divergence_confirm_units"].display_name == "背驰确认目标仓位"
assert "背驰" in params["divergence_confirm_units"].description
assert params["high_confidence_units"].display_name == "高确定性目标仓位"
assert "三买" in params["high_confidence_units"].description
assert params["sell_confirm_units"].display_name == "卖出确认保留仓位"
assert "顶背驰" in params["sell_confirm_units"].description
```

- [ ] **Step 3: Run focused tests and confirm RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_sizes_position_by_chan_certainty tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_divergence_confirmation_targets_middle_units tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_in_position_property_remains_compatible tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_invalid_unit_configuration tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance -q
```

Expected: FAIL because `position_units` and the new constructor parameters do not exist and defaults still filter to third buy/sell.

### Task 2: Implement Target Unit Position State

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add constructor parameters and validation**

Add the four unit parameters after `watch_confirm_bars`, validate them, and set `allowed_point_types` default to `"all"`.

- [ ] **Step 2: Replace internal boolean state**

Add `_position_units`, `position_units`, and the compatibility `in_position` property. Initialize `_position_units = 0` and remove direct assignment to `self.in_position = False` in `__init__`.

- [ ] **Step 3: Add target unit helpers**

Add helper methods:

```python
def _target_units_for_signal(self, signal) -> int:
    if signal.kind == "CHAN_STRUCT_BUY_T2":
        return self.low_confidence_units
    if signal.kind == "CHAN_STRUCT_BUY_CONFIRM":
        return self.divergence_confirm_units
    if signal.kind == "CHAN_STRUCT_BUY_T3":
        return self.high_confidence_units
    if signal.kind == "CHAN_STRUCT_SELL_T2":
        return max(0, self.position_units - self.low_confidence_units)
    if signal.kind == "CHAN_STRUCT_SELL_CONFIRM":
        return self.sell_confirm_units
    if signal.kind == "CHAN_STRUCT_SELL_T3":
        return 0
    return self.position_units
```

Add:

```python
def _target_units_for_armed_confirmation(self, action: str) -> int:
    if action == "buy":
        return self.divergence_confirm_units
    if action == "sell":
        return self.sell_confirm_units
    return self.position_units
```

Add an emit helper that clamps the target between 0 and `high_confidence_units`, emits only the delta, updates `position_units`, clears/keeps state, and resets `holding_bars`.

- [ ] **Step 4: Route normal and armed signals through target units**

Replace the existing direct `self.in_position` buy/sell branches with target-unit emission. Keep `emitted` de-duplication, `armed_watch` clearing, score/mode/filter behavior, and existing reason prefixes.

- [ ] **Step 5: Make time exit clear all units**

When `max_holding_bars` fires, emit `position_units * trade_size`, set `position_units = 0`, and keep the existing time-exit reason.

- [ ] **Step 6: Run focused tests and confirm GREEN**

Run the command from Task 1 Step 3. Expected: PASS.

### Task 3: Expose Parameter Metadata

**Files:**
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] **Step 1: Add guidance entries**

Add four `PARAMETER_GUIDANCE` entries with Chinese labels:

- `low_confidence_units`: `低确定性目标仓位`
- `divergence_confirm_units`: `背驰确认目标仓位`
- `high_confidence_units`: `高确定性目标仓位`
- `sell_confirm_units`: `卖出确认保留仓位`

Descriptions must mention 二买、背驰、三买、顶背驰 respectively.

- [ ] **Step 2: Run registry focused tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults -q
```

Expected: PASS.

### Task 4: Expand Fixed Benchmark Fixtures And Rules

**Files:**
- Modify: `docs/rules/strategy-benchmark-backtest.md`
- Modify: `AGENTS.md`
- Create: `docs/qa/2026-06-19-chan-position-sizing-qa.md`

- [ ] **Step 1: Persist missing fixtures**

Use the project data command or data manager path to create these qfq daily CSV fixtures under `data/market/a_share/SSE/{code}/`:

```text
601318 中国平安 SSE
600901 江苏金租 SSE
600989 宝丰能源 SSE
603986 兆易创新 SSE
```

Use the requested fixed comparison range `20230619` to `20260619`.

- [ ] **Step 2: Update benchmark rule docs**

Update `docs/rules/strategy-benchmark-backtest.md` and `AGENTS.md` so the required benchmark universe lists all six fixtures.

- [ ] **Step 3: Run fixed six-stock benchmark**

Run a deterministic local benchmark for `ChanStructureStrategy` over all six persisted fixtures with default strategy parameters, initial cash 100000, and current backtest cost defaults. Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.

- [ ] **Step 4: Write QA evidence**

Create `docs/qa/2026-06-19-chan-position-sizing-qa.md` with:

- Parameter set.
- Fixture paths and metadata.
- Results table for six stocks.
- Comparison note against the previous two-stock V2 default.
- Interpretation that this validates behavior, not optimized performance.

### Task 5: Full Verification And Browser Acceptance

**Files:**
- No code files expected beyond previous tasks.

- [ ] **Step 1: Run full Python suite**

```bash
PYTHONPATH=src python -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests and build because registry metadata is visible in React**

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

Expected: all tests pass and build exits 0.

- [ ] **Step 3: Run whitespace check**

```bash
git diff --check
```

Expected: no output.

- [ ] **Step 4: Capture React screenshots**

Start `./scripts/run_app.sh`, open `http://localhost:5173`, navigate to the strategy/backtest surface where `ChanStructureStrategy` parameters are visible, and capture desktop and mobile screenshots.

- [ ] **Step 5: Final status**

Report commit status, verification commands, benchmark result summary, screenshot paths, and sedimentation changes.

