from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Bar:
    symbol: str
    exchange: str
    trading_day: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    turnover: float = 0.0
    timestamp: datetime | None = None
    timeframe: str = "daily"


@dataclass(frozen=True)
class Signal:
    action: str
    symbol: str
    price: float
    volume: int
    reason: str = ""

    def __post_init__(self) -> None:
        action = self.action.lower()
        if action not in {"buy", "sell"}:
            raise ValueError(f"unsupported signal action: {self.action}")
        object.__setattr__(self, "action", action)
