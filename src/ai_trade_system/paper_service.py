from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ai_trade_system.market import Bar
from ai_trade_system.paper import PaperBroker, RiskLimits
from ai_trade_system.strategy import Strategy


class PaperTradingService:
    def __init__(
        self,
        strategy: Strategy,
        initial_cash: float,
        commission_rate: float = 0.0003,
        slippage: float = 0.01,
        max_order_cash: float = 50_000,
    ) -> None:
        self.strategy = strategy
        self.broker = PaperBroker(
            initial_cash=initial_cash,
            risk_limits=RiskLimits(max_order_cash=max_order_cash),
            commission_rate=commission_rate,
            slippage=slippage,
        )

    def run(self, bars: Iterable[Bar], log_path: str | Path | None = None) -> list[dict]:
        events: list[dict] = [{"event": "service_started"}]
        marks: dict[str, float] = {}

        self.strategy.on_init()
        self.strategy.on_start()
        try:
            for bar in bars:
                marks[bar.symbol] = bar.close_price
                for signal in self.strategy.on_bar(bar):
                    if signal.action == "buy":
                        result = self.broker.buy(signal.symbol, signal.price, signal.volume, trading_day=bar.trading_day)
                    else:
                        result = self.broker.sell(signal.symbol, signal.price, signal.volume, trading_day=bar.trading_day)

                    events.append(
                        {
                            "event": "order_accepted" if result.accepted else "order_rejected",
                            "side": result.side,
                            "symbol": result.symbol,
                            "price": result.price,
                            "volume": result.volume,
                            "reason": result.reason,
                            "trading_day": bar.trading_day.isoformat(),
                        }
                    )

                events.append(
                    {
                        "event": "equity",
                        "trading_day": bar.trading_day.isoformat(),
                        "equity": self.broker.equity(marks),
                        "cash": self.broker.cash,
                    }
                )
        finally:
            self.strategy.on_stop()
            events.append({"event": "service_stopped", "final_equity": self.broker.equity(marks)})

        if log_path:
            self._write_jsonl(events, log_path)
        return events

    @staticmethod
    def _write_jsonl(events: list[dict], log_path: str | Path) -> None:
        path = Path(log_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            for event in events:
                file.write(json.dumps(event, ensure_ascii=False) + "\n")
