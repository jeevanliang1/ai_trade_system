from datetime import date

from ai_trade_system.analytics import calculate_backtest_metrics, calculate_signal_attribution, classify_signal_family, drawdown_series
from ai_trade_system.backtest import EquityPoint, TradeAttribution
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


def test_calculate_backtest_metrics_adds_benchmark_and_volatility_context():
    points = [
        EquityPoint(date(2024, 1, 1), 100.0, 100.0, 10.0),
        EquityPoint(date(2024, 1, 2), 104.0, 92.0, 11.0),
        EquityPoint(date(2024, 1, 3), 102.0, 90.0, 11.5),
        EquityPoint(date(2024, 1, 4), 108.0, 88.0, 12.0),
    ]

    metrics = calculate_backtest_metrics(points, [], initial_cash=100.0)

    assert metrics.total_return_pct == 8.0
    assert metrics.benchmark_return_pct == 20.0
    assert metrics.excess_return_pct == -12.0
    assert metrics.annual_volatility_pct > 0
    assert metrics.sharpe_ratio == round(metrics.annualized_return_pct / metrics.annual_volatility_pct, 4)


def test_classify_signal_family_handles_chan_families():
    reasons = {
        "chan_structure:CHAN_STRUCT_BUY_T1_DIVERGENCE:bottom divergence": ("t1_divergence", "T1背驰"),
        "chan_structure:CHAN_STRUCT_BUY_T2:second buy": ("t2", "T2二买二卖"),
        "chan_structure:CHAN_STRUCT_SELL_T3:third sell": ("t3", "T3三买三卖"),
        "chan_structure:CHAN_STRUCT_BUY_CONFIRM:confirmed divergence": ("divergence_confirm", "背驰确认"),
        "chan_structure:ARMED_CONFIRM:CHAN_STRUCT_BUY_T1_DIVERGENCE->CHAN_STRUCT_BUY_T3:confirmed": (
            "divergence_confirm",
            "背驰确认",
        ),
        "chan_structure:TIME_EXIT:max_holding_bars=15": ("time_exit", "时间退出"),
        "fast_ma_cross_up": ("other", "其他信号"),
    }

    assert {reason: classify_signal_family(reason) for reason in reasons} == reasons


def test_calculate_signal_attribution_summarizes_entry_and_exit_families():
    attributions = [
        TradeAttribution(
            "buy",
            "000001",
            10.0,
            100,
            1.0,
            date(2024, 1, 1),
            "chan_structure:CHAN_STRUCT_BUY_T3:third buy",
            "t3",
            "T3三买三卖",
        ),
        TradeAttribution(
            "sell",
            "000001",
            12.0,
            100,
            1.2,
            date(2024, 1, 2),
            "chan_structure:TIME_EXIT:max_holding_bars=15",
            "time_exit",
            "时间退出",
        ),
        TradeAttribution(
            "buy",
            "000001",
            20.0,
            50,
            0.5,
            date(2024, 1, 3),
            "chan_structure:CHAN_STRUCT_BUY_T2:second buy",
            "t2",
            "T2二买二卖",
        ),
        TradeAttribution(
            "sell",
            "000001",
            18.0,
            50,
            0.45,
            date(2024, 1, 4),
            "chan_structure:CHAN_STRUCT_SELL_T3:third sell",
            "t3",
            "T3三买三卖",
        ),
    ]

    rows = {row.family: row for row in calculate_signal_attribution(attributions, initial_cash=100_000)}

    assert rows["t3"].trade_count == 2
    assert rows["t3"].buy_count == 1
    assert rows["t3"].sell_count == 1
    assert rows["t3"].entry_closed_trades == 1
    assert rows["t3"].entry_realized_pnl == 197.8
    assert rows["t3"].entry_win_rate_pct == 100.0
    assert rows["t3"].exit_closed_trades == 1
    assert rows["t3"].exit_realized_pnl == -100.95
    assert rows["t3"].exit_win_rate_pct == 0.0
    assert rows["t3"].exit_realized_drawdown_pct == -0.1009
    assert rows["t2"].entry_realized_pnl == -100.95
    assert rows["time_exit"].exit_realized_pnl == 197.8
