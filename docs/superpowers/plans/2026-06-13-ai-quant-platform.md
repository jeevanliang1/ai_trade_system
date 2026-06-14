# AI Quant Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, operable A-share quant research platform with strategy creation, portfolio strategy composition, backtesting, paper replay, risk controls, and mock LLM-assisted research.

**Architecture:** Keep the pure Python strategy core and extend it with focused domain modules for indicators, analytics, portfolio aggregation, risk guardrails, and LLM insights. Rebuild the Streamlit app into a research-workbench layout that composes the existing services and the new modules without adding live trading behavior.

**Tech Stack:** Python 3.10+, pandas, Streamlit, Plotly, pytest, existing `ai_trade_system` modules.

---

## File Structure

- Create `src/ai_trade_system/indicators.py`: technical indicator series and latest snapshot.
- Create `src/ai_trade_system/analytics.py`: backtest metrics, drawdown, and trade statistics.
- Create `src/ai_trade_system/risk.py`: deterministic risk guardrail summaries.
- Create `src/ai_trade_system/portfolio.py`: multi-strategy weighted signal aggregation and portfolio strategy adapter.
- Create `src/ai_trade_system/llm.py`: prompt snapshots, mock provider, and structured AI insights.
- Create `src/ai_trade_system/web/components.py`: Streamlit CSS, panels, compact metric helpers, and shared chart helpers.
- Modify `src/ai_trade_system/web/view_models.py`: add frames for indicators, analytics, portfolio entries, risk status, and AI insight.
- Modify `src/ai_trade_system/web/app.py`: replace the simple tab UI with the professional research-workbench platform.
- Modify `docs/architecture.md`, `docs/context/current-system-state.md`, and `docs/runbooks/web-console.md`: document the new platform workflow.
- Add tests:
  - `tests/test_indicators.py`
  - `tests/test_analytics.py`
  - `tests/test_risk.py`
  - `tests/test_portfolio.py`
  - `tests/test_llm.py`

## Task 1: Technical Indicators

**Files:**

- Create: `src/ai_trade_system/indicators.py`
- Test: `tests/test_indicators.py`

- [ ] **Step 1: Write failing tests**

```python
from datetime import date, timedelta

from ai_trade_system.indicators import latest_indicator_snapshot, simple_moving_average
from ai_trade_system.market import Bar


def _bars(closes):
    start = date(2024, 1, 1)
    return [
        Bar("000001", "SZSE", start + timedelta(days=i), close - 1, close + 1, close - 2, close, 1000 + i, 10000 + i)
        for i, close in enumerate(closes)
    ]


def test_simple_moving_average_returns_none_until_window_is_full():
    assert simple_moving_average([10, 12, 14], 2) == [None, 11.0, 13.0]


def test_latest_indicator_snapshot_summarizes_trend_momentum_and_risk():
    snapshot = latest_indicator_snapshot(_bars([10, 11, 12, 13, 14, 15, 16]), short_window=3, long_window=5)

    assert snapshot.symbol == "000001"
    assert snapshot.close_price == 16
    assert snapshot.short_ma == 15
    assert snapshot.long_ma == 14
    assert snapshot.trend == "bullish"
    assert snapshot.momentum > 0
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_indicators.py -v
```

Expected: import failure for `ai_trade_system.indicators`.

- [ ] **Step 3: Implement indicators**

Create `IndicatorSnapshot` dataclass and functions:

- `simple_moving_average(values, window)`
- `rate_of_change(values, window)`
- `relative_strength_index(values, window=14)`
- `bollinger_bands(values, window=20, deviations=2.0)`
- `max_drawdown_from_closes(values)`
- `latest_indicator_snapshot(bars, short_window=20, long_window=60)`

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_indicators.py -v
```

Expected: all tests pass.

## Task 2: Backtest Analytics

**Files:**

- Create: `src/ai_trade_system/analytics.py`
- Test: `tests/test_analytics.py`

- [ ] **Step 1: Write failing tests**

```python
from datetime import date

from ai_trade_system.analytics import calculate_backtest_metrics, drawdown_series
from ai_trade_system.backtest import EquityPoint
from ai_trade_system.paper import Trade


def test_drawdown_series_tracks_peak_to_trough_loss():
    points = [
        EquityPoint(date(2024, 1, 1), 100.0, 100.0, 10.0),
        EquityPoint(date(2024, 1, 2), 120.0, 120.0, 12.0),
        EquityPoint(date(2024, 1, 3), 90.0, 90.0, 9.0),
    ]

    assert drawdown_series(points)[-1].drawdown_pct == -25.0


