from datetime import date

from ai_trade_system.market import Bar
from ai_trade_system.strategies.popular import (
    BollingerMeanReversionStrategy,
    DonchianBreakoutStrategy,
    PriceMomentumStrategy,
    RsiMeanReversionStrategy,
)
from ai_trade_system.strategy_registry import discover_strategies


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


def test_registry_includes_popular_builtin_strategies():
    names = {spec.name for spec in discover_strategies(user_dir="/tmp/nonexistent-ai-trade-strategies")}

    assert {
        "BollingerMeanReversionStrategy",
        "DonchianBreakoutStrategy",
        "PriceMomentumStrategy",
        "RsiMeanReversionStrategy",
    }.issubset(names)


def test_rsi_mean_reversion_buys_oversold_and_sells_overbought():
    strategy = RsiMeanReversionStrategy("000001", rsi_period=3, oversold=35, overbought=65, trade_size=100)
    closes = [10, 9, 8, 7, 8, 9, 10]
    signals = [signal for index, close in enumerate(closes, start=1) for signal in strategy.on_bar(make_bar(index, close))]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[0].reason == "rsi_oversold"
    assert signals[1].reason == "rsi_overbought"


def test_bollinger_mean_reversion_buys_lower_band_and_sells_middle_reversion():
    strategy = BollingerMeanReversionStrategy("000001", window=3, num_std=1.0, trade_size=100)
    closes = [10, 10, 10, 8, 10]
    signals = [signal for index, close in enumerate(closes, start=1) for signal in strategy.on_bar(make_bar(index, close))]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[0].reason == "below_lower_band"
    assert signals[1].reason == "reverted_to_middle_band"


def test_donchian_breakout_buys_new_high_and_sells_exit_breakdown():
    strategy = DonchianBreakoutStrategy("000001", entry_window=3, exit_window=2, trade_size=100)
    closes = [10, 11, 12, 13, 11, 10]
    signals = [signal for index, close in enumerate(closes, start=1) for signal in strategy.on_bar(make_bar(index, close))]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[0].reason == "donchian_breakout"
    assert signals[1].reason == "donchian_exit"


def test_price_momentum_buys_strength_and_sells_weakness():
    strategy = PriceMomentumStrategy("000001", lookback=3, entry_threshold=0.10, exit_threshold=-0.05, trade_size=100)
    closes = [10, 10, 10, 12, 9]
    signals = [signal for index, close in enumerate(closes, start=1) for signal in strategy.on_bar(make_bar(index, close))]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[0].reason == "positive_momentum"
    assert signals[1].reason == "negative_momentum"
