# Chan Offensive Fusion Combo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Chan-led fusion and portfolio combination less conservative by improving upside capture while preserving the fixed-fixture downside floor.

**Architecture:** Keep Chan as the primary signal source in `ChanVolumeFusionStrategy`, but gate weak-volume reductions behind broader trend-break evidence so strong trends are not cut too early. Add a Chan-led offensive portfolio preset through the existing `portfolio_presets` API path, using strategy parameter overrides instead of changing `PortfolioStrategy` semantics.

**Tech Stack:** Pure Python strategy core, pytest, existing FastAPI route tests, existing React Portfolio Lab tests, persisted local qfq fixtures, docs/QA markdown.

---

### Task 1: Strategy Trend-Hold Red Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add tests for weak-volume continuation gating**

Append tests near the current `ChanVolumeFusionStrategy` tests:

```python
def test_chan_volume_fusion_holds_weak_volume_above_continuation_trend(monkeypatch):
    bars = [
        make_volume_bar(1, 10.0, 1000),
        make_volume_bar(2, 10.2, 1000),
        make_volume_bar(3, 10.4, 1000),
        make_volume_bar(4, 10.6, 1000),
        make_volume_bar(5, 10.1, 1000),
    ]
    patch_chan_structure_analyzer(monkeypatch, [], trends=[SimpleNamespace(level="stroke", trend_type="up")])
    strategy = popular_strategies.ChanVolumeFusionStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        momentum_window=3,
        volume_window=3,
        trend_window=3,
        continuation_trend_window=3,
        weak_volume_requires_trend_break=True,
        weak_volume_exit_mode="reduce",
        weak_volume_momentum_pct=0.0,
        severe_weak_momentum_pct=-0.08,
        max_holding_bars=0,
    )
    strategy.position_units = 2

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []
    assert strategy.position_units == 2
```

Add the companion break test:

```python
def test_chan_volume_fusion_reduces_weak_volume_after_continuation_trend_break(monkeypatch):
    bars = [
        make_volume_bar(1, 10.0, 1000),
        make_volume_bar(2, 10.3, 1000),
        make_volume_bar(3, 10.6, 1000),
        make_volume_bar(4, 10.9, 1000),
        make_volume_bar(5, 9.7, 1000),
    ]
    patch_chan_structure_analyzer(monkeypatch, [], trends=[SimpleNamespace(level="stroke", trend_type="up")])
    strategy = popular_strategies.ChanVolumeFusionStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        momentum_window=3,
        volume_window=3,
        trend_window=3,
        continuation_trend_window=3,
        weak_volume_requires_trend_break=True,
        weak_volume_exit_mode="reduce",
        weak_volume_momentum_pct=0.0,
        severe_weak_momentum_pct=-0.08,
        max_holding_bars=0,
    )
    strategy.position_units = 2

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("sell", 100)]
    assert strategy.position_units == 1
    assert signals[0].reason.startswith("chan_volume_fusion:CHAN_VOLUME_WEAK_REDUCE")
```

Add the severe weakness and explicit Chan sell priority tests:

```python
def test_chan_volume_fusion_severe_weak_momentum_reduces_before_trend_break(monkeypatch):
    bars = [
        make_volume_bar(1, 10.0, 1000),
        make_volume_bar(2, 10.5, 1000),
        make_volume_bar(3, 11.0, 1000),
        make_volume_bar(4, 11.5, 1000),
        make_volume_bar(5, 10.7, 1000),
    ]
    patch_chan_structure_analyzer(monkeypatch, [], trends=[SimpleNamespace(level="stroke", trend_type="up")])
    strategy = popular_strategies.ChanVolumeFusionStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        momentum_window=3,
        volume_window=3,
        trend_window=3,
        continuation_trend_window=3,
        weak_volume_requires_trend_break=True,
        weak_volume_exit_mode="reduce",
        weak_volume_momentum_pct=0.0,
        severe_weak_momentum_pct=-0.02,
        max_holding_bars=0,
    )
    strategy.position_units = 2

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("sell", 100)]
    assert strategy.position_units == 1
```

