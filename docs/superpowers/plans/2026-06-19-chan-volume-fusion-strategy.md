# Chan Volume Fusion Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a built-in `ChanVolumeFusionStrategy` where Chan structure is the only master signal source and volume momentum acts as confirmation, sizing, and exit-timing evidence.

**Architecture:** Implement the strategy in the existing built-in strategy module so it flows through the current registry, API, backtest, paper, and React strategy controls. Reuse the existing `Strategy` interface and avoid changing `PortfolioStrategy`; this is a dedicated fusion strategy, not a generic portfolio vote. Tests pin strategy discovery, fusion-specific decision rules, and API backtest compatibility.

**Tech Stack:** Python strategy core under `src/ai_trade_system`, pytest, existing FastAPI service tests, local qfq CSV benchmark fixtures, optional frontend Vitest/build verification.

---

### Task 1: Registry And Metadata Red Test

**Files:**
- Modify: `tests/test_strategy_registry.py`

- [ ] **Step 1: Write the failing registry test**

Add a test that discovers `ChanVolumeFusionStrategy` and asserts Chinese metadata plus the enum options for `weak_volume_exit_mode`:

```python
def test_chan_volume_fusion_strategy_is_registered_with_guidance():
    specs = discover_strategies()
    spec = next(strategy for strategy in specs if strategy.class_name == "ChanVolumeFusionStrategy")

    assert spec.display_name == "缠论量价融合"
    assert "量价动量确认低确定性买点" in spec.description

    parameters = {parameter.name: parameter for parameter in inspect_strategy_parameters(spec)}
    assert parameters["weak_volume_exit_mode"].options == ("reduce", "exit", "ignore")
    assert parameters["low_confidence_requires_volume"].display_name
    assert parameters["volume_boost_units"].description
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py::test_chan_volume_fusion_strategy_is_registered_with_guidance -q
```

Expected: FAIL because `ChanVolumeFusionStrategy` is not registered yet.

### Task 2: Fusion Behavior Red Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add minimal direct-state tests**

Add tests that instantiate `ChanVolumeFusionStrategy`, use internal helper methods for deterministic behavior, and avoid heavy Chan scans:

```python
def test_chan_volume_fusion_blocks_low_confidence_without_strong_volume():
    strategy = ChanVolumeFusionStrategy("000001", low_confidence_requires_volume=True)

    assert not strategy._volume_allows_low_confidence("neutral")
    assert strategy._volume_allows_low_confidence("strong")


def test_chan_volume_fusion_boosts_high_confidence_units_with_strong_volume():
    strategy = ChanVolumeFusionStrategy("000001", high_confidence_units=2, volume_boost_units=1, max_units=3)

    assert strategy._apply_volume_boost(2, "strong") == 3
    assert strategy._apply_volume_boost(2, "neutral") == 2


def test_chan_volume_fusion_weak_volume_reduces_or_exits():
    reduce_strategy = ChanVolumeFusionStrategy("000001", weak_volume_exit_mode="reduce")
    exit_strategy = ChanVolumeFusionStrategy("000001", weak_volume_exit_mode="exit")
    ignore_strategy = ChanVolumeFusionStrategy("000001", weak_volume_exit_mode="ignore")

    assert reduce_strategy._weak_volume_target_units(2) == 1
    assert exit_strategy._weak_volume_target_units(2) == 0
    assert ignore_strategy._weak_volume_target_units(2) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_blocks_low_confidence_without_strong_volume \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_boosts_high_confidence_units_with_strong_volume \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_weak_volume_reduces_or_exits -q
```

Expected: FAIL because the class and helpers do not exist.

### Task 3: Implement Strategy Skeleton And Metadata

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] **Step 1: Add `ChanVolumeFusionStrategy` constructor and helper methods**

Implement a class with the documented constructor parameters and deterministic helpers:

```python
class ChanVolumeFusionStrategy(Strategy):
    def __init__(self, symbol: str, ..., weak_volume_exit_mode: str = "reduce", ...) -> None:
        if weak_volume_exit_mode not in {"reduce", "exit", "ignore"}:
            raise ValueError("weak_volume_exit_mode must be reduce, exit, or ignore")
        self.symbol = symbol
        ...

    def _volume_allows_low_confidence(self, state: str) -> bool:
        return not self.low_confidence_requires_volume or state == "strong"

    def _apply_volume_boost(self, target_units: int, state: str) -> int:
        if self.high_confidence_volume_boost and state == "strong":
            return min(self.max_units, target_units + self.volume_boost_units)
        return target_units

    def _weak_volume_target_units(self, current_units: int) -> int:
        if self.weak_volume_exit_mode == "exit":
            return 0
        if self.weak_volume_exit_mode == "reduce":
            return max(0, current_units - 1)
        return current_units
```

