# Chan Dynamic Position Cap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add dynamic buy-side position caps to `ChanStructureStrategy` so high-certainty signals respect Chan Core V2 trend context and current floating-loss risk.

**Architecture:** Keep signal generation unchanged. Compute normal A/B target units first, then pass buy targets through a cap helper that reads `result.core_v2.trends` and strategy average entry price; sell targets bypass the cap. Expose the new knobs through the existing strategy constructor and registry metadata so React renders them automatically.

**Tech Stack:** Python strategy core, pytest, existing strategy registry metadata, existing fixed six-stock qfq fixtures, React/FastAPI parameter surface.

---

### Task 1: Dynamic Cap Behavior Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add RED tests for trend caps**

Add tests near existing Chan structure tests:

```python
def test_chan_structure_strategy_dynamic_cap_limits_t3_buy_in_downtrend(monkeypatch):
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

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 100)]
    assert strategy.position_units == 1
```

```python
def test_chan_structure_strategy_dynamic_cap_allows_full_t3_buy_in_uptrend(monkeypatch):
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
        trends=[SimpleNamespace(level="stroke", trend_type="up")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 300)]
    assert strategy.position_units == 3
```

```python
def test_chan_structure_strategy_dynamic_cap_limits_range_t3_to_trend_cap(monkeypatch):
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
        trends=[SimpleNamespace(level="stroke", trend_type="range")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 200)]
    assert strategy.position_units == 2
```

- [ ] **Step 2: Add RED tests for off mode, risk cap, and validation**

```python
def test_chan_structure_strategy_position_cap_off_preserves_full_t3_target(monkeypatch):
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
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=20.0,
        max_holding_bars=0,
        position_cap_mode="off",
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 300)]
```

```python
def test_chan_structure_strategy_drawdown_cap_blocks_add_on_buy(monkeypatch):
    bars = [
        make_chan_bar(0, 12.0, 12.5, 11.5),
        make_chan_bar(1, 12.0, 12.5, 11.5),
        make_chan_bar(2, 12.0, 12.5, 11.5),
        make_chan_bar(3, 11.0, 11.2, 10.8),
        make_chan_bar(4, 11.0, 11.2, 10.8),
    ]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_CONFIRM",
                "buy",
                60.0,
                bars[2].close_price,
                metadata={"point_type": "first-buy", "level": "segment"},
            ),
            make_research_signal(
                bars[3].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                60.0,
                bars[3].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            ),
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="up"), SimpleNamespace(level="segment", trend_type="up")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 200)]
    assert strategy.position_units == 2
```

```python
def test_chan_structure_strategy_full_exit_clears_average_entry_price(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                60.0,
                bars[2].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_SELL_T3",
                "sell",
                -60.0,
                bars[4].close_price,
                tags=("chan", "structure", "third-sell"),
                metadata={"point_type": "third-sell", "level": "stroke"},
            ),
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="up")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=6, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 300), ("sell", 300)]
    assert strategy.position_units == 0
    assert strategy.average_entry_price is None
```

```python
def test_chan_structure_strategy_rejects_invalid_dynamic_cap_configuration():
    invalid_kwargs = [
        {"position_cap_mode": "bad"},
        {"trend_cap_units": 0},
        {"trend_cap_units": 4, "high_confidence_units": 3},
        {"risk_drawdown_cap_pct": -1.0},
    ]

    for kwargs in invalid_kwargs:
        try:
            ChanStructureStrategy("000001", **kwargs)
        except ValueError as exc:
            assert "position_cap" in str(exc) or "trend_cap_units" in str(exc) or "risk_drawdown" in str(exc)
        else:
            raise AssertionError(f"invalid dynamic cap config should raise: {kwargs}")
```

