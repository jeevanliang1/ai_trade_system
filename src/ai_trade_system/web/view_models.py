from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ai_trade_system.backtest import EquityPoint
from ai_trade_system.market import Bar
from ai_trade_system.paper import Trade
from ai_trade_system.strategy import Strategy

BAR_COLUMNS = [
    "symbol",
    "exchange",
    "trading_day",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
    "turnover",
]
EQUITY_COLUMNS = ["trading_day", "equity", "cash", "close_price"]
TRADE_COLUMNS = ["trading_day", "side", "symbol", "price", "volume", "commission", "notional"]
ORDER_EVENT_COLUMNS = ["trading_day", "event", "side", "symbol", "price", "volume", "reason"]
PAPER_EQUITY_COLUMNS = ["trading_day", "equity", "cash"]
SIGNAL_COLUMNS = ["trading_day", "action", "symbol", "price", "volume", "reason"]


def bars_to_frame(bars: Iterable[Bar]) -> pd.DataFrame:
    rows = [
        {
            "symbol": bar.symbol,
            "exchange": bar.exchange,
            "trading_day": bar.trading_day,
            "open_price": bar.open_price,
            "high_price": bar.high_price,
            "low_price": bar.low_price,
            "close_price": bar.close_price,
            "volume": bar.volume,
            "turnover": bar.turnover,
        }
        for bar in bars
    ]
    return _sorted_frame(rows, BAR_COLUMNS)


def equity_curve_to_frame(points: Iterable[EquityPoint]) -> pd.DataFrame:
    rows = [
        {
            "trading_day": point.trading_day,
            "equity": point.equity,
            "cash": point.cash,
            "close_price": point.close_price,
        }
        for point in points
    ]
    return _sorted_frame(rows, EQUITY_COLUMNS)


def trades_to_frame(trades: Iterable[Trade]) -> pd.DataFrame:
    rows = [
        {
            "trading_day": trade.trading_day,
            "side": trade.side,
            "symbol": trade.symbol,
            "price": trade.price,
            "volume": trade.volume,
            "commission": trade.commission,
            "notional": trade.price * trade.volume,
        }
        for trade in trades
    ]
    return _sorted_frame(rows, TRADE_COLUMNS)


def strategy_signals_to_frame(bars: Iterable[Bar], strategy: Strategy) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    strategy.on_init()
    strategy.on_start()
    try:
        for bar in bars:
            for signal in strategy.on_bar(bar):
                rows.append(
                    {
                        "trading_day": bar.trading_day,
                        "action": signal.action,
                        "symbol": signal.symbol,
                        "price": signal.price,
                        "volume": signal.volume,
                        "reason": signal.reason,
                    }
                )
    finally:
        strategy.on_stop()
    return _sorted_frame(rows, SIGNAL_COLUMNS)


def load_paper_events(path: str | Path) -> list[dict[str, Any]]:
    event_path = Path(path)
    if not event_path.exists():
        return []
    with event_path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def paper_events_to_frames(events: Iterable[dict[str, Any]]) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    order_rows: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}

    for event in events:
        event_name = event.get("event", "")
        if event_name in {"order_accepted", "order_rejected"}:
            order_rows.append({column: event.get(column, "") for column in ORDER_EVENT_COLUMNS})
        elif event_name == "equity":
            equity_rows.append({column: event.get(column, "") for column in PAPER_EQUITY_COLUMNS})
        elif event_name == "service_stopped":
            summary = dict(event)

    return (
        _sorted_frame(order_rows, ORDER_EVENT_COLUMNS),
        _sorted_frame(equity_rows, PAPER_EQUITY_COLUMNS),
        summary,
    )


def _sorted_frame(rows: list[dict[str, Any]], columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=columns)
    if "trading_day" in frame.columns and not frame.empty:
        frame = frame.sort_values("trading_day").reset_index(drop=True)
    return frame