def test_calculate_backtest_metrics_counts_trades_and_return():
    points = [
        EquityPoint(date(2024, 1, 1), 100.0, 100.0, 10.0),
        EquityPoint(date(2024, 1, 2), 110.0, 90.0, 11.0),
    ]
    trades = [Trade("buy", "000001", 10.0, 100, 0.3, date(2024, 1, 1))]

    metrics = calculate_backtest_metrics(points, trades, initial_cash=100.0)

    assert metrics.total_return_pct == 10.0
    assert metrics.trade_count == 1
    assert metrics.final_equity == 110.0
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_analytics.py -v
```

Expected: import failure for `ai_trade_system.analytics`.

- [ ] **Step 3: Implement analytics**

Create dataclasses:

- `DrawdownPoint(trading_day, equity, drawdown_pct)`
- `BacktestMetrics(final_equity, total_return_pct, annualized_return_pct, max_drawdown_pct, trade_count, win_rate_pct, profit_factor, exposure_pct)`

Implement:

- `drawdown_series(equity_curve)`
- `calculate_backtest_metrics(equity_curve, trades, initial_cash)`

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_analytics.py -v
```

Expected: all tests pass.

## Task 3: Risk Guardrails

**Files:**

- Create: `src/ai_trade_system/risk.py`
- Test: `tests/test_risk.py`

- [ ] **Step 1: Write failing tests**

```python
from ai_trade_system.risk import RiskGuardrailConfig, evaluate_risk_guardrails


def test_risk_guardrails_warn_when_drawdown_breaches_limit():
    status = evaluate_risk_guardrails(
        metrics={"max_drawdown_pct": -22.5},
        config=RiskGuardrailConfig(max_drawdown_pct=20.0, max_order_cash=50000, min_cash_balance=0),
    )

    assert status.ok is False
    assert "最大回撤" in status.warnings[0]


def test_risk_guardrails_pass_when_metrics_inside_limits():
    status = evaluate_risk_guardrails(
        metrics={"max_drawdown_pct": -8.0},
        config=RiskGuardrailConfig(max_drawdown_pct=20.0, max_order_cash=50000, min_cash_balance=0),
    )

    assert status.ok is True
    assert status.warnings == []
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_risk.py -v
```

Expected: import failure for `ai_trade_system.risk`.

- [ ] **Step 3: Implement risk**

Create:

- `RiskGuardrailConfig`
- `RiskGuardrailStatus`
- `evaluate_risk_guardrails(metrics, config)`

The implementation should treat drawdown inputs as negative percentages and compare absolute breach magnitude to the configured positive threshold.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_risk.py -v
```

Expected: all tests pass.

## Task 4: Portfolio Strategy Aggregation

**Files:**

- Create: `src/ai_trade_system/portfolio.py`
- Test: `tests/test_portfolio.py`

- [ ] **Step 1: Write failing tests**

```python
from ai_trade_system.market import Signal
from ai_trade_system.portfolio import PortfolioStrategy, StrategyAllocation
from ai_trade_system.strategy import Strategy


class BuyStrategy(Strategy):
    def on_bar(self, bar):
        return [Signal("buy", bar.symbol, bar.close_price, 100, "buy")]


class SellStrategy(Strategy):
    def on_bar(self, bar):
        return [Signal("sell", bar.symbol, bar.close_price, 100, "sell")]


def test_weighted_vote_keeps_buy_when_buy_weight_is_larger(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("buy", BuyStrategy(), 0.7),
            StrategyAllocation("sell", SellStrategy(), 0.3),
        ],
        mode="weighted_vote",
    )

    signals = strategy.on_bar(sample_bar)

    assert signals[0].action == "buy"
    assert signals[0].volume == 100
    assert "portfolio_weighted_vote" in signals[0].reason


def test_equal_vote_returns_no_signal_on_tie(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("buy", BuyStrategy(), 1.0),
            StrategyAllocation("sell", SellStrategy(), 1.0),
        ],
        mode="equal_vote",
    )

    assert strategy.on_bar(sample_bar) == []
```

Add a local `sample_bar` fixture in the same test file.

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_portfolio.py -v
```

Expected: import failure for `ai_trade_system.portfolio`.

- [ ] **Step 3: Implement portfolio**

Create:

- `StrategyAllocation(name, strategy, weight, enabled=True)`
- `PortfolioSignalBreakdown`
- `PortfolioStrategy(Strategy)`

Support modes:

- `weighted_vote`: compare weighted buy and sell scores.
- `equal_vote`: compare one vote per enabled strategy.
- `first_active`: return the first enabled strategy signal.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_portfolio.py -v
```

Expected: all tests pass.

## Task 5: Mock LLM Research Module

**Files:**

- Create: `src/ai_trade_system/llm.py`
- Test: `tests/test_llm.py`

- [ ] **Step 1: Write failing tests**

```python
from datetime import date

from ai_trade_system.indicators import IndicatorSnapshot
from ai_trade_system.llm import LLMResearchRequest, MockLLMProvider, build_research_prompt


def _snapshot():
    return IndicatorSnapshot(
        symbol="000001",
        trading_day=date(2024, 1, 5),
        close_price=12.0,
        short_ma=11.0,
        long_ma=10.0,
        rsi=55.0,
        momentum=9.0,
        drawdown_pct=-3.0,
        trend="bullish",
    )


def test_build_research_prompt_contains_technical_and_information_inputs():
    request = LLMResearchRequest(
        symbol="000001",
        horizon="5个交易日",
        indicator_snapshot=_snapshot(),
        information_notes=["政策支持流动性改善"],
        risk_context={"max_drawdown_pct": 20},
        prompt_mode="balanced",
    )

    prompt = build_research_prompt(request)

    assert "技术指标" in prompt
    assert "信息面" in prompt
    assert "政策支持流动性改善" in prompt


