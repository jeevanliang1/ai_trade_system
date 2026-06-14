from datetime import date

import pytest

from ai_trade_system.market import Bar, Signal
from ai_trade_system.portfolio import PortfolioStrategy, StrategyAllocation
from ai_trade_system.strategy import Strategy


@pytest.fixture
def sample_bar():
    return Bar("000001", "SZSE", date(2024, 1, 1), 10.0, 11.0, 9.0, 10.5, 1000, 10000)


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