- [ ] **Step 3: Run RED tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_dynamic_cap_limits_t3_buy_in_downtrend \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_dynamic_cap_allows_full_t3_buy_in_uptrend \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_dynamic_cap_limits_range_t3_to_trend_cap \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_position_cap_off_preserves_full_t3_target \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_drawdown_cap_blocks_add_on_buy \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_full_exit_clears_average_entry_price \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_invalid_dynamic_cap_configuration -q
```

Expected: FAIL because constructor parameters and dynamic cap logic do not exist yet.

### Task 2: Strategy Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add constants and constructor parameters**

Add:

```python
CHAN_POSITION_CAP_MODES = {"off", "trend", "risk", "trend_risk"}
```

Add constructor parameters after `range_max_units`:

```python
position_cap_mode: str = "trend_risk",
trend_cap_units: int = 2,
risk_drawdown_cap_pct: float = 3.0,
```

Validate:

```python
if position_cap_mode not in CHAN_POSITION_CAP_MODES:
    raise ValueError("position_cap_mode must be one of: off, trend, risk, trend_risk")
if trend_cap_units < 1 or trend_cap_units > high_confidence_units:
    raise ValueError("trend_cap_units must be between 1 and high_confidence_units")
if risk_drawdown_cap_pct < 0:
    raise ValueError("risk_drawdown_cap_pct must be non-negative")
```

Assign to `self`, and initialize:

```python
self.average_entry_price: float | None = None
```

- [ ] **Step 2: Cap normal and armed buy targets**

For armed confirmation and normal signal paths, after computing `target_units`, call:

```python
target_units = self._cap_target_units(signal, result, target_units)
```

Then run `_can_emit_target_units(...)` as before.

- [ ] **Step 3: Add cap helper methods**

Add methods:

```python
def _cap_target_units(self, signal, result, target_units: int) -> int:
    target_units = self._clamp_position_units(target_units)
    if signal.action != "buy" or self.position_cap_mode == "off":
        return target_units
    capped = target_units
    if self.position_cap_mode in {"trend", "trend_risk"}:
        capped = min(capped, self._trend_cap_units(signal, result))
    if self.position_cap_mode in {"risk", "trend_risk"} and self._drawdown_cap_blocks_add(signal.price):
        capped = min(capped, self.position_units)
    return self._clamp_position_units(capped)
```

```python
def _trend_cap_units(self, signal, result) -> int:
    trend = self._trend_for_signal(signal, result)
    if trend is None:
        return self.high_confidence_units
    trend_type = getattr(trend, "trend_type", "")
    if trend_type == "up":
        return self.high_confidence_units
    if trend_type in {"transition", "range"}:
        return self.trend_cap_units
    if trend_type == "down":
        return self.low_confidence_units
    return self.high_confidence_units
```

```python
def _drawdown_cap_blocks_add(self, price: float) -> bool:
    if self.position_units <= 0 or self.average_entry_price is None:
        return False
    if self.average_entry_price <= 0:
        return False
    drawdown_pct = (price / self.average_entry_price - 1) * 100
    return drawdown_pct <= -self.risk_drawdown_cap_pct
```

- [ ] **Step 4: Track average entry price**

In `_emit_position_delta(...)`, update average entry on buys and clear on full exits:

```python
previous_units = self.position_units
action = "buy" if target_units > previous_units else "sell"
delta_units = abs(target_units - previous_units)
volume = delta_units * self.trade_size
if action == "buy":
    previous_cost = (self.average_entry_price or price) * previous_units
    new_cost = previous_cost + price * delta_units
    self.average_entry_price = new_cost / target_units if target_units > 0 else None
elif target_units == 0:
    self.average_entry_price = None
