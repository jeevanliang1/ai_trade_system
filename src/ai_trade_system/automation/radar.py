from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Iterable

from ai_trade_system.api.service import _chan_structure_score, _volume_momentum_score
from ai_trade_system.automation.models import AutomationConfig, RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.data import read_bars_csv
from ai_trade_system.data_manager import data_file_for_stock
from ai_trade_system.stock_catalog import StockInfo


def scan_star_radar_candidates(
    stocks: Iterable[StockInfo],
    config: AutomationConfig,
    generated_at: str | None = None,
) -> WeeklyRadarResult:
    stock_list = list(stocks)
    generated = generated_at or datetime.now().replace(microsecond=0).isoformat()
    rows: list[RadarCandidateScore] = []
    missing = 0
    for stock in stock_list:
        data_file = data_file_for_stock(stock, adjust=config.adjust)
        if not data_file.latest_path.exists():
            missing += 1
            continue
        bars = read_bars_csv(data_file.latest_path)
        chan_score, chan_latest, _chan_blockers, _chan_preview = _chan_structure_score(bars, config.min_bars, config.lookback)
        volume_score, _volume_latest, _volume_blockers, momentum = _volume_momentum_score(bars, config.min_bars)
        chan_total = float(chan_score.get("total_score", 0) or 0)
        volume_total = float(volume_score.get("total_score", 0) or 0)
        composite = round(max(0.0, chan_total) * config.chan_weight + volume_total * config.volume_weight, 4)
        latest = bars[-1] if bars else None
        rows.append(
            RadarCandidateScore(
                code=stock.code,
                name=stock.name,
                exchange=stock.exchange,
                rank=0,
                composite_score=composite,
                chan_score=chan_total,
                volume_score=volume_total,
                latest_day=latest.trading_day.isoformat() if latest else None,
                latest_close=latest.close_price if latest else None,
                chan_signal_title=_signal_value(chan_latest, "title"),
                chan_signal_action=_signal_value(chan_latest, "action"),
                volume_entry_ready=bool(momentum.get("entry_ready")),
                reason=_radar_reason(chan_score, volume_score, chan_latest, momentum),
            )
        )
    rows.sort(key=lambda row: (-row.composite_score, -max(0.0, row.chan_score), -row.volume_score, row.code))
    top = [replace(row, rank=index) for index, row in enumerate(rows[: config.top_n], start=1)]
    return WeeklyRadarResult(
        run_id=f"weekly-{generated}",
        generated_at=generated,
        status="success" if top else "failed",
        total_candidates=len(stock_list),
        scanned=len(rows),
        missing=missing,
        top=top,
    )


def _signal_value(signal: dict | None, key: str) -> str | None:
    if not signal:
        return None
    value = signal.get(key)
    return str(value) if value is not None else None


def _radar_reason(chan_score: dict, volume_score: dict, chan_latest: dict | None, momentum: dict) -> str:
    title = _signal_value(chan_latest, "title") or "暂无缠论触发"
    action = _signal_value(chan_latest, "action") or "watch"
    volume_ready = bool(momentum.get("entry_ready"))
    momentum_pct = momentum.get("momentum_pct")
    volume_ratio = momentum.get("volume_ratio")
    if volume_ready:
        volume_text = f"量价确认，动量 {momentum_pct:.2f}%，放量 {volume_ratio:.2f}倍"
    else:
        volume_text = volume_score.get("summary") or "量价未确认"
    if action == "buy":
        return f"{title}，{volume_text}"
    if action == "sell":
        return f"{title}，结构偏风险，{volume_text}"
    return f"{chan_score.get('summary') or title}，{volume_text}"