- [ ] **Step 2: Register metadata**

Add the strategy to `BUILTIN_STRATEGIES` and add `weak_volume_exit_mode` guidance/options to `PARAMETER_GUIDANCE`. Add guidance entries for `low_confidence_requires_volume`, `high_confidence_volume_boost`, `volume_boost_units`, `strong_volume_extend_bars`, `weak_volume_momentum_pct`, and `max_units`.

- [ ] **Step 3: Run registry and helper tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py::test_chan_volume_fusion_strategy_is_registered_with_guidance tests/test_builtin_popular_strategies.py -q
```

Expected: registry and helper tests pass; unrelated existing tests stay green.

### Task 4: Add Signal-Level Fusion Red Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add signal emission tests**

Add tests that monkeypatch the lightweight internal decision hooks instead of building full Chan structures:

```python
def test_chan_volume_fusion_emits_volume_confirmed_t2_buy(monkeypatch):
    strategy = ChanVolumeFusionStrategy("000001", trade_size=100)
    monkeypatch.setattr(strategy, "_chan_target_for_bar", lambda bar: ("buy", 1, "CHAN_VOLUME_T2_BUY"))
    monkeypatch.setattr(strategy, "_volume_state", lambda bar: "strong")

    signals = strategy.on_bar(make_bar("000001", close=10.0))

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 100)]
    assert signals[0].reason == "CHAN_VOLUME_T2_BUY_VOLUME_CONFIRMED"
```

Add similar tests for T3 volume boost, weak-volume reduce, and Chan sell priority.

- [ ] **Step 2: Run tests to verify failure**

Run the new test names with `PYTHONPATH=src python -m pytest ... -q`.

Expected: FAIL until `on_bar` uses the hook methods.

### Task 5: Implement `on_bar` Fusion Flow

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add volume-state calculation**

Maintain closes and volumes, then classify `strong`, `neutral`, or `weak` from the latest bar and configured windows.

- [ ] **Step 2: Add Chan target hook**

Implement `_chan_target_for_bar(bar)` to use the existing Chan analyzer result and current Chan signal semantics to return:

```python
tuple[str, int, str] | None
```

where the tuple is `(action, target_units, reason)`.

- [ ] **Step 3: Use fusion rules in `on_bar`**

`on_bar` should:

1. Update volume state.
2. Ask Chan for target action/units/reason.
3. Block T2 buy when required volume is not strong.
4. Boost T3/confirmation buys when volume is strong.
5. Apply weak-volume reduce/exit when no Chan exit is present.
6. Preserve Chan sell priority.
7. Emit delta orders using current units and `trade_size`.

- [ ] **Step 4: Run signal tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q
```

Expected: PASS.

### Task 6: API Compatibility Red/Green

**Files:**
- Modify: `tests/test_api_routes.py`

- [ ] **Step 1: Add API exposure/backtest assertions**

Extend existing strategy route tests to assert `ChanVolumeFusionStrategy` is visible. Add or extend a demo-data backtest test to run the strategy by id and assert metrics/trades keys exist.

- [ ] **Step 2: Run API tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py -q
```

Expected: PASS after registry and strategy implementation.

### Task 7: Benchmarks And QA

**Files:**
- Create: `docs/qa/2026-06-19-chan-volume-fusion-benchmark.md`

- [ ] **Step 1: Run fixed six-stock benchmark**

Use local qfq fixtures and compare at least `ChanStructureStrategy`, `VolumeConfirmedMomentumStrategy`, and `ChanVolumeFusionStrategy`.

- [ ] **Step 2: Run STAR Top-20 exploratory benchmark when local sample exists**

Use `/tmp/kechuang_top20_eligible_selection.json` when present. If absent, document the skip.

- [ ] **Step 3: Write QA record**

Record parameters, fixture metadata, return, benchmark return, excess return, max drawdown, trade count, win rate, profit factor, and a short interpretation.

### Task 8: Full Verification

**Files:**
- No production edits expected.

- [ ] **Step 1: Run targeted backend tests**

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_api_routes.py -q
```

- [ ] **Step 2: Run full backend tests**

```bash
PYTHONPATH=src python -m pytest
```

- [ ] **Step 3: Run frontend tests/build**

```bash
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] **Step 4: Report git state**

Because the worktree already contains unrelated uncommitted changes, do not commit implementation unless the final staged diff can be isolated cleanly. Report any uncommitted files and which files were touched for this implementation.