def test_mock_llm_provider_returns_structured_bullish_insight():
    request = LLMResearchRequest(
        symbol="000001",
        horizon="5个交易日",
        indicator_snapshot=_snapshot(),
        information_notes=["政策支持流动性改善"],
        risk_context={"max_drawdown_pct": 20},
        prompt_mode="balanced",
    )

    insight = MockLLMProvider().generate_insight(request)

    assert insight.direction == "bullish"
    assert insight.confidence >= 70
    assert insight.provider == "MockLLMProvider"
```

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_llm.py -v
```

Expected: import failure for `ai_trade_system.llm`.

- [ ] **Step 3: Implement LLM module**

Create dataclasses:

- `LLMResearchRequest`
- `LLMInsight`

Create:

- `build_research_prompt(request)`
- `MockLLMProvider.generate_insight(request)`

Mock logic should be deterministic and derived from trend, momentum, RSI/drawdown risk, and positive or negative information-side terms.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_llm.py -v
```

Expected: all tests pass.

## Task 6: View Models

**Files:**

- Modify: `src/ai_trade_system/web/view_models.py`
- Test: `tests/test_web_view_models.py`

- [ ] **Step 1: Add failing tests**

Add tests for:

- `indicator_snapshot_to_frame`
- `drawdowns_to_frame`
- `metrics_to_frame`
- `llm_insight_to_sections`

- [ ] **Step 2: Verify tests fail**

Run:

```bash
python -m pytest tests/test_web_view_models.py -v
```

Expected: missing function failures.

- [ ] **Step 3: Implement view-model helpers**

Add conversion helpers that return pandas frames or plain dictionaries suitable for Streamlit rendering. Preserve existing helper names and outputs.

- [ ] **Step 4: Verify tests pass**

Run:

```bash
python -m pytest tests/test_web_view_models.py -v
```

Expected: all tests pass.

## Task 7: Streamlit Research Workbench

**Files:**

- Create: `src/ai_trade_system/web/components.py`
- Modify: `src/ai_trade_system/web/app.py`
- Test: smoke through import and existing web view-model tests.

- [ ] **Step 1: Add a lightweight import smoke test**

Add to `tests/test_web_view_models.py` or a new `tests/test_web_app_import.py`:

```python
def test_web_app_imports():
    import ai_trade_system.web.app as app

    assert callable(app.main)
```

- [ ] **Step 2: Verify test state**

Run:

```bash
python -m pytest tests/test_web_app_import.py tests/test_web_view_models.py -v
```

Expected: import still passes before the large UI rewrite; this guards against breaking module import during the rewrite.

- [ ] **Step 3: Implement shared components**

Create helpers:

- `apply_platform_theme()`
- `section_header(title, caption=None)`
- `status_pill(label, tone="neutral")`
- `metric_strip(items)`

Use Streamlit markdown/CSS only; do not introduce a separate frontend framework.

- [ ] **Step 4: Rebuild app layout**

Replace the current simple tab surface with:

- left navigation-like sidebar and compact top status area.
- tabs: `总览`, `数据中心`, `策略工坊`, `组合实验室`, `回测中心`, `AI研究员`, `纸面交易`, `风控`.
- right inspector on research/backtest views for AI and risk status.
- chart and table composition matching the selected workbench concept.

- [ ] **Step 5: Verify import and full tests**

Run:

```bash
python -m pytest
```

Expected: all tests pass.

## Task 8: Documentation and Sedimentation

**Files:**

- Modify: `docs/architecture.md`
- Modify: `docs/context/current-system-state.md`
- Modify: `docs/runbooks/web-console.md`
- Optional: Modify `README.md` if user-facing commands or scope changed.

- [ ] **Step 1: Update architecture docs**

Document new modules and LLM research flow.

- [ ] **Step 2: Update current system state**

Document the platform surface, still noting no live trading.

- [ ] **Step 3: Update runbook**

Document the new UI workflow and mock LLM module.

- [ ] **Step 4: Verify docs**

Run:

```bash
test -s docs/architecture.md
test -s docs/context/current-system-state.md
test -s docs/runbooks/web-console.md
```

Expected: all commands exit 0.

## Task 9: Rendered UI Verification

**Files:**

- No committed source changes unless QA reveals defects.

- [ ] **Step 1: Start Streamlit**

Run:

```bash
./scripts/run_web.sh
```

Expected: Streamlit serves the app at `http://localhost:8501`.

- [ ] **Step 2: Browser QA**

Verify:

- app loads and is not blank.
- no framework error overlay.
- no relevant console errors.
- primary first viewport resembles the selected Strategy Research Workbench concept.
- tabs render meaningful content.
- data load path works with existing CSV or shows a useful empty state.
- strategy creation/editing controls are present.
- portfolio composition controls are present.
- mock AI insight can be generated from visible inputs.

- [ ] **Step 3: Final verification**

Run:

```bash
python -m pytest
```

Expected: all tests pass.

