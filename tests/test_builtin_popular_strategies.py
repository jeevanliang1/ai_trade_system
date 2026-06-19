from datetime import date, timedelta
from types import SimpleNamespace

from ai_trade_system.market import Bar
from ai_trade_system.backtest import run_backtest
from ai_trade_system.research.models import ResearchSignal
from ai_trade_system.strategies import popular as popular_strategies
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


def make_low_confidence_t2_chan_bars() -> list[Bar]:
    return [
        make_chan_bar(0, 12.0, 12.4, 11.6),
        make_chan_bar(1, 11.4, 11.8, 11.0),
        make_chan_bar(2, 10.8, 11.2, 10.4),
        make_chan_bar(3, 10.1, 10.5, 9.7),
        make_chan_bar(4, 9.8, 10.2, 9.4),
        make_chan_bar(5, 10.4, 10.8, 10.0),
        make_chan_bar(6, 11.1, 11.5, 10.7),
        make_chan_bar(7, 11.6, 12.0, 11.2),
        make_chan_bar(8, 10.9, 11.3, 10.5),
        make_chan_bar(9, 10.4, 10.8, 10.0),
        make_chan_bar(10, 10.8, 11.2, 10.4),
        make_chan_bar(11, 11.5, 11.9, 11.1),
        make_chan_bar(12, 12.0, 12.4, 11.6),
        make_chan_bar(13, 12.4, 12.8, 12.0),
    ]


def make_research_signal(
    day: date,
    kind: str,
    action: str,
    score: float,
    price: float,
    tags: tuple[str, ...] = ("chan", "structure", "confirmation"),
    metadata: dict[str, object] | None = None,
) -> ResearchSignal:
    return ResearchSignal(
        trading_day=day,
        symbol="000001",
        exchange="SZSE",
        kind=kind,
        action=action,
        price=price,
        strength=min(0.95, abs(score) / 100),
        score=score,
        title=kind,
        reason=f"test {kind}",
        tags=tags,
        metadata=metadata or {},
    )


def patch_chan_structure_scan(monkeypatch, signals: list[ResearchSignal]) -> None:
    class FakeAnalyzer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def update_bar(self, bar):
            return SimpleNamespace(signals=signals)

    monkeypatch.setattr(popular_strategies, "ChanCoreV2Analyzer", FakeAnalyzer, raising=False)
    monkeypatch.setattr(
        popular_strategies,
        "scan_chan_structure",
        lambda *args, **kwargs: SimpleNamespace(signals=signals),
        raising=False,
    )


def patch_chan_structure_analyzer(
    monkeypatch, signals: list[ResearchSignal], trends: list[object] | None = None
) -> None:
    class FakeAnalyzer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def update_bar(self, bar):
            return SimpleNamespace(signals=signals, core_v2=SimpleNamespace(trends=trends or []))

    monkeypatch.setattr(popular_strategies, "ChanCoreV2Analyzer", FakeAnalyzer, raising=False)


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
        signal_mode="structure",
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
    assert signals[0].volume == 300
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T3")


def test_chan_structure_strategy_emits_sell_after_structural_sell_signal():
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=8,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=40,
        signal_mode="structure",
        trade_size=100,
    )
    strategy.position_units = strategy.high_confidence_units
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
        allowed_point_types="all",
        max_holding_bars=0,
        trade_size=100,
    )
    strategy.position_units = strategy.high_confidence_units

    signals = [signal for bar in make_deep_chan_bars() for signal in strategy.on_bar(bar)]

    assert signals[0].action == "sell"
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_SELL_CONFIRM")


def test_chan_structure_strategy_uses_incremental_chan_core_v2_analyzer(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    calls = []

    class FakeAnalyzer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def update_bar(self, bar):
            calls.append(bar.trading_day)
            return SimpleNamespace(
                signals=[
                    make_research_signal(
                        bars[2].trading_day,
                        "CHAN_STRUCT_BUY_T3",
                        "buy",
                        44.0,
                        bars[2].close_price,
                        tags=("chan", "structure", "third-buy"),
                        metadata={"point_type": "third-buy", "level": "stroke"},
                    )
                ]
            )

    monkeypatch.setattr(popular_strategies, "ChanCoreV2Analyzer", FakeAnalyzer)
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=30.0, allowed_point_types="all")

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert len(calls) == len(bars)
    assert [signal.action for signal in signals] == ["buy"]


