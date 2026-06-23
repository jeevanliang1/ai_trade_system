from __future__ import annotations

from datetime import date, timedelta

from ai_trade_system.automation import radar
from ai_trade_system.automation.models import AutomationConfig
from ai_trade_system.automation.radar import scan_star_radar_candidates
from ai_trade_system.data import write_bars_csv
from ai_trade_system.data_manager import data_file_for_stock
from ai_trade_system.market import Bar
from ai_trade_system.stock_catalog import StockInfo


def _bar(symbol: str, exchange: str, day: date, close: float, volume: float) -> Bar:
    return Bar(
        symbol=symbol,
        exchange=exchange,
        trading_day=day,
        open_price=close - 0.2,
        high_price=close + 0.4,
        low_price=close - 0.4,
        close_price=close,
        volume=volume,
        turnover=close * volume,
    )


def _write_stock(stock: StockInfo, closes: list[float], volumes: list[float]) -> None:
    start = date(2026, 1, 1)
    write_bars_csv(
        [_bar(stock.code, stock.exchange, start + timedelta(days=index), close, volumes[index]) for index, close in enumerate(closes)],
        data_file_for_stock(stock, adjust="qfq").latest_path,
    )


def test_scan_star_radar_candidates_ranks_by_chan_primary_volume_assist(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    strong = StockInfo("688001", "强结构", "SSE")
    weak = StockInfo("688002", "弱结构", "SSE")
    missing = StockInfo("688003", "缺数据", "SSE")
    closes = [10, 9, 10, 11, 12, 13, 14, 15, 14, 13, 12, 11, 10, 9, 10, 11, 12, 13, 14, 15] * 4
    _write_stock(strong, closes, [1000.0] * len(closes))
    _write_stock(weak, [10 + index * 0.05 for index in range(80)], [900.0] * 79 + [2500.0])

    result = scan_star_radar_candidates([weak, missing, strong], AutomationConfig(top_n=2, min_bars=60, lookback=120))

    assert result.total_candidates == 3
    assert result.scanned == 2
    assert result.missing == 1
    assert len(result.top) == 2
    assert result.top[0].rank == 1
    assert result.top[0].composite_score >= result.top[1].composite_score
    assert result.top[0].reason


def test_scan_star_radar_candidates_uses_chan_multilevel_daily_anchor_score(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    stock = StockInfo("688001", "华兴源创", "SSE")
    _write_stock(stock, [10 + index * 0.05 for index in range(80)], [1000.0] * 80)
    calls: list[tuple[int, int, int]] = []

    def fake_score(bars, min_bars, lookback):
        calls.append((len(bars), min_bars, lookback))
        score = {
            "total_score": 88.0,
            "direction": "bullish",
            "confidence": 0.92,
            "chan_score": 88.0,
            "rsi_score": 0,
            "summary": "多级别日线锚定买入",
        }
        latest_signal = {
            "title": "缠论多级别日线锚定买入",
            "kind": "CHAN_MULTILEVEL_DAILY_ANCHOR_BUY",
            "action": "buy",
            "trading_day": "2026-03-21",
            "price": 13.95,
            "reason": "chan_multilevel:DAILY_ANCHOR",
        }
        return score, latest_signal, [], {"strategy": {"entry_mode": "daily_anchor"}}

    monkeypatch.setattr(radar, "_chan_multilevel_daily_anchor_score", fake_score, raising=False)

    result = scan_star_radar_candidates([stock], AutomationConfig(top_n=1, min_bars=60, lookback=120))

    assert calls == [(80, 60, 120)]
    assert result.top[0].chan_signal_title == "缠论多级别日线锚定买入"
    assert result.top[0].chan_signal_action == "buy"
    assert result.top[0].composite_score == 88.0
