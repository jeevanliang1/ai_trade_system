from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import pstdev

from ai_trade_system.market import Bar


@dataclass(frozen=True)
class IndicatorSnapshot:
    symbol: str
    trading_day: date
    close_price: float
    short_ma: float | None
    long_ma: float | None
    rsi: float | None
    momentum: float | None
    drawdown_pct: float
    trend: str


@dataclass(frozen=True)
class BollingerPoint:
    middle: float | None
    upper: float | None
    lower: float | None


def simple_moving_average(values: list[float], window: int) -> list[float | None]:
    _require_positive_window(window)
    averages: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < window:
            averages.append(None)
            continue
        sample = values[index + 1 - window : index + 1]
        averages.append(sum(sample) / window)
    return averages


def rate_of_change(values: list[float], window: int) -> list[float | None]:
    _require_positive_window(window)
    changes: list[float | None] = []
    for index, value in enumerate(values):
        if index < window:
            changes.append(None)
            continue
        previous = values[index - window]
        changes.append(None if previous == 0 else (value / previous - 1) * 100)
    return changes


def relative_strength_index(values: list[float], window: int = 14) -> list[float | None]:
    _require_positive_window(window)
    if not values:
        return []

    result: list[float | None] = [None]
    gains: list[float] = []
    losses: list[float] = []
    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gains.append(max(change, 0.0))
        losses.append(abs(min(change, 0.0)))
        if index < window:
            result.append(None)
            continue
        sample_gains = gains[index - window : index]
        sample_losses = losses[index - window : index]
        average_gain = sum(sample_gains) / window
        average_loss = sum(sample_losses) / window
        if average_loss == 0:
            result.append(100.0 if average_gain > 0 else 50.0)
        else:
            relative_strength = average_gain / average_loss
            result.append(100 - (100 / (1 + relative_strength)))
    return result


def bollinger_bands(values: list[float], window: int = 20, deviations: float = 2.0) -> list[BollingerPoint]:
    _require_positive_window(window)
    points: list[BollingerPoint] = []
    for index in range(len(values)):
        if index + 1 < window:
            points.append(BollingerPoint(None, None, None))
            continue
        sample = values[index + 1 - window : index + 1]
        middle = sum(sample) / window
        width = pstdev(sample) * deviations
        points.append(BollingerPoint(middle=middle, upper=middle + width, lower=middle - width))
    return points


def max_drawdown_from_closes(values: list[float]) -> float:
    peak: float | None = None
    max_drawdown = 0.0
    for value in values:
        peak = value if peak is None else max(peak, value)
        if peak:
            max_drawdown = min(max_drawdown, (value / peak - 1) * 100)
    return max_drawdown


def latest_indicator_snapshot(
    bars: list[Bar],
    short_window: int = 20,
    long_window: int = 60,
    rsi_window: int = 14,
    momentum_window: int = 5,
) -> IndicatorSnapshot:
    if not bars:
        raise ValueError("bars cannot be empty")

    closes = [bar.close_price for bar in bars]
    short_ma = simple_moving_average(closes, short_window)[-1]
    long_ma = simple_moving_average(closes, long_window)[-1]
    rsi = relative_strength_index(closes, rsi_window)[-1]
    momentum = rate_of_change(closes, min(momentum_window, max(1, len(closes) - 1)))[-1]
    latest = bars[-1]

    if short_ma is not None and long_ma is not None:
        if short_ma > long_ma:
            trend = "bullish"
        elif short_ma < long_ma:
            trend = "bearish"
        else:
            trend = "neutral"
    else:
        trend = "neutral"

    return IndicatorSnapshot(
        symbol=latest.symbol,
        trading_day=latest.trading_day,
        close_price=latest.close_price,
        short_ma=short_ma,
        long_ma=long_ma,
        rsi=rsi,
        momentum=momentum,
        drawdown_pct=max_drawdown_from_closes(closes),
        trend=trend,
    )


def _require_positive_window(window: int) -> None:
    if window <= 0:
        raise ValueError("window must be positive")
