from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Iterable

from ai_trade_system.api.service import _chan_multilevel_daily_anchor_score
from ai_trade_system.automation.models import AutomationConfig, RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.data import read_bars_csv
from ai_trade_system.data_manager import data_file_for_stock
from ai_trade_system.stock_catalog import StockInfo


def scan_star_radar_candidates(
    stocks: Iterable[StockInfo],
    config: AutomationConfig,
    generated_at: str | None = None,
) -> WeeklyRadarResult:
    return scan_weekly_radar_candidates({"star": stocks}, config, generated_at=generated_at)


def scan_weekly_radar_candidates(
    stocks_by_board: dict[str, Iterable[StockInfo]],
    config: AutomationConfig,
    generated_at: str | None = None,
) -> WeeklyRadarResult:
    generated = generated_at or datetime.now().replace(microsecond=0).isoformat()
    board_top: dict[str, list[RadarCandidateScore]] = {}
    all_rows: list[RadarCandidateScore] = []
    total_candidates = 0
    scanned = 0
    missing = 0
    for board, board_stocks in stocks_by_board.items():
        stock_list = list(board_stocks)
        total_candidates += len(stock_list)
        rows, board_missing = _scan_rows(stock_list, config, board)
        scanned += len(rows)
        missing += board_missing
        all_rows.extend(rows)
        board_top[board] = _rank_rows(rows, config.top_n)

    combined = _rank_rows([row for row in all_rows if "ST" not in row.name.upper()], config.top_n)
    if combined:
        board_top["combined_non_st"] = combined
    top = combined or _rank_rows(all_rows, config.top_n)
    return WeeklyRadarResult(
        run_id=f"weekly-{generated}",
        generated_at=generated,
        status="success" if top else "failed",
        total_candidates=total_candidates,
        scanned=scanned,
        missing=missing,
        top=top,
        board_top=board_top,
    )


def _scan_rows(stock_list: list[StockInfo], config: AutomationConfig, board: str) -> tuple[list[RadarCandidateScore], int]:
    rows: list[RadarCandidateScore] = []
    missing = 0
    for stock in stock_list:
        data_file = data_file_for_stock(stock, adjust=config.adjust)
        if not data_file.latest_path.exists():
            missing += 1
            continue
        bars = read_bars_csv(data_file.latest_path)
        strategy_score, strategy_latest, _strategy_blockers, _strategy_preview = _chan_multilevel_daily_anchor_score(
            bars,
            config.min_bars,
            config.lookback,
        )
        strategy_total = float(strategy_score.get("total_score", 0) or 0)
        composite = round(max(0.0, strategy_total), 4)
        latest = bars[-1] if bars else None
        rows.append(
            RadarCandidateScore(
                code=stock.code,
                name=stock.name,
                exchange=stock.exchange,
                rank=0,
                composite_score=composite,
                chan_score=strategy_total,
                volume_score=0.0,
                latest_day=latest.trading_day.isoformat() if latest else None,
                latest_close=latest.close_price if latest else None,
                chan_signal_title=_signal_value(strategy_latest, "title"),
                chan_signal_action=_signal_value(strategy_latest, "action"),
                volume_entry_ready=_signal_value(strategy_latest, "action") == "buy",
                reason=_radar_reason(strategy_score, strategy_latest),
                board=board,
            )
        )
    return rows, missing


def _rank_rows(rows: list[RadarCandidateScore], limit: int) -> list[RadarCandidateScore]:
    sorted_rows = sorted(rows, key=lambda row: (-row.composite_score, -max(0.0, row.chan_score), row.code))
    return [replace(row, rank=index) for index, row in enumerate(sorted_rows[:limit], start=1)]


def _signal_value(signal: dict | None, key: str) -> str | None:
    if not signal:
        return None
    value = signal.get(key)
    return str(value) if value is not None else None


def _radar_reason(strategy_score: dict, strategy_latest: dict | None) -> str:
    title = _signal_value(strategy_latest, "title") or "暂无缠论多级别触发"
    action = _signal_value(strategy_latest, "action") or "watch"
    strategy_text = strategy_score.get("summary") or "缠论多级别日线锚定暂无当前策略信号"
    if action == "buy":
        return f"{title}，{strategy_text}"
    if action == "sell":
        return f"{title}，策略偏风险，{strategy_text}"
    return strategy_text
