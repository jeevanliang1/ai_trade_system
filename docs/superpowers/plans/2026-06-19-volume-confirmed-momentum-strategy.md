# Volume-Confirmed Momentum Strategy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a built-in volume-confirmed price momentum strategy and validate it against persistent three-year A-share data for 中芯国际 and 五粮液.

**Architecture:** Implement the strategy as a new class in the existing built-in `popular.py` strategy module, then expose it through `strategy_registry` metadata and parameter guidance. Benchmark data should use the existing managed data layout under `data/market/a_share/{exchange}/{code}/`, with repeatable result documentation under `docs/qa/`.

**Tech Stack:** Python 3, pytest, existing `Strategy`/`Signal`/`run_backtest` engine, existing AKShare-backed `data_manager`, Markdown QA docs.

---

## File Structure

- Modify `tests/test_builtin_popular_strategies.py`: add TDD coverage for entry, volume rejection, exits, and backtestability.
- Modify `tests/test_strategy_registry.py`: add registry/API-facing metadata and parameter guidance checks.
- Modify `src/ai_trade_system/strategies/popular.py`: add `VolumeConfirmedMomentumStrategy`.
- Modify `src/ai_trade_system/strategy_registry.py`: add built-in strategy spec and parameter guidance.
- Modify `docs/context/pending-features.md`: remove the completed strategy item and keep the Signal Radar follow-up as the next recommended feature.
- Create `docs/qa/2026-06-19-volume-momentum-benchmark.md`: record fixed symbols, data paths, commands, and benchmark backtest results.
- Generate ignored local data files under `data/market/a_share/SSE/688981/` and `data/market/a_share/SZSE/000858/`.

## Task 1: Strategy Behavior Tests

**Files:**
- Modify: `tests/test_builtin_popular_strategies.py`
- Later modify: `src/ai_trade_system/strategies/popular.py`

- [ ] **Step 1: Add failing strategy behavior tests**

Add `VolumeConfirmedMomentumStrategy` to the import list:

```python
from ai_trade_system.strategies.popular import (
    BollingerMeanReversionStrategy,
    ChanRsiResearchStrategy,
    DonchianBreakoutStrategy,
    PriceMomentumStrategy,
    RsiMeanReversionStrategy,
    VolumeConfirmedMomentumStrategy,
)
```

Add a volume-aware helper and tests:

