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
