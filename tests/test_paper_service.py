from datetime import date

from ai_trade_system.market import Bar
from ai_trade_system.paper_service import PaperTradingService
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


def test_paper_trading_service_records_equity_and_order_events():
    service = PaperTradingService(
        strategy=DualMovingAverageStrategy("000001", fast_window=2, slow_window=3, trade_size=100),
        initial_cash=100_000,
        commission_rate=0.0,
        slippage=0.0,
    )

    events = service.run([make_bar(1, 10), make_bar(2, 11), make_bar(3, 12), make_bar(4, 11), make_bar(5, 10)])

    assert events[0]["event"] == "service_started"
    assert any(event["event"] == "order_accepted" for event in events)
    assert events[-1]["event"] == "service_stopped"
    assert "final_equity" in events[-1]
