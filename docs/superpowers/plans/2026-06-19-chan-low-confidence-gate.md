# Chan Low-Confidence Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable low-confidence gate so `ChanStructureStrategy` no longer lets ordinary 二买/二卖 T2 signals trade unconditionally by default.

**Architecture:** Keep Chan signal generation unchanged. Add gate evaluation inside `ChanStructureStrategy` after existing score/mode/point/level filters and before normal target-unit emission, while leaving the armed T1 confirmation path as an explicit bypass. Use `result.core_v2.trends` from the incremental analyzer for trend compatibility, with stroke/segment fallback when a signal is fractal-level.

**Tech Stack:** Python strategy core, pytest, existing strategy registry metadata, existing fixed six-stock qfq fixtures, React/FastAPI parameter surface.

---

### Task 1: Low-Confidence Gate Behavior Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add deterministic fake analyzer helper**

Add this helper after `patch_chan_structure_scan`:

```python
def patch_chan_structure_analyzer(monkeypatch, signals: list[ResearchSignal], trends: list[object] | None = None) -> None:
    class FakeAnalyzer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def update_bar(self, bar):
            return SimpleNamespace(signals=signals, core_v2=SimpleNamespace(trends=trends or []))

    monkeypatch.setattr(popular_strategies, "ChanCoreV2Analyzer", FakeAnalyzer, raising=False)
```

- [ ] **Step 2: Add RED tests for T2 gating**

Add these tests near the existing Chan structure tests:

```python
def test_chan_structure_strategy_default_gate_blocks_t2_buy_in_downtrend(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []
    assert strategy.position_units == 0
```

```python
def test_chan_structure_strategy_t2_score_override_passes_low_confidence_gate(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                36.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 100)]
```

```python
def test_chan_structure_strategy_gate_off_preserves_plain_t2_behavior(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=20.0,
        low_confidence_gate="off",
        max_holding_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 100)]
```

```python
def test_chan_structure_strategy_armed_t1_confirmation_bypasses_low_confidence_gate(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T1_DIVERGENCE",
                "buy",
                62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
                metadata={"point_type": "first-buy", "level": "segment"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            ),
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=20.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        watch_confirm_bars=5,
        max_holding_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 200)]
    assert signals[0].reason.startswith("chan_structure:ARMED_CONFIRM")
```

```python
def test_chan_structure_strategy_range_context_caps_low_confidence_adds(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="range")],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=20.0,
        max_holding_bars=0,
        range_max_units=1,
    )
    strategy.position_units = 1

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []
    assert strategy.position_units == 1
```

```python
def test_chan_structure_strategy_t3_ignores_low_confidence_gate(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                44.0,
                bars[2].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 300)]
```

```python
def test_chan_structure_strategy_rejects_invalid_low_confidence_gate_configuration():
    invalid_kwargs = [
        {"low_confidence_gate": "bad"},
        {"low_confidence_min_score": -1.0},
        {"range_max_units": -1},
        {"range_max_units": 4, "high_confidence_units": 3},
    ]

    for kwargs in invalid_kwargs:
        try:
            ChanStructureStrategy("000001", **kwargs)
        except ValueError as exc:
            assert "low_confidence" in str(exc) or "range_max_units" in str(exc)
        else:
            raise AssertionError(f"invalid low-confidence gate config should raise: {kwargs}")
```

- [ ] **Step 3: Run RED tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_default_gate_blocks_t2_buy_in_downtrend \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_t2_score_override_passes_low_confidence_gate \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_gate_off_preserves_plain_t2_behavior \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_armed_t1_confirmation_bypasses_low_confidence_gate \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_range_context_caps_low_confidence_adds \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_t3_ignores_low_confidence_gate \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_invalid_low_confidence_gate_configuration -q
```

Expected: FAIL because constructor parameters and low-confidence gate logic do not exist.

### Task 2: Implement Low-Confidence Gate

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add constants and constructor parameters**

Add:

```python
CHAN_LOW_CONFIDENCE_GATES = {"off", "divergence", "trend", "divergence_or_trend"}
CHAN_LOW_CONFIDENCE_SIGNAL_KINDS = {"CHAN_STRUCT_BUY_T2", "CHAN_STRUCT_SELL_T2"}
CHAN_CORE_V2_TREND_LEVELS = {"stroke", "segment"}
```

Add constructor parameters after `watch_confirm_bars`:

```python
low_confidence_gate: str = "divergence_or_trend",
low_confidence_min_score: float = 32.0,
range_max_units: int = 1,
```

Validate them and assign them to `self`.

- [ ] **Step 2: Gate normal T2 emission**

In `on_bar`, after existing score/mode/filter checks and before de-duplication/emission, skip normal low-confidence signals when:

```python
not self._low_confidence_gate_allows(signal, result)
```

Do not add this check inside the armed confirmation block.

- [ ] **Step 3: Add helper methods**

Add helpers:

```python
def _low_confidence_gate_allows(self, signal, result) -> bool:
    if signal.kind not in CHAN_LOW_CONFIDENCE_SIGNAL_KINDS:
        return True
    if self.low_confidence_gate == "off":
        return True
    if self.low_confidence_gate == "divergence":
        return False
    if abs(signal.score) >= self.low_confidence_min_score:
        return True
    return self._trend_context_allows_low_confidence(signal, result)