```python
def make_volume_bar(day: int, close: float, volume: float) -> Bar:
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=date(2024, 1, day),
        open_price=close,
        high_price=close,
        low_price=close,
        close_price=close,
        volume=volume,
        turnover=close * volume,
    )


def collect_volume_momentum_signals(closes: list[float], volumes: list[float], **kwargs):
    strategy = VolumeConfirmedMomentumStrategy("000001", trade_size=100, **kwargs)
    return [
        signal
        for index, (close, volume) in enumerate(zip(closes, volumes), start=1)
        for signal in strategy.on_bar(make_volume_bar(index, close, volume))
    ]


def test_volume_confirmed_momentum_buys_only_when_price_volume_and_trend_pass():
    signals = collect_volume_momentum_signals(
        [10, 10.2, 10.4, 10.6, 11.2],
        [1000, 1000, 1000, 1000, 2200],
        momentum_window=3,
        min_momentum_pct=0.05,
        volume_window=3,
        volume_multiplier=1.5,
        trend_window=3,
        max_holding_bars=5,
    )

    assert [signal.action for signal in signals] == ["buy"]
    assert signals[0].reason == "volume_confirmed_momentum_entry"


def test_volume_confirmed_momentum_rejects_price_momentum_without_volume_expansion():
    signals = collect_volume_momentum_signals(
        [10, 10.2, 10.4, 10.6, 11.2],
        [1000, 1000, 1000, 1000, 1200],
        momentum_window=3,
        min_momentum_pct=0.05,
        volume_window=3,
        volume_multiplier=1.5,
        trend_window=3,
        max_holding_bars=5,
    )

    assert signals == []


def test_volume_confirmed_momentum_sells_when_momentum_weakens():
    signals = collect_volume_momentum_signals(
        [10, 10.2, 10.4, 10.6, 11.2, 10.5],
        [1000, 1000, 1000, 1000, 2200, 1000],
        momentum_window=3,
        min_momentum_pct=0.05,
        volume_window=3,
        volume_multiplier=1.5,
        trend_window=3,
        max_holding_bars=10,
    )

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[1].reason == "momentum_exit"


def test_volume_confirmed_momentum_sells_when_trend_breaks():
    signals = collect_volume_momentum_signals(
        [10, 10.2, 10.4, 10.6, 11.2, 10.0],
        [1000, 1000, 1000, 1000, 2200, 1000],
        momentum_window=3,
        min_momentum_pct=0.05,
        volume_window=3,
        volume_multiplier=1.5,
        trend_window=3,
        max_holding_bars=10,
    )

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[1].reason == "trend_exit"


def test_volume_confirmed_momentum_sells_after_max_holding_bars():
    signals = collect_volume_momentum_signals(
        [10, 10.2, 10.4, 10.6, 11.2, 11.4, 11.6],
        [1000, 1000, 1000, 1000, 2200, 1000, 1000],
        momentum_window=3,
        min_momentum_pct=0.05,
        volume_window=3,
        volume_multiplier=1.5,
        trend_window=3,
        max_holding_bars=2,
    )

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[1].reason == "time_exit"


def test_volume_confirmed_momentum_is_backtestable():
    strategy = VolumeConfirmedMomentumStrategy(
        "000001",
        momentum_window=3,
        min_momentum_pct=0.05,
        volume_window=3,
        volume_multiplier=1.5,
        trend_window=3,
        max_holding_bars=2,
        trade_size=100,
    )
    bars = [
        make_volume_bar(index, close, volume)
        for index, (close, volume) in enumerate(
            zip([10, 10.2, 10.4, 10.6, 11.2, 11.4, 11.6], [1000, 1000, 1000, 1000, 2200, 1000, 1000]),
            start=1,
        )
    ]

    result = run_backtest(bars, strategy)

    assert [trade.side for trade in result.trades] == ["buy", "sell"]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q
```

Expected: FAIL because `VolumeConfirmedMomentumStrategy` cannot be imported.

## Task 2: Strategy Implementation

**Files:**
- Modify: `src/ai_trade_system/strategies/popular.py`
- Test: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add minimal strategy implementation**

Add the class before `_rsi`:

