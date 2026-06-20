from __future__ import annotations

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from ai_trade_system.data import write_bars_csv
from ai_trade_system.market import Bar
from ai_trade_system.research.models import ResearchSignal
from ai_trade_system.strategies import popular as popular_strategies
from ai_trade_system.strategies.popular import ChanMultiLevelReversalStrategy


def make_daily_bar(index: int, close: float = 10.0) -> Bar:
    day = date(2024, 1, 1) + timedelta(days=index)
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=day,
        open_price=close,
        high_price=close + 0.4,
        low_price=close - 0.4,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
        timeframe="daily",
    )


def make_minute_bar(index: int, timeframe: str, hour: int, minute: int, close: float = 10.0) -> Bar:
    day = date(2024, 1, 1) + timedelta(days=index)
    stamp = datetime(day.year, day.month, day.day, hour, minute)
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=day,
        timestamp=stamp,
        timeframe=timeframe,
        open_price=close,
        high_price=close + 0.2,
        low_price=close - 0.2,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def make_signal(day: date, kind: str, action: str, score: float, point_type: str, level: str = "segment") -> ResearchSignal:
    return ResearchSignal(
        trading_day=day,
        symbol="000001",
        exchange="SZSE",
        kind=kind,
        action=action,
        price=10.0,
        strength=min(0.95, abs(score) / 100),
        score=score,
        title=kind,
        reason=f"test {kind}",
        tags=("chan", "structure", point_type),
        metadata={"point_type": point_type, "level": level},
    )


def patch_multilevel_analyzers(monkeypatch, scripts: dict[str, list[ResearchSignal]], seen: list[tuple[str, object]]) -> None:
    class FakeAnalyzer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.latest_by_timeframe: dict[str, list[ResearchSignal]] = {}

        def update_bar(self, bar):
            timeframe = getattr(bar, "timeframe", "daily")
            seen.append((timeframe, bar.timestamp or bar.trading_day))
            signals = scripts.get(timeframe, [])
            trends = [SimpleNamespace(level="stroke", trend_type=scripts.get(f"{timeframe}:trend", ["transition"])[0])]
            return SimpleNamespace(signals=signals, core_v2=SimpleNamespace(trends=trends))

    monkeypatch.setattr(popular_strategies, "ChanCoreV2Analyzer", FakeAnalyzer, raising=False)


def test_chan_multilevel_strategy_rejects_invalid_configuration(tmp_path):
    with pytest.raises(ValueError, match="lower_level_policy"):
        ChanMultiLevelReversalStrategy("000001", lower_level_policy="bad")
    with pytest.raises(ValueError, match="minute_missing_policy"):
        ChanMultiLevelReversalStrategy("000001", minute_missing_policy="bad")
    with pytest.raises(ValueError, match="minute_sell_mode"):
        ChanMultiLevelReversalStrategy("000001", minute_sell_mode="bad")
    with pytest.raises(ValueError, match="min_confirm_score"):
        ChanMultiLevelReversalStrategy("000001", min_confirm_score=-1)
    with pytest.raises(ValueError, match="confirm_timeframe"):
        ChanMultiLevelReversalStrategy("000001", confirm_timeframe="5m")


def test_chan_multilevel_skip_entry_blocks_daily_buy_when_minute_data_missing(monkeypatch):
    day = date(2024, 1, 1)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {"daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")]},
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        confirm_csv_path="/tmp/missing-30m.csv",
        risk_csv_path="/tmp/missing-15m.csv",
        minute_missing_policy="skip_entry",
    )

    assert strategy.on_bar(make_daily_bar(0)) == []


def test_chan_multilevel_daily_only_fallback_preserves_daily_buy_when_configured(monkeypatch):
    day = date(2024, 1, 1)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {"daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")]},
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        confirm_csv_path="/tmp/missing-30m.csv",
        risk_csv_path="/tmp/missing-15m.csv",
        minute_missing_policy="daily_only",
    )

    signals = strategy.on_bar(make_daily_bar(0))

    assert [signal.action for signal in signals] == ["buy"]
    assert "DAILY_FALLBACK" in signals[0].reason


def test_chan_multilevel_daily_buy_requires_30m_confirmation(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        lower_level_policy="confirm_only",
    )

    signals = strategy.on_bar(make_daily_bar(0))

    assert [signal.action for signal in signals] == ["buy"]
    assert "CONFIRM_30M" in signals[0].reason


def test_chan_multilevel_bearish_15m_blocks_confirmed_buy(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [make_signal(day, "CHAN_STRUCT_SELL_T3", "sell", -35, "third-sell")],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        min_risk_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
    )

    assert strategy.on_bar(make_daily_bar(0)) == []


@pytest.mark.parametrize(
    ("minute_sell_mode", "expected_sell_volume", "expected_position_units"),
    [
        ("reduce", 1, 2),
        ("exit", 3, 0),
    ],
)
def test_chan_multilevel_15m_risk_signal_reduces_or_exits_existing_position(
    monkeypatch,
    tmp_path,
    minute_sell_mode,
    expected_sell_volume,
    expected_position_units,
):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0), make_minute_bar(1, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15), make_minute_bar(1, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [make_signal(day + timedelta(days=1), "CHAN_STRUCT_SELL_T3", "sell", -35, "third-sell")],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        min_risk_score=20,
        trade_size=1,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        minute_sell_mode=minute_sell_mode,
    )

    strategy.on_bar(make_daily_bar(0))
    strategy.position_units = 3
    signals = strategy.on_bar(make_daily_bar(1))

    assert [signal.action for signal in signals] == ["sell"]
    assert signals[0].volume == expected_sell_volume
    assert "RISK_15M" in signals[0].reason
    assert strategy.position_units == expected_position_units


def test_chan_multilevel_does_not_consume_future_minute_bars(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm.csv"
    risk_path = tmp_path / "risk.csv"
    write_bars_csv([make_minute_bar(0, "30m", 10, 0), make_minute_bar(1, "30m", 10, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "15m", 10, 15), make_minute_bar(1, "15m", 10, 15)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "30m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "15m": [],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        lower_level_policy="confirm_only",
    )

    strategy.on_bar(make_daily_bar(0))

    assert ("30m", datetime(2024, 1, 1, 10, 0)) in seen
    assert ("30m", datetime(2024, 1, 2, 10, 0)) not in seen
    assert ("15m", datetime(2024, 1, 1, 10, 15)) in seen
    assert ("15m", datetime(2024, 1, 2, 10, 15)) not in seen