```python
def test_chan_volume_fusion_chan_sell_ignores_continuation_hold(monkeypatch):
    bars = [
        make_volume_bar(1, 10.0, 1000),
        make_volume_bar(2, 10.2, 1000),
        make_volume_bar(3, 10.4, 1000),
        make_volume_bar(4, 10.6, 1000),
        make_volume_bar(5, 10.1, 1000),
    ]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[-1].trading_day,
                "CHAN_STRUCT_SELL_T3",
                "sell",
                -60.0,
                bars[-1].close_price,
                tags=("chan", "structure", "third-sell"),
                metadata={"point_type": "third-sell", "level": "stroke"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="up")],
    )
    strategy = popular_strategies.ChanVolumeFusionStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        momentum_window=3,
        volume_window=3,
        trend_window=3,
        continuation_trend_window=3,
        weak_volume_requires_trend_break=True,
        weak_volume_exit_mode="reduce",
        max_holding_bars=0,
    )
    strategy.position_units = 2

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("sell", 200)]
    assert strategy.position_units == 0
    assert signals[0].reason.startswith("chan_volume_fusion:CHAN_VOLUME_CHAN_SELL")
```

- [ ] **Step 2: Run red tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_holds_weak_volume_above_continuation_trend \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_reduces_weak_volume_after_continuation_trend_break \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_severe_weak_momentum_reduces_before_trend_break \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_chan_sell_ignores_continuation_hold \
  -q
```

Expected: FAIL with `TypeError` because `continuation_trend_window`, `weak_volume_requires_trend_break`, and `severe_weak_momentum_pct` are not implemented.

### Task 2: Strategy Trend-Hold Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`
- Modify: `src/ai_trade_system/strategy_registry.py`
- Test: `tests/test_builtin_popular_strategies.py`
- Test: `tests/test_strategy_registry.py`

- [ ] **Step 1: Add constructor parameters and state**

Modify `ChanVolumeFusionStrategy.__init__` to accept:

```python
weak_volume_requires_trend_break: bool = True,
continuation_trend_window: int = 60,
severe_weak_momentum_pct: float = -0.06,
```

Validate `continuation_trend_window > 0`, assign the fields, and change `volume_closes` maxlen to include `continuation_trend_window`:

```python
if continuation_trend_window <= 0:
    raise ValueError("continuation_trend_window must be positive")
self.weak_volume_requires_trend_break = bool(weak_volume_requires_trend_break)
self.continuation_trend_window = int(continuation_trend_window)
self.severe_weak_momentum_pct = float(severe_weak_momentum_pct)
self.volume_closes = deque(maxlen=max(self.momentum_window, self.trend_window, self.continuation_trend_window) + 1)
```

- [ ] **Step 2: Preserve volume diagnostics**

Change `_classify_volume_state` so it stores the latest helper diagnostics for the current bar:

```python
self._latest_volume_momentum = momentum
self._latest_continuation_trend_average = mean(previous_closes[-self.continuation_trend_window :])
```

Initialize these fields in `__init__`:

```python
self._latest_volume_momentum = 0.0
self._latest_continuation_trend_average: float | None = None
```

- [ ] **Step 3: Add weak-volume gate helpers**

Add methods:

```python
def _weak_volume_should_reduce(self, bar: Bar, result) -> bool:
    if not self.weak_volume_requires_trend_break:
        return True
    if self._latest_volume_momentum <= self.severe_weak_momentum_pct:
        return True
    trend_average = self._latest_continuation_trend_average
    if trend_average is not None and bar.close_price < trend_average:
        return True
    return self._chan_context_is_bearish(result)

def _chan_context_is_bearish(self, result) -> bool:
    core_v2 = getattr(result, "core_v2", None)
    trends = list(getattr(core_v2, "trends", []) or [])
    for trend in reversed(trends):
        if getattr(trend, "level", None) in CHAN_CORE_V2_TREND_LEVELS:
            return getattr(trend, "trend_type", "") == "down"
    return False
```

In `on_bar`, replace the weak-volume branch condition:

```python
if self.in_position and volume_state == "weak" and self._weak_volume_should_reduce(bar, result):
    ...
```

- [ ] **Step 4: Add parameter guidance**

In `PARAMETER_GUIDANCE`, add entries for:

```python
"weak_volume_requires_trend_break"
"continuation_trend_window"
"severe_weak_momentum_pct"
```

Use Chinese labels and explain that turning the gate on avoids premature reduction during healthy trend pauses.

- [ ] **Step 5: Run green tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_holds_weak_volume_above_continuation_trend \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_reduces_weak_volume_after_continuation_trend_break \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_severe_weak_momentum_reduces_before_trend_break \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_chan_sell_ignores_continuation_hold \
  tests/test_strategy_registry.py::test_chan_volume_fusion_strategy_is_registered_with_guidance \
  -q
