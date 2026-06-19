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


class NoSignalStrategy(Strategy):
    def on_bar(self, bar):
        return []


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


def test_weighted_vote_records_strategy_signal_contributions(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("buy", BuyStrategy(), 0.7),
            StrategyAllocation("sell", SellStrategy(), 0.3),
        ],
        mode="weighted_vote",
    )

    strategy.on_bar(sample_bar)

    assert strategy.last_breakdown.buy_score == 0.7
    assert strategy.last_breakdown.sell_score == 0.3
    assert len(strategy.last_breakdown.contributions) == 2
    buy, sell = strategy.last_breakdown.contributions
    assert buy.allocation_index == 0
    assert buy.name == "buy"
    assert buy.action == "buy"
    assert buy.score == 0.7
    assert buy.weight == 0.7
    assert buy.volume == 100
    assert buy.reason == "buy"
    assert buy.selected is True
    assert sell.allocation_index == 1
    assert sell.name == "sell"
    assert sell.action == "sell"
    assert sell.score == 0.3
    assert sell.selected is False


def test_first_active_records_selected_and_ignored_contributions(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("buy", BuyStrategy(), 0.7),
            StrategyAllocation("sell", SellStrategy(), 0.3),
        ],
        mode="first_active",
    )

    signals = strategy.on_bar(sample_bar)

    assert signals[0].action == "buy"
    assert len(strategy.last_breakdown.contributions) == 2
    assert strategy.last_breakdown.contributions[0].selected is True
    assert strategy.last_breakdown.contributions[0].allocation_index == 0
    assert strategy.last_breakdown.contributions[1].selected is False
    assert strategy.last_breakdown.contributions[1].allocation_index == 1


def test_equal_vote_returns_no_signal_on_tie(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("buy", BuyStrategy(), 1.0),
            StrategyAllocation("sell", SellStrategy(), 1.0),
        ],
        mode="equal_vote",
    )

    assert strategy.on_bar(sample_bar) == []


def test_primary_assist_ignores_auxiliary_only_signal(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("primary", NoSignalStrategy(), 1.0),
            StrategyAllocation("aux", BuyStrategy(), 0.2),
        ],
        mode="primary_assist",
    )

    assert strategy.on_bar(sample_bar) == []
    assert strategy.last_breakdown.buy_score == 0.2
    assert strategy.last_breakdown.contributions[0].selected is False


def test_primary_assist_vetoes_conflicting_auxiliary_buy(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("primary", BuyStrategy(), 1.0),
            StrategyAllocation("aux", SellStrategy(), 0.2),
        ],
        mode="primary_assist",
    )

    assert strategy.on_bar(sample_bar) == []
    assert strategy.last_breakdown.buy_score == 1.0
    assert strategy.last_breakdown.sell_score == 0.2
    assert all(not contribution.selected for contribution in strategy.last_breakdown.contributions)


def test_primary_assist_boosts_aligned_auxiliary_buy(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("primary", BuyStrategy(), 1.0),
            StrategyAllocation("aux", BuyStrategy(), 0.2),
        ],
        mode="primary_assist",
    )

    signals = strategy.on_bar(sample_bar)

    assert signals[0].action == "buy"
    assert signals[0].volume == 108
    assert signals[0].reason == "portfolio_primary_assist"
    assert all(contribution.selected for contribution in strategy.last_breakdown.contributions)


def test_primary_assist_keeps_primary_sell_when_auxiliary_conflicts(sample_bar):
    strategy = PortfolioStrategy(
        [
            StrategyAllocation("primary", SellStrategy(), 1.0),
            StrategyAllocation("aux", BuyStrategy(), 0.2),
        ],
        mode="primary_assist",
    )

    signals = strategy.on_bar(sample_bar)

    assert signals[0].action == "sell"
    assert signals[0].volume == 100
    assert strategy.last_breakdown.contributions[0].selected is True
    assert strategy.last_breakdown.contributions[1].selected is False