```python
class VolumeConfirmedMomentumStrategy(Strategy):
    def __init__(
        self,
        symbol: str,
        momentum_window: int = 20,
        min_momentum_pct: float = 0.08,
        volume_window: int = 20,
        volume_multiplier: float = 1.5,
        trend_window: int = 60,
        max_holding_bars: int = 20,
        trade_size: int = 100,
    ) -> None:
        self.symbol = symbol
        self.momentum_window = max(1, int(momentum_window))
        self.min_momentum_pct = float(min_momentum_pct)
        self.volume_window = max(1, int(volume_window))
        self.volume_multiplier = max(0.0, float(volume_multiplier))
        self.trend_window = max(1, int(trend_window))
        self.max_holding_bars = max(1, int(max_holding_bars))
        self.trade_size = max(1, int(trade_size))
        self.closes: deque[float] = deque(maxlen=max(self.momentum_window, self.trend_window) + 1)
        self.volumes: deque[float] = deque(maxlen=self.volume_window + 1)
        self.in_position = False
        self.holding_bars = 0

    def on_bar(self, bar: Bar) -> list[Signal]:
        if bar.symbol != self.symbol:
            return []

        previous_closes = list(self.closes)
        previous_volumes = list(self.volumes)
        self.closes.append(bar.close_price)
        self.volumes.append(bar.volume)

        if self.in_position:
            self.holding_bars += 1
            exit_reason = self._exit_reason(bar.close_price, previous_closes)
            if exit_reason:
                self.in_position = False
                self.holding_bars = 0
                return [Signal("sell", bar.symbol, bar.close_price, self.trade_size, exit_reason)]
            return []

        if not self._entry_ready(previous_closes, previous_volumes):
            return []
        if not self._has_price_momentum(bar.close_price, previous_closes):
            return []
        if not self._has_volume_confirmation(bar.volume, previous_volumes):
            return []
        if not self._passes_trend_filter(bar.close_price, previous_closes):
            return []

        self.in_position = True
        self.holding_bars = 0
        return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "volume_confirmed_momentum_entry")]

    def _entry_ready(self, previous_closes: list[float], previous_volumes: list[float]) -> bool:
        return len(previous_closes) >= max(self.momentum_window, self.trend_window) and len(previous_volumes) >= self.volume_window

    def _has_price_momentum(self, close_price: float, previous_closes: list[float]) -> bool:
        base = previous_closes[-self.momentum_window]
        return base > 0 and close_price / base - 1 >= self.min_momentum_pct

    def _has_volume_confirmation(self, volume: float, previous_volumes: list[float]) -> bool:
        if volume <= 0:
            return False
        baseline = mean(previous_volumes[-self.volume_window :])
        return baseline > 0 and volume >= baseline * self.volume_multiplier

    def _passes_trend_filter(self, close_price: float, previous_closes: list[float]) -> bool:
        trend_average = mean(previous_closes[-self.trend_window :])
        return close_price > trend_average

    def _exit_reason(self, close_price: float, previous_closes: list[float]) -> str | None:
        if len(previous_closes) >= self.momentum_window:
            base = previous_closes[-self.momentum_window]
            if base > 0 and close_price <= base:
                return "momentum_exit"
        if len(previous_closes) >= self.trend_window and close_price < mean(previous_closes[-self.trend_window :]):
            return "trend_exit"
        if self.holding_bars >= self.max_holding_bars:
            return "time_exit"
        return None
```

- [ ] **Step 2: Run strategy tests to verify GREEN**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py -q
```

Expected: PASS.

## Task 3: Registry Metadata And Parameter Guidance

**Files:**
- Modify: `src/ai_trade_system/strategy_registry.py`
- Modify: `tests/test_strategy_registry.py`
- Modify: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Add failing registry assertions**

In `tests/test_builtin_popular_strategies.py`, add `"VolumeConfirmedMomentumStrategy"` to the expected built-in names set.

In `tests/test_strategy_registry.py`, add:

```python
def test_volume_confirmed_momentum_strategy_metadata_and_parameter_guidance():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(item for item in specs if item.name == "VolumeConfirmedMomentumStrategy")

    assert spec.display_name == "量价动量策略"
    assert "成交量放大" in spec.description

    params = {param.name: param for param in inspect_strategy_parameters(spec)}
    assert params["momentum_window"].display_name == "动量回看周期"
    assert "价格涨幅" in params["min_momentum_pct"].description
    assert "成交量" in params["volume_multiplier"].description
    assert "持仓" in params["max_holding_bars"].description
```

If the test file already imports `discover_strategies` and `inspect_strategy_parameters`, reuse the existing imports instead of duplicating them.

- [ ] **Step 2: Run registry tests to verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py tests/test_builtin_popular_strategies.py::test_registry_includes_popular_builtin_strategies -q
```

Expected: FAIL because the new strategy is not registered yet.

- [ ] **Step 3: Register metadata and guidance**

Add this `StrategySpec` to `BUILTIN_STRATEGIES` in `src/ai_trade_system/strategy_registry.py`:

```python
StrategySpec(
    id="builtin:popular:VolumeConfirmedMomentumStrategy",
    name="VolumeConfirmedMomentumStrategy",
    class_name="VolumeConfirmedMomentumStrategy",
    source="builtin",
    path=None,
    module_name="ai_trade_system.strategies.popular",
    display_name="量价动量策略",
    description="价格上涨动量、成交量放大和趋势过滤同时满足时买入；动量转弱、跌破趋势或持仓超期时卖出。",
),
```