```

```python
def _trend_context_allows_low_confidence(self, signal, result) -> bool:
    if self.low_confidence_gate not in {"trend", "divergence_or_trend"}:
        return False
    trend = self._trend_for_signal(signal, result)
    if trend is None:
        return True
    trend_type = getattr(trend, "trend_type", "")
    if signal.action == "buy":
        if trend_type in {"up", "transition"}:
            return True
        if trend_type == "range":
            return self.position_units < self.range_max_units
        return False
    if signal.action == "sell":
        if trend_type in {"down", "transition", "range"}:
            return True
        return False
    return False
```

```python
def _trend_for_signal(self, signal, result):
    core_v2 = getattr(result, "core_v2", None)
    trends = list(getattr(core_v2, "trends", []) or [])
    if not trends:
        return None
    metadata = getattr(signal, "metadata", {}) or {}
    level = metadata.get("level")
    if level in CHAN_CORE_V2_TREND_LEVELS:
        for trend in reversed(trends):
            if getattr(trend, "level", None) == level:
                return trend
    for fallback_level in ("stroke", "segment"):
        for trend in reversed(trends):
            if getattr(trend, "level", None) == fallback_level:
                return trend
    return None
```

- [ ] **Step 4: Run GREEN tests**

Run the command from Task 1 Step 3. Expected: PASS.

### Task 3: Registry Metadata Tests And Implementation

**Files:**
- Modify: `tests/test_strategy_registry.py`
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] **Step 1: Add RED registry assertions**

Extend `test_chan_structure_strategy_metadata_and_parameter_guidance`:

```python
assert params["low_confidence_gate"].display_name == "低确定性门控"
assert "二买" in params["low_confidence_gate"].description
assert params["low_confidence_gate"].options == ("off", "divergence", "trend", "divergence_or_trend")
assert params["low_confidence_min_score"].display_name == "低确定性放行分"
assert "T2" in params["low_confidence_min_score"].description
assert params["range_max_units"].display_name == "震荡区最大仓位"
assert "range" in params["range_max_units"].description
```

Extend `test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults`:

```python
assert defaults["low_confidence_gate"] == "divergence_or_trend"
assert defaults["low_confidence_min_score"] == 32.0
assert defaults["range_max_units"] == 1
```

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults -q
```

Expected: FAIL because metadata/defaults do not exist yet.

- [ ] **Step 2: Add metadata guidance**

In `PARAMETER_GUIDANCE`, add:

```python
"low_confidence_gate": ParameterGuidance(
    display_name="低确定性门控",
    description="控制二买/二卖 T2 这类低确定性信号是否需要背驰确认、走势兼容或高分放行。",
    increase_effect="该参数不是数值大小；off 最宽松，divergence 最严格，trend 和 divergence_or_trend 介于两者之间。",
    decrease_effect="该参数不是数值大小；切换枚举值会改变 T2 信号参与交易的条件。",
    options=("off", "divergence", "trend", "divergence_or_trend"),
),
"low_confidence_min_score": ParameterGuidance(
    display_name="低确定性放行分",
    description="二买/二卖 T2 信号达到该分数后，即使缺少趋势兼容或背驰确认也允许交易。",
    increase_effect="调大后 T2 分数放行更严格，交易更少。",
    decrease_effect="调小后更多 T2 信号可被分数放行，交易更频繁。",
),
"range_max_units": ParameterGuidance(
    display_name="震荡区最大仓位",
    description="Chan Core V2 判断为 range 震荡时，低确定性买点最多允许持有的仓位单位。",
    increase_effect="调大后震荡区也允许更多低确定性加仓，收益弹性和回撤都会增加。",
    decrease_effect="调小后震荡区低确定性买点更克制，减少反复交易。",
),
```

- [ ] **Step 3: Run registry GREEN tests**

Run the registry command from Step 1. Expected: PASS.

### Task 4: Full Verification, Benchmark, Docs, Browser

**Files:**
- Create: `docs/qa/2026-06-19-chan-low-confidence-gate-qa.md`
- Modify: `docs/context/pending-features.md`
- Modify: `README.md`
- Modify: `strategies/README.md`
- Modify: `docs/architecture.md`

- [ ] **Step 1: Run full verification**

Run:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
git diff --check
```

Expected: all pass and diff check has no output.

- [ ] **Step 2: Run six-stock benchmark**

Run `ChanStructureStrategy(code)` with defaults over:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv
```

Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.

- [ ] **Step 3: Write QA and docs**

Create `docs/qa/2026-06-19-chan-low-confidence-gate-qa.md` with:

- Parameter set.
- Fixture metadata.
- Six-stock result table.
- Comparison against A variant from `docs/qa/2026-06-19-chan-position-sizing-qa.md`.
- Interpretation that this is behavior validation, not broad optimization.

Update README/architecture/strategies docs to mention low-confidence T2 gating. Update `docs/context/pending-features.md` to mark B complete and keep C/dynamic position cap or signal attribution as the next recommended feature.

- [ ] **Step 4: Browser validation**

Start `./scripts/run_app.sh`, select `缠论结构策略`, verify new parameters render:

- `低确定性门控`
- `低确定性放行分`
- `震荡区最大仓位`

Capture desktop and mobile screenshots under `/tmp/`.

- [ ] **Step 5: Commit implementation**

Commit all implementation and documentation changes:

```bash
git add .
git commit -m "feat: gate low-confidence chan signals"
```

