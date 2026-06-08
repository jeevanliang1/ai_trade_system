from __future__ import annotations

from abc import ABC, abstractmethod

from ai_trade_system.market import Bar, Signal


class Strategy(ABC):
    def on_init(self) -> None:
        pass

    def on_start(self) -> None:
        pass

    def on_stop(self) -> None:
        pass

    @abstractmethod
    def on_bar(self, bar: Bar) -> list[Signal]:
        raise NotImplementedError
