from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class RiskLimits:
    max_order_cash: float = 50_000
    max_position_shares: int = 50_000
    min_cash_balance: float = 0


@dataclass(frozen=True)
class OrderResult:
    accepted: bool
    side: str
    symbol: str
    price: float
    volume: int
    reason: str = ""


@dataclass
class Trade:
    side: str
    symbol: str
    price: float
    volume: int
    commission: float
    trading_day: date | datetime | None = None


@dataclass
class PaperBroker:
    initial_cash: float
    risk_limits: RiskLimits = field(default_factory=RiskLimits)
    commission_rate: float = 0.0003
    slippage: float = 0.0
    cash: float = field(init=False)
    positions: dict[str, int] = field(default_factory=dict, init=False)
    trades: list[Trade] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self.cash = float(self.initial_cash)

    def buy(self, symbol: str, price: float, volume: int, trading_day: date | datetime | None = None) -> OrderResult:
        execution_price = price + self.slippage
        notional = execution_price * volume
        commission = notional * self.commission_rate
        if notional > self.risk_limits.max_order_cash:
            return OrderResult(False, "buy", symbol, execution_price, volume, "exceeds max_order_cash")
        if self.cash - notional - commission < self.risk_limits.min_cash_balance:
            return OrderResult(False, "buy", symbol, execution_price, volume, "insufficient cash")
        if self.position(symbol) + volume > self.risk_limits.max_position_shares:
            return OrderResult(False, "buy", symbol, execution_price, volume, "exceeds max_position_shares")

        self.cash -= notional + commission
        self.positions[symbol] = self.position(symbol) + volume
        self.trades.append(Trade("buy", symbol, execution_price, volume, commission, trading_day))
        return OrderResult(True, "buy", symbol, execution_price, volume)

    def sell(self, symbol: str, price: float, volume: int, trading_day: date | datetime | None = None) -> OrderResult:
        held = self.position(symbol)
        if held <= 0:
            return OrderResult(False, "sell", symbol, price, volume, "no position")
        sell_volume = min(volume, held)
        execution_price = max(0, price - self.slippage)
        notional = execution_price * sell_volume
        commission = notional * self.commission_rate
        self.cash += notional - commission
        self.positions[symbol] = held - sell_volume
        self.trades.append(Trade("sell", symbol, execution_price, sell_volume, commission, trading_day))
        return OrderResult(True, "sell", symbol, execution_price, sell_volume)

    def position(self, symbol: str) -> int:
        return self.positions.get(symbol, 0)

    def equity(self, marks: dict[str, float]) -> float:
        position_value = sum(volume * marks.get(symbol, 0.0) for symbol, volume in self.positions.items())
        return self.cash + position_value
