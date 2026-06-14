from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ai_trade_system.analytics import BacktestMetrics, DrawdownPoint
from ai_trade_system.backtest import EquityPoint
from ai_trade_system.indicators import IndicatorSnapshot
from ai_trade_system.llm import LLMInsight
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
METRIC_COLUMNS = ["metric", "value"]
DRAWDOWN_COLUMNS = ["trading_day", "equity", "drawdown_pct"]


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


def indicator_snapshot_to_frame(snapshot: IndicatorSnapshot) -> pd.DataFrame:
    rows = [
        {"metric": "股票代码", "value": str(snapshot.symbol)},
        {"metric": "交易日", "value": str(snapshot.trading_day)},
        {"metric": "收盘价", "value": _display_value(snapshot.close_price)},
        {"metric": "短均线", "value": _display_value(snapshot.short_ma)},
        {"metric": "长均线", "value": _display_value(snapshot.long_ma)},
        {"metric": "RSI", "value": _display_value(snapshot.rsi)},
        {"metric": "动量(%)", "value": _display_value(snapshot.momentum)},
        {"metric": "回撤(%)", "value": _display_value(snapshot.drawdown_pct)},
        {"metric": "趋势", "value": snapshot.trend},
    ]
    return pd.DataFrame(rows, columns=METRIC_COLUMNS)


def metrics_to_frame(metrics: BacktestMetrics) -> pd.DataFrame:
    rows = [
        {"metric": "最终权益", "value": metrics.final_equity},
        {"metric": "累计收益(%)", "value": metrics.total_return_pct},
        {"metric": "年化收益(%)", "value": metrics.annualized_return_pct},
        {"metric": "基准收益(%)", "value": metrics.benchmark_return_pct},
        {"metric": "超额收益(%)", "value": metrics.excess_return_pct},
        {"metric": "年化波动(%)", "value": metrics.annual_volatility_pct},
        {"metric": "夏普比率", "value": metrics.sharpe_ratio},
        {"metric": "最大回撤(%)", "value": metrics.max_drawdown_pct},
        {"metric": "交易次数", "value": metrics.trade_count},
        {"metric": "胜率(%)", "value": metrics.win_rate_pct},
        {"metric": "盈亏比", "value": metrics.profit_factor},
        {"metric": "平均持仓(%)", "value": metrics.exposure_pct},
    ]
    return pd.DataFrame(rows, columns=METRIC_COLUMNS)


def drawdowns_to_frame(points: Iterable[DrawdownPoint]) -> pd.DataFrame:
    rows = [
        {
            "trading_day": point.trading_day,
            "equity": point.equity,
            "drawdown_pct": point.drawdown_pct,
        }
        for point in points
    ]
    return _sorted_frame(rows, DRAWDOWN_COLUMNS)


def llm_insight_to_sections(insight: LLMInsight) -> dict[str, Any]:
    return {
        "summary": {
            "symbol": insight.symbol,
            "horizon": insight.horizon,
            "direction": insight.direction,
            "confidence": insight.confidence,
            "suggested_action": insight.suggested_action,
            "provider": insight.provider,
            "prompt_version": insight.prompt_version,
            "created_at": insight.created_at,
        },
        "technical_evidence": list(insight.technical_evidence),
        "information_evidence": list(insight.information_evidence),
        "risk_warnings": list(insight.risk_warnings),
    }


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


def _display_value(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)