def test_chan_structure_strategy_sizes_position_by_chan_certainty(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(8)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                30.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            ),
            make_research_signal(
                bars[3].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                44.0,
                bars[3].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_SELL_T2",
                "sell",
                -30.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-sell"),
                metadata={"point_type": "second-sell", "level": "fractal"},
            ),
            make_research_signal(
                bars[5].trading_day,
                "CHAN_STRUCT_SELL_CONFIRM",
                "sell",
                -60.0,
                bars[5].close_price,
                metadata={"point_type": "first-sell", "level": "segment"},
            ),
            make_research_signal(
                bars[6].trading_day,
                "CHAN_STRUCT_SELL_T3",
                "sell",
                -44.0,
                bars[6].close_price,
                tags=("chan", "structure", "third-sell"),
                metadata={"point_type": "third-sell", "level": "stroke"},
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=8,
        min_signal_score=20.0,
        allowed_point_types="all",
        max_holding_bars=0,
        trade_size=100,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [
        ("buy", 100),
        ("buy", 200),
        ("sell", 100),
        ("sell", 100),
        ("sell", 100),
    ]
    assert strategy.position_units == 0


def test_chan_structure_strategy_divergence_confirmation_targets_middle_units(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_CONFIRM",
                "buy",
                60.0,
                bars[2].close_price,
                metadata={"point_type": "first-buy", "level": "segment"},
            )
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=30.0,
        allowed_point_types="all",
        max_holding_bars=0,
        trade_size=100,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 200)]
    assert strategy.position_units == 2


def test_chan_structure_strategy_in_position_property_remains_compatible():
    strategy = ChanStructureStrategy("000001")

    strategy.in_position = True
    assert strategy.in_position is True
    assert strategy.position_units == 1

    strategy.in_position = False
    assert strategy.in_position is False
    assert strategy.position_units == 0


def test_chan_structure_strategy_rejects_invalid_unit_configuration():
    invalid_kwargs = [
        {"low_confidence_units": 0},
        {"low_confidence_units": 2, "divergence_confirm_units": 1},
        {"divergence_confirm_units": 3, "high_confidence_units": 2},
        {"high_confidence_units": 3, "sell_confirm_units": 3},
        {"sell_confirm_units": -1},
    ]

    for kwargs in invalid_kwargs:
        try:
            ChanStructureStrategy("000001", **kwargs)
        except ValueError as exc:
            assert "units" in str(exc)
        else:
            raise AssertionError(f"invalid units should raise ValueError: {kwargs}")


def test_chan_structure_strategy_default_gate_blocks_t2_buy_in_downtrend(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []
    assert strategy.position_units == 0


def test_chan_structure_strategy_t2_score_override_passes_low_confidence_gate(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                36.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 100)]


def test_chan_structure_strategy_gate_off_preserves_plain_t2_behavior(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=20.0,
        low_confidence_gate="off",
        max_holding_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 100)]


def test_chan_structure_strategy_armed_t1_confirmation_bypasses_low_confidence_gate(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T1_DIVERGENCE",
                "buy",
                62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
                metadata={"point_type": "first-buy", "level": "segment"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            ),
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=20.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        watch_confirm_bars=5,
        max_holding_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 200)]
    assert signals[0].reason.startswith("chan_structure:ARMED_CONFIRM")


def test_chan_structure_strategy_range_context_caps_low_confidence_adds(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="range")],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=20.0,
        max_holding_bars=0,
        range_max_units=1,
    )
    strategy.position_units = 1

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []
    assert strategy.position_units == 1


def test_chan_structure_strategy_t3_ignores_low_confidence_gate(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_analyzer(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                44.0,
                bars[2].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            )
        ],
        trends=[SimpleNamespace(level="stroke", trend_type="down")],
    )
    strategy = ChanStructureStrategy("000001", min_bars=3, lookback=5, min_signal_score=20.0, max_holding_bars=0)

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [(signal.action, signal.volume) for signal in signals] == [("buy", 300)]


def test_chan_structure_strategy_rejects_invalid_low_confidence_gate_configuration():
    invalid_kwargs = [
        {"low_confidence_gate": "bad"},
        {"low_confidence_min_score": -1.0},
        {"range_max_units": -1},
        {"range_max_units": 4, "high_confidence_units": 3},
    ]

    for kwargs in invalid_kwargs:
        try:
            ChanStructureStrategy("000001", **kwargs)
        except ValueError as exc:
            assert "low_confidence" in str(exc) or "range_max_units" in str(exc)
        else:
            raise AssertionError(f"invalid low-confidence gate config should raise: {kwargs}")


def test_chan_structure_strategy_default_filters_low_confidence_structure_signals():
    bars = make_low_confidence_t2_chan_bars()
    tuned_default = ChanStructureStrategy("000001", min_bars=12, lookback=40, min_stroke_bars=2, min_rebound_pct=0.03)
    relaxed_gate = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="structure",
        allowed_point_types="all",
        low_confidence_gate="off",
    )

    tuned_signals = [signal for bar in bars for signal in tuned_default.on_bar(bar)]
    relaxed_gate_signals = [signal for bar in bars for signal in relaxed_gate.on_bar(bar)]

    assert tuned_default.min_signal_score == 28.0
    assert tuned_default.signal_mode == "all"
    assert tuned_default.allowed_point_types == "all"
    assert tuned_default.max_holding_bars == 15
    assert tuned_default.low_confidence_gate == "divergence_or_trend"
    assert tuned_signals == []
    assert [signal.action for signal in relaxed_gate_signals] == ["buy"]
    assert relaxed_gate_signals[0].volume == 100
    assert relaxed_gate_signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T2")