```

Expected: PASS.

### Task 3: Offensive Portfolio Preset

**Files:**
- Modify: `src/ai_trade_system/portfolio_presets.py`
- Modify: `tests/test_api_routes.py`

- [ ] **Step 1: Add red API test for the new preset**

Extend `test_bootstrap_returns_portfolio_presets_for_strategy_combinations` in `tests/test_api_routes.py`:

```python
offensive = next(preset for preset in presets if preset["id"] == "chan_offensive_fusion_stack")

assert offensive["name"] == "缠论进攻融合组合"
assert offensive["mode"] == "weighted_vote"
assert "进攻" in offensive["description"]
assert offensive["allocations"][0]["strategy"]["id"] == "builtin:popular:ChanVolumeFusionStrategy"
assert offensive["allocations"][0]["weight"] > offensive["allocations"][1]["weight"]
assert offensive["allocations"][0]["strategy"]["params"]["symbol"] == "000001"
assert offensive["allocations"][0]["strategy"]["params"]["weak_volume_requires_trend_break"] is True
assert offensive["allocations"][0]["strategy"]["params"]["high_confidence_units"] == 3
assert offensive["allocations"][0]["strategy"]["params"]["max_units"] == 4
```

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_bootstrap_returns_portfolio_presets_for_strategy_combinations -q
```

Expected: FAIL because `chan_offensive_fusion_stack` is not in `PORTFOLIO_PRESETS`.

- [ ] **Step 2: Add the preset**

In `src/ai_trade_system/portfolio_presets.py`, append:

```python
PortfolioPresetSpec(
    id="chan_offensive_fusion_stack",
    name="缠论进攻融合组合",
    description="以缠论量价融合为主，叠加量价、MACD和ATR趋势确认，目标是在强趋势中提高收益上限并保留下限控制。",
    mode="weighted_vote",
    allocations=(
        PortfolioPresetAllocationSpec(
            "ChanVolumeFusionStrategy",
            1.4,
            "缠论量价主策略",
            params={
                "high_confidence_units": 3,
                "max_units": 4,
                "volume_boost_units": 1,
                "weak_volume_requires_trend_break": True,
                "continuation_trend_window": 60,
                "severe_weak_momentum_pct": -0.06,
            },
        ),
        PortfolioPresetAllocationSpec("ChanStructureStrategy", 0.6, "缠论结构基准"),
        PortfolioPresetAllocationSpec("VolumeConfirmedMomentumStrategy", 0.8, "量价趋势确认"),
        PortfolioPresetAllocationSpec("MacdTrendStrategy", 0.55, "趋势延续确认"),
        PortfolioPresetAllocationSpec("AtrVolatilityBreakoutStrategy", 0.45, "波动突破确认"),
    ),
)
```

- [ ] **Step 3: Run preset tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_bootstrap_returns_portfolio_presets_for_strategy_combinations tests/test_portfolio.py -q
```

Expected: PASS.

### Task 4: Benchmarks And QA Sedimentation

**Files:**
- Create: `docs/qa/2026-06-19-chan-offensive-fusion-combo-benchmark.md`
- Modify: `docs/context/pending-features.md`
- Modify: `README.md`
- Modify: `strategies/README.md`

- [ ] **Step 1: Run fixed six-stock benchmark**

Use this runner:

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.api.schemas import PortfolioRequest
from ai_trade_system.api.service import _build_portfolio
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.portfolio_presets import portfolio_preset_views
from ai_trade_system.strategy_registry import discover_strategies
from ai_trade_system.strategies.popular import ChanVolumeFusionStrategy

cases = [
    ("688981", "中芯国际", "SSE", "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"),
    ("000858", "五粮液", "SZSE", "data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv"),
    ("601318", "中国平安", "SSE", "data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv"),
    ("600901", "江苏金租", "SSE", "data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv"),
    ("600989", "宝丰能源", "SSE", "data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv"),
    ("603986", "兆易创新", "SSE", "data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv"),
]
config = BacktestConfig(initial_cash=100000)
strategies = discover_strategies()
for symbol, name, exchange, path in cases:
    bars = read_bars_csv(path)
    preset = next(item for item in portfolio_preset_views(strategies, symbol) if item["id"] == "chan_offensive_fusion_stack")
    portfolio = PortfolioRequest(
        allocations=[
            {"strategy": allocation["strategy"], "weight": allocation["weight"], "enabled": allocation["enabled"]}
            for allocation in preset["allocations"]
        ],
        mode=preset["mode"],
        ai_adjust=False,
        ai_direction=None,
    )
    single_result = run_backtest(bars, ChanVolumeFusionStrategy(symbol), config)
    single_metrics = calculate_backtest_metrics(single_result.equity_curve, single_result.trades, config.initial_cash)
    combo_result = run_backtest(bars, _build_portfolio(portfolio), config)
    combo_metrics = calculate_backtest_metrics(combo_result.equity_curve, combo_result.trades, config.initial_cash)
    print(symbol, name, len(bars), bars[0].trading_day, bars[-1].trading_day, single_metrics, combo_metrics)
PY
```

