from datetime import date, timedelta

from ai_trade_system.market import Bar
from ai_trade_system.backtest import run_backtest
from ai_trade_system.strategies.popular import (
    BollingerMeanReversionStrategy,
    ChanStructureStrategy,
    ChanRsiResearchStrategy,
    DonchianBreakoutStrategy,
    PriceMomentumStrategy,
    RsiMeanReversionStrategy,
    VolumeConfirmedMomentumStrategy,
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


def make_chan_bar(index: int, close: float, high: float, low: float) -> Bar:
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=date(2024, 1, 1) + timedelta(days=index),
        open_price=close,
        high_price=high,
        low_price=low,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def make_deep_chan_bars() -> list[Bar]:
    points = [
        (1, 10.0),
        (6, 15.0),
        (11, 12.0),
        (16, 16.0),
        (21, 13.0),
        (26, 17.0),
        (31, 9.0),
        (36, 14.0),
        (41, 8.0),
        (46, 12.0),
        (51, 7.0),
        (86, 18.0),
        (91, 13.0),
        (96, 19.0),
        (101, 6.0),
        (130, 15.0),
        (160, 5.0),
        (190, 14.0),
        (220, 4.0),
    ]
    bars: list[Bar] = []
    for index in range(points[-1][0] + 2):
        if index <= points[0][0]:
            close = points[0][1] + (points[0][0] - index + 1) * 0.2
        elif index >= points[-1][0]:
            close = points[-1][1] - (index - points[-1][0] + 1) * 0.2
        else:
            close = points[-1][1]
            for (left_index, left_price), (right_index, right_price) in zip(points, points[1:]):
                if left_index <= index <= right_index:
                    ratio = (index - left_index) / (right_index - left_index)
                    close = left_price + (right_price - left_price) * ratio
                    break
        close = round(close, 4)
        bars.append(make_chan_bar(index, close, close + 0.1, close - 0.1))
    return bars


def collect_volume_momentum_signals(closes: list[float], volumes: list[float], **kwargs):
    strategy = VolumeConfirmedMomentumStrategy("000001", trade_size=100, **kwargs)
    return [
        signal
        for index, (close, volume) in enumerate(zip(closes, volumes), start=1)
        for signal in strategy.on_bar(make_volume_bar(index, close, volume))
    ]


def test_registry_includes_popular_builtin_strategies():
    names = {spec.name for spec in discover_strategies(user_dir="/tmp/nonexistent-ai-trade-strategies")}

    assert {
        "BollingerMeanReversionStrategy",
        "ChanRsiResearchStrategy",
        "DonchianBreakoutStrategy",
        "PriceMomentumStrategy",
        "RsiMeanReversionStrategy",
        "VolumeConfirmedMomentumStrategy",
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


def test_chan_rsi_research_strategy_buys_from_research_preview_signal():
    strategy = ChanRsiResearchStrategy("000001", min_bars=12, lookback=40, trade_size=100)
    closes = [12.0, 11.4, 10.8, 10.1, 9.8, 10.4, 11.1, 11.6, 10.9, 10.4, 10.8, 11.5, 12.0, 12.4]

    signals = [signal for index, close in enumerate(closes, start=1) for signal in strategy.on_bar(make_bar(index, close))]

    assert [signal.action for signal in signals] == ["buy"]
    assert signals[0].volume == 100
    assert signals[0].reason.startswith("research:")


def test_chan_rsi_research_strategy_is_backtestable():
    strategy = ChanRsiResearchStrategy("000001", min_bars=12, lookback=40, trade_size=100)
    closes = [12.0, 11.4, 10.8, 10.1, 9.8, 10.4, 11.1, 11.6, 10.9, 10.4, 10.8, 11.5, 12.0, 12.4]
    bars = [make_bar(index, close) for index, close in enumerate(closes, start=1)]

    result = run_backtest(bars, strategy)

    assert len(result.trades) == 1
    assert result.trades[0].side == "buy"


def test_chan_structure_strategy_emits_buy_from_structural_buy_signal():
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=8,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=40,
        trade_size=100,
    )
    bars = [
        make_chan_bar(0, 10.0, 10.4, 9.8),
        make_chan_bar(1, 9.4, 9.8, 9.1),
        make_chan_bar(2, 10.4, 10.9, 10.0),
        make_chan_bar(3, 11.6, 12.0, 11.1),
        make_chan_bar(4, 10.8, 11.0, 10.2),
        make_chan_bar(5, 10.1, 10.5, 9.7),
        make_chan_bar(6, 11.5, 12.0, 11.0),
        make_chan_bar(7, 12.8, 13.2, 12.2),
        make_chan_bar(8, 12.6, 12.8, 12.4),
        make_chan_bar(9, 12.5, 12.6, 12.3),
        make_chan_bar(10, 12.3, 12.4, 12.1),
        make_chan_bar(11, 12.8, 13.0, 12.5),
    ]

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy"]
    assert signals[0].volume == 100
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T3")


def test_chan_structure_strategy_emits_sell_after_structural_sell_signal():
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=8,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=40,
        trade_size=100,
    )
    strategy.in_position = True
    bars = [
        make_chan_bar(0, 12.0, 12.4, 11.7),
        make_chan_bar(1, 12.8, 13.2, 12.2),
        make_chan_bar(2, 11.8, 12.1, 11.4),
        make_chan_bar(3, 10.7, 11.1, 10.2),
        make_chan_bar(4, 11.3, 11.7, 10.9),
        make_chan_bar(5, 12.0, 12.4, 11.6),
        make_chan_bar(6, 10.9, 11.3, 10.5),
        make_chan_bar(7, 9.6, 9.7, 9.4),
        make_chan_bar(8, 9.7, 9.8, 9.6),
        make_chan_bar(9, 9.9, 10.0, 9.7),
        make_chan_bar(10, 9.5, 9.8, 9.1),
    ]

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["sell"]
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_SELL_T3")


def test_chan_structure_strategy_emits_confirmation_from_segment_divergence():
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=240,
        min_stroke_bars=4,
        min_rebound_pct=0.02,
        min_signal_score=50,
        trade_size=100,
    )
    strategy.in_position = True

    signals = [signal for bar in make_deep_chan_bars() for signal in strategy.on_bar(bar)]

    assert signals[0].action == "sell"
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_SELL_CONFIRM")


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
        [10, 10.2, 10.4, 10.6, 11.2, 10.3],
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
        [10, 10.2, 10.4, 10.6, 10.8, 11.2, 10.7],
        [1000, 1000, 1000, 1000, 1000, 2200, 1000],
        momentum_window=5,
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
