from datetime import date

from ai_trade_system.backtest import EquityPoint
from ai_trade_system.analytics import BacktestMetrics, DrawdownPoint
from ai_trade_system.indicators import IndicatorSnapshot
from ai_trade_system.llm import LLMInsight
from ai_trade_system.market import Bar
from ai_trade_system.paper import Trade
from ai_trade_system.web.view_models import (
    bars_to_frame,
    drawdowns_to_frame,
    equity_curve_to_frame,
    indicator_snapshot_to_frame,
    llm_insight_to_sections,
    metrics_to_frame,
    paper_events_to_frames,
    strategy_signals_to_frame,
    trades_to_frame,
)
from ai_trade_system.strategies.dual_moving_average import DualMovingAverageStrategy


def test_bars_to_frame_sorts_bars_and_exposes_price_columns():
    bars = [
        Bar("000001", "SZSE", date(2024, 1, 3), 12, 13, 11, 12.5, 1000, 12_500),
        Bar("000001", "SZSE", date(2024, 1, 2), 10, 11, 9, 10.5, 800, 8_400),
    ]

    frame = bars_to_frame(bars)

    assert list(frame["trading_day"]) == [date(2024, 1, 2), date(2024, 1, 3)]
    assert list(frame.columns) == [
        "symbol",
        "exchange",
        "trading_day",
        "open_price",
        "high_price",
        "low_price",
        "close_price",
        "volume",
        "turnover",
    ]


def test_equity_curve_and_trades_to_frame_handle_empty_inputs():
    assert list(equity_curve_to_frame([]).columns) == ["trading_day", "equity", "cash", "close_price"]
    assert trades_to_frame([]).empty
    assert list(trades_to_frame([]).columns) == [
        "trading_day",
        "side",
        "symbol",
        "price",
        "volume",
        "commission",
        "notional",
    ]


def test_trades_to_frame_includes_notional():
    frame = trades_to_frame([Trade("buy", "000001", 10.5, 200, 0.63, date(2024, 1, 2))])

    assert frame.iloc[0]["trading_day"] == date(2024, 1, 2)
    assert frame.iloc[0]["side"] == "buy"
    assert frame.iloc[0]["notional"] == 2100


def test_paper_events_to_frames_splits_orders_and_equity_events():
    events = [
        {"event": "service_started"},
        {
            "event": "order_accepted",
            "side": "buy",
            "symbol": "000001",
            "price": 10,
            "volume": 100,
            "reason": "",
            "trading_day": "2024-01-02",
        },
        {"event": "equity", "trading_day": "2024-01-02", "equity": 100_100, "cash": 99_000},
        {"event": "service_stopped", "final_equity": 100_100},
    ]

    orders, equity, summary = paper_events_to_frames(events)

    assert len(orders) == 1
    assert len(equity) == 1
    assert summary["final_equity"] == 100_100


def test_equity_curve_to_frame_preserves_equity_values():
    frame = equity_curve_to_frame([EquityPoint(date(2024, 1, 2), 100_500, 99_500, 10.5)])

    assert frame.iloc[0]["equity"] == 100_500


def test_strategy_signals_to_frame_shows_signal_dates_actions_and_reasons():
    bars = [
        Bar("000001", "SZSE", date(2024, 1, 1), 10, 10, 10, 10, 1000, 10_000),
        Bar("000001", "SZSE", date(2024, 1, 2), 11, 11, 11, 11, 1000, 11_000),
        Bar("000001", "SZSE", date(2024, 1, 3), 12, 12, 12, 12, 1000, 12_000),
        Bar("000001", "SZSE", date(2024, 1, 4), 11, 11, 11, 11, 1000, 11_000),
        Bar("000001", "SZSE", date(2024, 1, 5), 10, 10, 10, 10, 1000, 10_000),
    ]
    strategy = DualMovingAverageStrategy("000001", fast_window=2, slow_window=3, trade_size=100)

    frame = strategy_signals_to_frame(bars, strategy)

    assert list(frame.columns) == ["trading_day", "action", "symbol", "price", "volume", "reason"]
    assert list(frame["action"]) == ["buy", "sell"]
    assert list(frame["trading_day"]) == [date(2024, 1, 3), date(2024, 1, 5)]


def test_indicator_snapshot_to_frame_exposes_latest_technical_state():
    snapshot = IndicatorSnapshot("000001", date(2024, 1, 5), 12, 11, 10, 55, 9, -3, "bullish")

    frame = indicator_snapshot_to_frame(snapshot)

    assert list(frame.columns) == ["metric", "value"]
    assert "趋势" in list(frame["metric"])
    assert "bullish" in list(frame["value"])


def test_metrics_and_drawdowns_to_frame_support_dashboard_tables():
    metrics = BacktestMetrics(
        final_equity=110,
        total_return_pct=10,
        annualized_return_pct=12,
        benchmark_return_pct=6,
        excess_return_pct=4,
        annual_volatility_pct=14,
        sharpe_ratio=0.86,
        max_drawdown_pct=-8,
        trade_count=3,
        win_rate_pct=50,
        profit_factor=1.5,
        exposure_pct=30,
    )
    drawdowns = [DrawdownPoint(date(2024, 1, 2), 100, -5)]

    metric_frame = metrics_to_frame(metrics)
    drawdown_frame = drawdowns_to_frame(drawdowns)

    assert metric_frame.iloc[0]["metric"] == "最终权益"
    assert "基准收益(%)" in list(metric_frame["metric"])
    assert "夏普比率" in list(metric_frame["metric"])
    assert drawdown_frame.iloc[0]["drawdown_pct"] == -5


def test_llm_insight_to_sections_keeps_evidence_and_risk_separate():
    insight = LLMInsight(
        symbol="000001",
        horizon="5个交易日",
        direction="bullish",
        confidence=76,
        suggested_action="buy",
        technical_evidence=["均线多头"],
        information_evidence=["政策支持"],
        risk_warnings=["控制仓位"],
        prompt_version="v1",
        provider="Mock",
        created_at="2024-01-01T00:00:00Z",
    )

    sections = llm_insight_to_sections(insight)

    assert sections["summary"]["direction"] == "bullish"
    assert sections["technical_evidence"] == ["均线多头"]
    assert sections["risk_warnings"] == ["控制仓位"]