Add these `PARAMETER_GUIDANCE` entries:

```python
"momentum_window": ParameterGuidance(
    display_name="动量回看周期",
    description="比较当前收盘价和多少个交易日前的收盘价，用来判断价格涨幅是否足够强。",
    increase_effect="调大后更看重中期动量，信号更稳但更慢。",
    decrease_effect="调小后更看重短期动量，信号更快但更容易被噪音影响。",
),
"min_momentum_pct": ParameterGuidance(
    display_name="最小动量涨幅",
    description="当前价格相对回看日前价格至少上涨多少比例才允许入场。",
    increase_effect="调大后只追更强的上涨，交易更少。",
    decrease_effect="调小后更容易触发买入，机会更多但强度要求下降。",
),
"volume_window": ParameterGuidance(
    display_name="成交量基准周期",
    description="计算平均成交量时使用的回看天数。",
    increase_effect="调大后成交量基准更稳定，异常放量确认更严格。",
    decrease_effect="调小后成交量基准更贴近近期变化，信号更敏感。",
),
"volume_multiplier": ParameterGuidance(
    display_name="放量倍数",
    description="当前成交量至少达到历史平均成交量的多少倍，才认为有成交量放大确认。",
    increase_effect="调大后需要更明显放量才买入，交易更少但确认更强。",
    decrease_effect="调小后放量要求降低，信号更多但确认力度下降。",
),
"trend_window": ParameterGuidance(
    display_name="趋势过滤周期",
    description="计算趋势均线时使用的回看天数，当前价格需站上该均线才允许买入。",
    increase_effect="调大后更偏中长期趋势过滤，入场更慢。",
    decrease_effect="调小后趋势过滤更灵敏，入场更早但抗噪更弱。",
),
"max_holding_bars": ParameterGuidance(
    display_name="最大持仓天数",
    description="买入后最多持有多少根日线，超过后即使未触发其他退出条件也会离场。",
    increase_effect="调大后允许趋势运行更久，但可能承受更大回撤。",
    decrease_effect="调小后退出更快，资金周转更快但可能错过后续趋势。",
),
```

- [ ] **Step 4: Run registry tests to verify GREEN**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_strategy_registry.py tests/test_builtin_popular_strategies.py -q
```

Expected: PASS.

## Task 4: Persistent Benchmark Data

**Files:**
- Generate ignored local files under `data/market/a_share/SSE/688981/`
- Generate ignored local files under `data/market/a_share/SZSE/000858/`
- Create: `docs/qa/2026-06-19-volume-momentum-benchmark.md`

- [ ] **Step 1: Fetch fixed three-year data**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.data_manager import update_watchlist_data

stocks = [
    {"code": "688981", "name": "中芯国际", "exchange": "SSE"},
    {"code": "000858", "name": "五粮液", "exchange": "SZSE"},
]
result = update_watchlist_data(
    stocks,
    start_date="20230619",
    end_date="20260619",
    adjust="qfq",
    if_stale=True,
)
print(result)
PY
```

Expected: files are created or skipped as fresh under:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
```

- [ ] **Step 2: Run repeatable benchmark backtests**

Run:

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.strategies.popular import VolumeConfirmedMomentumStrategy

cases = [
    ("688981", "中芯国际", "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"),
    ("000858", "五粮液", "data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv"),
]
for symbol, name, path in cases:
    bars = read_bars_csv(path)
    strategy = VolumeConfirmedMomentumStrategy(symbol=symbol)
    result = run_backtest(bars, strategy, BacktestConfig(initial_cash=100000))
    metrics = calculate_backtest_metrics(result.equity_curve, result.trades, 100000)
    print(
        f"{symbol}\t{name}\trows={len(bars)}\t"
        f"start={bars[0].trading_day}\tend={bars[-1].trading_day}\t"
        f"final_equity={result.final_equity:.2f}\ttrades={len(result.trades)}\t"
        f"return_pct={metrics.total_return_pct:.2f}\tmax_drawdown_pct={metrics.max_drawdown_pct:.2f}"
    )
PY
```