def test_chan_structure_strategy_signal_mode_filters_structure_family():
    bars = make_low_confidence_t2_chan_bars()
    confirmation = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="confirmation",
        allowed_point_types="all",
    )
    structure = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="structure",
        allowed_point_types="all",
        low_confidence_gate="off",
    )
    exploratory = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=40,
        min_stroke_bars=2,
        min_rebound_pct=0.03,
        min_signal_score=24.0,
        signal_mode="all",
        allowed_point_types="all",
        low_confidence_gate="off",
    )

    confirmation_signals = [signal for bar in bars for signal in confirmation.on_bar(bar)]
    structure_signals = [signal for bar in bars for signal in structure.on_bar(bar)]
    all_signals = [signal for bar in bars for signal in exploratory.on_bar(bar)]

    assert confirmation_signals == []
    assert [signal.action for signal in structure_signals] == ["buy"]
    assert structure_signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T2")
    assert [signal.action for signal in all_signals] == ["buy"]
    assert all_signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T2")


def test_chan_structure_strategy_signal_mode_filters_confirmation_family():
    confirmation = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=240,
        min_stroke_bars=4,
        min_rebound_pct=0.02,
        min_signal_score=50,
        trade_size=100,
        signal_mode="confirmation",
        allowed_point_types="all",
        max_holding_bars=0,
    )
    structure = ChanStructureStrategy(
        "000001",
        min_bars=12,
        lookback=240,
        min_stroke_bars=4,
        min_rebound_pct=0.02,
        min_signal_score=50,
        trade_size=100,
        signal_mode="structure",
        allowed_point_types="all",
        max_holding_bars=0,
    )
    confirmation.position_units = confirmation.high_confidence_units
    structure.position_units = structure.high_confidence_units

    confirmation_signals = [signal for bar in make_deep_chan_bars() for signal in confirmation.on_bar(bar)]
    structure_signals = [signal for bar in make_deep_chan_bars() for signal in structure.on_bar(bar)]

    assert confirmation_signals[0].action == "sell"
    assert confirmation_signals[0].reason.startswith("chan_structure:CHAN_STRUCT_SELL_CONFIRM")
    assert structure_signals == []


