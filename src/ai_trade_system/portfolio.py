from __future__ import annotations

from dataclasses import dataclass, field

from ai_trade_system.market import Bar, Signal
from ai_trade_system.strategy import Strategy


@dataclass
class StrategyAllocation:
    name: str
    strategy: Strategy
    weight: float
    enabled: bool = True


@dataclass(frozen=True)
class PortfolioSignalBreakdown:
    buy_score: float
    sell_score: float
    active_signals: int
    mode: str
    reasons: list[str] = field(default_factory=list)


class PortfolioStrategy(Strategy):
    def __init__(self, allocations: list[StrategyAllocation], mode: str = "weighted_vote") -> None:
        if mode not in {"weighted_vote", "equal_vote", "first_active"}:
            raise ValueError(f"unsupported portfolio mode: {mode}")
        self.allocations = allocations
        self.mode = mode
        self.last_breakdown = PortfolioSignalBreakdown(0, 0, 0, mode, [])

    def on_init(self) -> None:
        for allocation in self._enabled_allocations():
            allocation.strategy.on_init()

    def on_start(self) -> None:
        for allocation in self._enabled_allocations():
            allocation.strategy.on_start()

    def on_stop(self) -> None:
        for allocation in self._enabled_allocations():
            allocation.strategy.on_stop()

    def on_bar(self, bar: Bar) -> list[Signal]:
        signals = self._collect_signals(bar)
        if self.mode == "first_active":
            return self._first_active(signals)
        return self._vote(signals, bar)

    def _enabled_allocations(self) -> list[StrategyAllocation]:
        return [allocation for allocation in self.allocations if allocation.enabled and allocation.weight > 0]

    def _collect_signals(self, bar: Bar) -> list[tuple[StrategyAllocation, Signal]]:
        collected: list[tuple[StrategyAllocation, Signal]] = []
        for allocation in self._enabled_allocations():
            for signal in allocation.strategy.on_bar(bar):
                collected.append((allocation, signal))
        return collected

    def _first_active(self, signals: list[tuple[StrategyAllocation, Signal]]) -> list[Signal]:
        if not signals:
            self.last_breakdown = PortfolioSignalBreakdown(0, 0, 0, self.mode, [])
            return []
        allocation, signal = signals[0]
        self.last_breakdown = PortfolioSignalBreakdown(
            buy_score=1.0 if signal.action == "buy" else 0.0,
            sell_score=1.0 if signal.action == "sell" else 0.0,
            active_signals=1,
            mode=self.mode,
            reasons=[f"{allocation.name}:{signal.reason}"],
        )
        return [Signal(signal.action, signal.symbol, signal.price, signal.volume, f"portfolio_first_active:{allocation.name}")]

    def _vote(self, signals: list[tuple[StrategyAllocation, Signal]], bar: Bar) -> list[Signal]:
        buy_score = 0.0
        sell_score = 0.0
        buy_volume = 0.0
        sell_volume = 0.0
        reasons: list[str] = []
        for allocation, signal in signals:
            score = allocation.weight if self.mode == "weighted_vote" else 1.0
            reasons.append(f"{allocation.name}:{signal.reason}")
            if signal.action == "buy":
                buy_score += score
                buy_volume += signal.volume * score
            elif signal.action == "sell":
                sell_score += score
                sell_volume += signal.volume * score

        self.last_breakdown = PortfolioSignalBreakdown(
            buy_score=buy_score,
            sell_score=sell_score,
            active_signals=len(signals),
            mode=self.mode,
            reasons=reasons,
        )
        if buy_score == sell_score:
            return []
        if buy_score > sell_score:
            return [Signal("buy", bar.symbol, bar.close_price, max(1, round(buy_volume / buy_score)), f"portfolio_{self.mode}")]
        return [Signal("sell", bar.symbol, bar.close_price, max(1, round(sell_volume / sell_score)), f"portfolio_{self.mode}")]