Expected: one summary line per stock with rows, date range, final equity, trades, return, and drawdown; paste the exact observed output into the QA document in Step 3.

- [ ] **Step 3: Document benchmark fixture and results**

Create `docs/qa/2026-06-19-volume-momentum-benchmark.md` with:

```markdown
# Volume Momentum Strategy Benchmark

Date: 2026-06-19

## Fixed Dataset

- 中芯国际: `688981` / `SSE`
- 五粮液: `000858` / `SZSE`
- Requested window: `20230619` to `20260619`
- Adjust: `qfq`

## Local Persistent Paths

- `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

These data files are local benchmark fixtures and are ignored by git through `data/*`. Re-run the update command only when intentionally refreshing the benchmark window.

## Strategy Parameters

Default `VolumeConfirmedMomentumStrategy` parameters:

- `momentum_window=20`
- `min_momentum_pct=0.08`
- `volume_window=20`
- `volume_multiplier=1.5`
- `trend_window=60`
- `max_holding_bars=20`
- `trade_size=100`

## Commands

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.data_manager import update_watchlist_data

stocks = [
    {"code": "688981", "name": "中芯国际", "exchange": "SSE"},
    {"code": "000858", "name": "五粮液", "exchange": "SZSE"},
]
print(update_watchlist_data(stocks, start_date="20230619", end_date="20260619", adjust="qfq", if_stale=True))
PY
```

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.strategies.popular import VolumeConfirmedMomentumStrategy

cases = [
    ("688981", "中芯国际", "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"),
    ("000858", "五粮液", "data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv"),
]
for symbol, name, path in cases:
    bars = read_bars_csv(path)
    result = run_backtest(bars, VolumeConfirmedMomentumStrategy(symbol=symbol), BacktestConfig(initial_cash=100000))
    metrics = calculate_backtest_metrics(result.equity_curve, result.trades, 100000)
    print(symbol, name, len(bars), bars[0].trading_day, bars[-1].trading_day, result.final_equity, len(result.trades), metrics.total_return_pct, metrics.max_drawdown_pct)
PY
```

## Results

- `688981` / 中芯国际: record observed row count, date range, final equity, trade count, total return, and max drawdown from Step 2.
- `000858` / 五粮液: record observed row count, date range, final equity, trade count, total return, and max drawdown from Step 2.
```

## Task 5: Verification And Browser Acceptance

**Files:**
- Modify: `docs/context/pending-features.md`
- Possibly generate screenshot under existing screenshot output directory

- [ ] **Step 1: Run focused Python verification**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full Python suite**

Run:

```bash
PYTHONPATH=src python -m pytest
```

Expected: PASS.

- [ ] **Step 3: Capture React platform screenshot**

Run the app:

```bash
./scripts/run_app.sh
```

Then in another terminal run the existing screenshot script:

```bash
node scripts/capture_app_screenshots.mjs
```

Expected: screenshot files are generated and the strategy is browser-visible through the existing Strategy Workshop strategy list or parameter surface.

- [ ] **Step 4: Update pending features**

In `docs/context/pending-features.md`:

- Remove `Implement the built-in VolumeConfirmedMomentumStrategy...`.
- Keep `After the volume-confirmed momentum strategy is complete, evaluate whether Signal Radar should rank candidates...`.
- Set Next Recommended Feature to that Signal Radar strategy-ranking evaluation.

- [ ] **Step 5: Review changed files**

Run:

```bash
git diff -- src/ai_trade_system/strategies/popular.py src/ai_trade_system/strategy_registry.py tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py docs/context/pending-features.md docs/qa/2026-06-19-volume-momentum-benchmark.md
```

Expected: only strategy, tests, pending-list, and QA benchmark documentation changed.
