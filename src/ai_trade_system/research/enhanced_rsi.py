from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from ai_trade_system.research.models import EnhancedRsiResult, ResearchSignal


def relative_strength_index(values: Sequence[float], period: int = 14) -> list[float | None]:
    closes = [float(value) for value in values]
    if not closes:
        return []
    if period <= 0:
        raise ValueError("period must be positive")

    result: list[float | None] = [None] * len(closes)
    for index in range(period, len(closes)):
        gains = []
        losses = []
        for delta_index in range(index - period + 1, index + 1):
            delta = closes[delta_index] - closes[delta_index - 1]
            gains.append(max(delta, 0.0))
            losses.append(max(-delta, 0.0))
        average_gain = sum(gains) / period
        average_loss = sum(losses) / period
        if average_gain == 0 and average_loss == 0:
            result[index] = 50.0
        elif average_loss == 0:
            result[index] = 100.0
        elif average_gain == 0:
            result[index] = 0.0
        else:
            rs = average_gain / average_loss
            result[index] = round(100 - (100 / (1 + rs)), 2)
    return result


def scan_enhanced_rsi(frame: pd.DataFrame, *, period: int = 14, lookback: int = 120) -> EnhancedRsiResult:
    if frame.empty:
        return EnhancedRsiResult([], None, 0.0)

    working = frame.tail(lookback).reset_index(drop=True).copy()
    working["rsi"] = relative_strength_index(working["close"].tolist(), period)
    signals: list[ResearchSignal] = []
    symbol = str(working.iloc[-1]["symbol"])
    exchange = str(working.iloc[-1]["exchange"])

    signals.extend(_threshold_signals(working, symbol, exchange))
    signals.extend(_recovery_signals(working, symbol, exchange))
    signals.extend(_divergence_signals(working, symbol, exchange))

    latest_values = working["rsi"].dropna()
    latest_rsi = None if latest_values.empty else round(float(latest_values.iloc[-1]), 2)
    return EnhancedRsiResult(signals, latest_rsi, _score_from_signals(signals))


def _threshold_signals(frame: pd.DataFrame, symbol: str, exchange: str) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    previous_rsi: float | None = None
    for _, row in frame.iterrows():
        rsi = row["rsi"]
        if pd.isna(rsi):
            continue
        current_rsi = float(rsi)
        if current_rsi <= 30 and (previous_rsi is None or previous_rsi > 30):
            signals.append(_signal(row, symbol, exchange, "RSI_OVERSOLD", "buy", 0.35, 18.0, f"RSI {rsi:.2f} 进入超卖区", ("rsi", "oversold")))
        elif current_rsi >= 70 and (previous_rsi is None or previous_rsi < 70):
            signals.append(_signal(row, symbol, exchange, "RSI_OVERBOUGHT", "sell", 0.35, -18.0, f"RSI {rsi:.2f} 进入超买区", ("rsi", "overbought")))
        previous_rsi = current_rsi
    return signals


def _recovery_signals(frame: pd.DataFrame, symbol: str, exchange: str) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    previous_rsi: float | None = None
    saw_oversold = False
    for _, row in frame.iterrows():
        rsi = row["rsi"]
        if pd.isna(rsi):
            continue
        if rsi <= 30:
            saw_oversold = True
        if saw_oversold and previous_rsi is not None and previous_rsi < 35 <= rsi:
            signals.append(_signal(row, symbol, exchange, "RSI_BULLISH_RECOVERY", "buy", 0.55, 24.0, f"RSI 从弱势区修复至 {rsi:.2f}", ("rsi", "recovery")))
            saw_oversold = False
        previous_rsi = float(rsi)
    return signals


def _divergence_signals(frame: pd.DataFrame, symbol: str, exchange: str) -> list[ResearchSignal]:
    signals: list[ResearchSignal] = []
    highs = _local_points(frame, "high")
    lows = _local_points(frame, "low")
    if len(highs) >= 2:
        prior, latest = highs[-2], highs[-1]
        if latest["price"] > prior["price"] and latest["rsi"] < prior["rsi"] - 2:
            signals.append(
                _signal(
                    frame.iloc[int(latest["index"])],
                    symbol,
                    exchange,
                    "RSI_BEARISH_DIVERGENCE",
                    "sell",
                    0.62,
                    -28.0,
                    "价格创新高但 RSI 高点回落，出现顶背离观察信号",
                    ("rsi", "divergence"),
                )
            )
    if len(lows) >= 2:
        prior, latest = lows[-2], lows[-1]
        if latest["price"] < prior["price"] and latest["rsi"] > prior["rsi"] + 2:
            signals.append(
                _signal(
                    frame.iloc[int(latest["index"])],
                    symbol,
                    exchange,
                    "RSI_BULLISH_DIVERGENCE",
                    "buy",
                    0.62,
                    28.0,
                    "价格创新低但 RSI 低点抬高，出现底背离观察信号",
                    ("rsi", "divergence"),
                )
            )
    return signals


def _local_points(frame: pd.DataFrame, kind: str) -> list[dict[str, float]]:
    points: list[dict[str, float]] = []
    if len(frame) < 3:
        return points
    for index in range(1, len(frame) - 1):
        rsi = frame.iloc[index]["rsi"]
        if pd.isna(rsi):
            continue
        previous_close = float(frame.iloc[index - 1]["close"])
        close = float(frame.iloc[index]["close"])
        next_close = float(frame.iloc[index + 1]["close"])
        if kind == "high" and close >= previous_close and close >= next_close:
            points.append({"index": float(index), "price": close, "rsi": float(rsi)})
        if kind == "low" and close <= previous_close and close <= next_close:
            points.append({"index": float(index), "price": close, "rsi": float(rsi)})
    return points


def _signal(row: pd.Series, symbol: str, exchange: str, kind: str, action: str, strength: float, score: float, reason: str, tags: tuple[str, ...]) -> ResearchSignal:
    return ResearchSignal(
        trading_day=row["trading_day"],
        symbol=symbol,
        exchange=exchange,
        kind=kind,
        action=action,
        price=round(float(row["close"]), 3),
        strength=strength,
        score=score,
        title=kind.replace("_", " "),
        reason=reason,
        tags=tags,
    )


def _score_from_signals(signals: list[ResearchSignal]) -> float:
    if not signals:
        return 0.0
    recent = signals[-6:]
    return round(max(-50.0, min(50.0, sum(signal.score for signal in recent))), 2)