def test_chan_structure_strategy_confirmation_mode_exits_on_opposite_signal(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(bars[2].trading_day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 70.0, bars[2].close_price),
            make_research_signal(bars[4].trading_day, "CHAN_STRUCT_SELL_CONFIRM", "sell", -65.0, bars[4].close_price),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=30.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        max_holding_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_CONFIRM")
    assert signals[1].reason.startswith("chan_structure:CHAN_STRUCT_SELL_CONFIRM")


def test_chan_structure_strategy_confirmation_mode_exits_after_max_holding_bars(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [make_research_signal(bars[2].trading_day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 70.0, bars[2].close_price)],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=30.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        max_holding_bars=2,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[1].price == bars[4].close_price
    assert signals[1].reason == "chan_structure:TIME_EXIT:max_holding_bars=2"


def test_chan_structure_strategy_confirmation_mode_trades_third_buy_and_sell(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(5)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(bars[2].trading_day, "CHAN_STRUCT_BUY_T3", "buy", 44.0, bars[2].close_price),
            make_research_signal(bars[4].trading_day, "CHAN_STRUCT_SELL_T3", "sell", -44.0, bars[4].close_price),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=5,
        min_signal_score=30.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        max_holding_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy", "sell"]
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T3")
    assert signals[1].reason.startswith("chan_structure:CHAN_STRUCT_SELL_T3")


def test_chan_structure_strategy_filters_allowed_point_types(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                40.0,
                bars[2].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                44.0,
                bars[4].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=30.0,
        signal_mode="all",
        allowed_point_types="third-buy",
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy"]
    assert signals[0].price == bars[4].close_price
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T3")


def test_chan_structure_strategy_filters_allowed_levels(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_CONFIRM",
                "buy",
                70.0,
                bars[2].close_price,
                metadata={"point_type": "first-buy", "level": "segment"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T3",
                "buy",
                44.0,
                bars[4].close_price,
                tags=("chan", "structure", "third-buy"),
                metadata={"point_type": "third-buy", "level": "stroke"},
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=30.0,
        signal_mode="confirmation",
        allowed_levels="stroke",
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy"]
    assert signals[0].price == bars[4].close_price
    assert signals[0].reason.startswith("chan_structure:CHAN_STRUCT_BUY_T3")


def test_chan_structure_strategy_arms_bottom_divergence_watch_and_confirms_with_t2(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T1_DIVERGENCE",
                "buy",
                62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-buy"),
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=30.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        watch_confirm_bars=5,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["buy"]
    assert signals[0].price == bars[4].close_price
    assert signals[0].reason.startswith(
        "chan_structure:ARMED_CONFIRM:CHAN_STRUCT_BUY_T1_DIVERGENCE->CHAN_STRUCT_BUY_T2"
    )


def test_chan_structure_strategy_armed_watch_respects_confirmation_filters(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T1_DIVERGENCE",
                "buy",
                62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
                metadata={"point_type": "first-buy", "level": "segment"},
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-buy"),
                metadata={"point_type": "second-buy", "level": "fractal"},
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=30.0,
        signal_mode="confirmation",
        watch_confirm_bars=5,
        allowed_point_types="third-buy",
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []


def test_chan_structure_strategy_arms_top_divergence_watch_and_confirms_with_t3(monkeypatch):
    bars = [make_chan_bar(index, 14 - index, 14.5 - index, 13.5 - index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_SELL_T1_DIVERGENCE",
                "sell",
                -62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_SELL_T3",
                "sell",
                -44.0,
                bars[4].close_price,
                tags=("chan", "structure", "third-sell"),
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=30.0,
        signal_mode="confirmation",
        allowed_point_types="all",
        watch_confirm_bars=5,
    )
    strategy.in_position = True

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert [signal.action for signal in signals] == ["sell"]
    assert signals[0].price == bars[4].close_price
    assert signals[0].reason.startswith(
        "chan_structure:ARMED_CONFIRM:CHAN_STRUCT_SELL_T1_DIVERGENCE->CHAN_STRUCT_SELL_T3"
    )


def test_chan_structure_strategy_expires_armed_divergence_watch(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(7)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T1_DIVERGENCE",
                "buy",
                62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
            ),
            make_research_signal(
                bars[5].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[5].close_price,
                tags=("chan", "structure", "second-buy"),
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=7,
        min_signal_score=30.0,
        signal_mode="confirmation",
        watch_confirm_bars=2,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []


def test_chan_structure_strategy_can_disable_divergence_watch_arming(monkeypatch):
    bars = [make_chan_bar(index, 10 + index, 10.5 + index, 9.5 + index) for index in range(6)]
    patch_chan_structure_scan(
        monkeypatch,
        [
            make_research_signal(
                bars[2].trading_day,
                "CHAN_STRUCT_BUY_T1_DIVERGENCE",
                "buy",
                62.0,
                bars[2].close_price,
                tags=("chan", "structure", "divergence", "watch"),
            ),
            make_research_signal(
                bars[4].trading_day,
                "CHAN_STRUCT_BUY_T2",
                "buy",
                28.0,
                bars[4].close_price,
                tags=("chan", "structure", "second-buy"),
            ),
        ],
    )
    strategy = ChanStructureStrategy(
        "000001",
        min_bars=3,
        lookback=6,
        min_signal_score=30.0,
        signal_mode="confirmation",
        watch_confirm_bars=0,
    )

    signals = [signal for bar in bars for signal in strategy.on_bar(bar)]

    assert signals == []


def test_chan_structure_strategy_rejects_unknown_signal_mode():
    try:
        ChanStructureStrategy("000001", signal_mode="unknown")
    except ValueError as exc:
        assert "signal_mode" in str(exc)
    else:
        raise AssertionError("unsupported signal_mode should raise ValueError")


def test_chan_structure_strategy_rejects_unknown_allowed_point_types():
    try:
        ChanStructureStrategy("000001", allowed_point_types="second-buy,bad-token")
    except ValueError as exc:
        assert "allowed_point_types" in str(exc)
    else:
        raise AssertionError("unsupported allowed_point_types should raise ValueError")


def test_chan_structure_strategy_rejects_unknown_allowed_levels():
    try:
        ChanStructureStrategy("000001", allowed_levels="segment,bad-level")
    except ValueError as exc:
        assert "allowed_levels" in str(exc)
    else:
        raise AssertionError("unsupported allowed_levels should raise ValueError")


def test_chan_structure_strategy_rejects_negative_max_holding_bars():
    try:
        ChanStructureStrategy("000001", max_holding_bars=-1)
    except ValueError as exc:
        assert "max_holding_bars" in str(exc)
    else:
        raise AssertionError("negative max_holding_bars should raise ValueError")


def test_chan_structure_strategy_rejects_negative_watch_confirm_bars():
    try:
        ChanStructureStrategy("000001", watch_confirm_bars=-1)
    except ValueError as exc:
        assert "watch_confirm_bars" in str(exc)
    else:
        raise AssertionError("negative watch_confirm_bars should raise ValueError")


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