self.position_units = target_units
```

In the time-exit branch, set `self.average_entry_price = None`.

- [ ] **Step 5: Run GREEN behavior tests**

Run the RED command from Task 1 Step 3. Expected: PASS.

### Task 3: Registry Metadata

**Files:**
- Modify: `tests/test_strategy_registry.py`
- Modify: `src/ai_trade_system/strategy_registry.py`

- [ ] **Step 1: Add RED registry assertions**

Extend `test_chan_structure_strategy_metadata_and_parameter_guidance`:

```python
assert params["position_cap_mode"].display_name == "动态仓位上限"
assert "trend_risk" in params["position_cap_mode"].description
assert params["position_cap_mode"].options == ("off", "trend", "risk", "trend_risk")
assert params["trend_cap_units"].display_name == "趋势不明上限"
assert "range" in params["trend_cap_units"].description
assert params["risk_drawdown_cap_pct"].display_name == "浮亏加仓阈值"
assert "浮亏" in params["risk_drawdown_cap_pct"].description
```

Extend `test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults`:

```python
assert defaults["position_cap_mode"] == "trend_risk"
assert defaults["trend_cap_units"] == 2
assert defaults["risk_drawdown_cap_pct"] == 3.0
```

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults -q
```

Expected: FAIL until metadata guidance is added.

- [ ] **Step 2: Add registry guidance**

Add `PARAMETER_GUIDANCE` entries:

```python
"position_cap_mode": ParameterGuidance(
    display_name="动态仓位上限",
    description="控制缠论结构策略是否用趋势环境和浮亏风险动态限制买入目标仓位；trend_risk 同时启用两类限制。",
    increase_effect="该参数不是数值大小；off 最宽松，trend/risk 只启用单项限制，trend_risk 最克制。",
    decrease_effect="该参数不是数值大小；切换枚举值会改变三买、背驰确认等买入信号能达到的最大仓位。",
    options=("off", "trend", "risk", "trend_risk"),
),
"trend_cap_units": ParameterGuidance(
    display_name="趋势不明上限",
    description="Chan Core V2 判断为 range 或 transition 时，买入信号最多允许达到的仓位单位。",
    increase_effect="调大后震荡或过渡走势中也允许更高仓位，收益弹性和回撤风险都会增加。",
    decrease_effect="调小后趋势不明时更克制，减少高仓位反复交易。",
),
"risk_drawdown_cap_pct": ParameterGuidance(
    display_name="浮亏加仓阈值",
    description="当前价格相对策略平均入场价浮亏达到该百分比后，禁止继续加仓但不强制卖出。",
    increase_effect="调大后允许更深浮亏时继续加仓，交易更激进。",
    decrease_effect="调小后更早停止加仓，风险预算更保守。",
),
```

- [ ] **Step 3: Run registry GREEN tests**

Run the registry command from Step 1. Expected: PASS.

### Task 4: Verification, Benchmark, Docs, Browser, Commit

**Files:**
- Create: `docs/qa/2026-06-19-chan-dynamic-position-cap-qa.md`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `strategies/README.md`
- Modify: `docs/context/pending-features.md`

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

Run default `ChanStructureStrategy(code)` over the six qfq fixtures:

```text
688981/SSE, 000858/SZSE, 601318/SSE, 600901/SSE, 600989/SSE, 603986/SSE
```

Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, profit factor, and exposure.

- [ ] **Step 3: Write QA and docs**

Create `docs/qa/2026-06-19-chan-dynamic-position-cap-qa.md` with:

- Parameter set.
- Fixture metadata.
- Six-stock result table.
- Comparison against B from `docs/qa/2026-06-19-chan-low-confidence-gate-qa.md`.
- Interpretation that this validates C behavior, not parameter optimization.

Update README/architecture/strategies docs to mention dynamic position caps. Update `docs/context/pending-features.md` to mark C complete and record the next recommended feature.

- [ ] **Step 4: Browser validation**

Start `./scripts/run_app.sh`, select `缠论结构策略`, verify:

- `动态仓位上限`
- `趋势不明上限`
- `浮亏加仓阈值`

Capture desktop and mobile screenshots under `/tmp/`.

- [ ] **Step 5: Commit implementation**

Commit all implementation and documentation changes:

```bash
git add .
git commit -m "feat: cap chan position risk dynamically"
```
