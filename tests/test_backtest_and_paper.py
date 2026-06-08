from datetime import date

from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.market import Bar
from ai_trade_system.paper import PaperBroker, RiskLimits
from ai_trade_system.strategies.dual_moving_average import DualMovingAverageStrategy


def make_bar(day: int, close: float) -> Bar:
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=date(2024, 1, day),
        open_price=close,
        high_price=close,
        low_price=close,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def test_paper_broker_rejects_orders_above_single_order_cash_limit():
    broker = PaperBroker(initial_cash=100_000, risk_limits=RiskLimits(max_order_cash=5_000))

    result = broker.buy(symbol="000001", price=10.0, volume=600)

    assert result.accepted is False
    assert "max_order_cash" in result.reason
    assert broker.cash == 100_000
    assert broker.position("000001") == 0


def test_backtest_runs_strategy_and_reports_equity_curve_and_trades():
    bars = [
        make_bar(1, 10),
        make_bar(2, 11),
        make_bar(3, 12),
        make_bar(4, 11),
        make_bar(5, 10),
    ]
    strategy = DualMovingAverageStrategy(symbol="000001", fast_window=2, slow_window=3, trade_size=100)

    result = run_backtest(bars, strategy, BacktestConfig(initial_cash=100_000, commission_rate=0.0, slippage=0.0))

    assert len(result.equity_curve) == 5
    assert result.trades
    assert result.trades[0].trading_day == date(2024, 1, 3)
    assert result.final_equity != 100_000