Copy the command output into the QA document as two markdown tables with this exact header:

```markdown
| Symbol | Name | Rows | Date range | Final equity | Return | Benchmark | Excess | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
```

The first table is the standalone `ChanVolumeFusionStrategy`; the second table is `chan_offensive_fusion_stack`.

- [ ] **Step 2: Run STAR supplemental benchmark**

Use the existing local `data/market/a_share/SSE/688*/` qfq fixtures, excluding `688981`, and run the offensive preset across the first 20 persisted files. Record a markdown table with the same table header as Step 1. Below the table, write one summary sentence containing the actual stock count, positive-result count, average return, median return, average max drawdown, total trades, best symbol and return, and worst symbol and return from the run.

- [ ] **Step 3: Write QA markdown**

Create `docs/qa/2026-06-19-chan-offensive-fusion-combo-benchmark.md` with:

```markdown
# Chan Offensive Fusion Combo Benchmark

Date: 2026-06-19

## Scope

Documents the trend-continuation gate in `ChanVolumeFusionStrategy` and the new `chan_offensive_fusion_stack` portfolio preset.

## Verification

- Red/green tests for weak-volume trend-hold behavior.
- Portfolio preset API test.
- Full Python test suite.
- Frontend tests and build.

## Fixed Six-Stock Benchmark

Paste the standalone and offensive preset benchmark tables generated in Step 1.

## STAR Supplemental Benchmark

Paste the STAR summary line and table generated in Step 2.

## Interpretation

State whether average return, best return, worst return, and drawdown improved versus `docs/qa/2026-06-19-chan-volume-fusion-benchmark.md`.
```

- [ ] **Step 4: Update durable docs**

Add a concise completed item to `docs/context/pending-features.md` under implemented strategy work. Update `README.md` and `strategies/README.md` only if the new preset or offensive parameters need user-facing mention.

### Task 5: Verification, Browser Acceptance, And Commit

**Files:**
- Test: whole repo
- Create: `docs/qa/screenshots/2026-06-19-chan-offensive-fusion-combo_desktop_1440.png`
- Create: `docs/qa/screenshots/2026-06-19-chan-offensive-fusion-combo_mobile_390.png`

- [ ] **Step 1: Run targeted tests**

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_api_routes.py tests/test_portfolio.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full backend tests**

```bash
PYTHONPATH=src python -m pytest
```

Expected: PASS.

- [ ] **Step 3: Run frontend checks**

```bash
cd frontend && npm test
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 4: Browser acceptance screenshot**

Run:

```bash
./scripts/run_app.sh
node scripts/capture_app_screenshots.mjs --url http://127.0.0.1:5173 --out-dir docs/qa/screenshots --prefix 2026-06-19-chan-offensive-fusion-combo
```

Confirm `/api/bootstrap` exposes `chan_offensive_fusion_stack`:

```bash
curl -s http://127.0.0.1:8000/api/bootstrap | python -c 'import json, sys; payload=json.load(sys.stdin); print(next(p["name"] for p in payload["portfolio_presets"] if p["id"] == "chan_offensive_fusion_stack"))'
```

Expected output:

```text
缠论进攻融合组合
```

- [ ] **Step 5: Commit implementation**

```bash
git status --short
git add README.md strategies/README.md docs/context/pending-features.md docs/qa/2026-06-19-chan-offensive-fusion-combo-benchmark.md docs/qa/screenshots/2026-06-19-chan-offensive-fusion-combo_*.png src/ai_trade_system/strategies/popular.py src/ai_trade_system/strategy_registry.py src/ai_trade_system/portfolio_presets.py tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_api_routes.py
git commit -m "feat: add offensive chan fusion combo"
```

Expected: commit succeeds and `git status --short` is clean.
