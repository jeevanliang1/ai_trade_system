from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import date, datetime
import threading
from typing import Iterable
from uuid import uuid4

from ai_trade_system.market import Bar
from ai_trade_system.realtime_sources import BarFetcher, MarketDataSource, default_realtime_market_data_sources
from ai_trade_system.stock_catalog import StockInfo
from ai_trade_system.strategy import Strategy


@dataclass(frozen=True)
class RealtimeMonitorConfig:
    strategy_id: str
    stocks: list[StockInfo]
    start_date: str
    adjust: str
    timeframe: str
    poll_interval_seconds: float
    stock_sources: dict[str, list[str]]
    source_counts: dict[str, int]
    stock_markets: dict[str, str]
    market_counts: dict[str, int]


class RealtimeMonitorService:
    def __init__(
        self,
        *,
        fetch_bars: BarFetcher | None = None,
        market_data_sources: dict[str, MarketDataSource] | None = None,
        max_events: int = 500,
    ) -> None:
        self.fetch_bars = fetch_bars
        if market_data_sources is not None:
            self._market_data_sources = market_data_sources
        elif fetch_bars is not None:
            self._market_data_sources = default_realtime_market_data_sources(fetch_bars)
        else:
            self._market_data_sources = default_realtime_market_data_sources()
        self._events: deque[dict] = deque(maxlen=max_events)
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._strategy: Strategy | None = None
        self._strategies: dict[str, Strategy] = {}
        self._config: RealtimeMonitorConfig | None = None
        self._started_at: str | None = None
        self._stopped_at: str | None = None
        self._last_error: str | None = None
        self._last_bar_time: str | None = None
        self._seen_bars: set[tuple[str, str, str, str]] = set()

    def start(
        self,
        *,
        strategy: Strategy,
        strategy_id: str,
        stocks: Iterable[StockInfo],
        start_date: str,
        adjust: str = "qfq",
        timeframe: str = "1m",
        poll_interval_seconds: float = 30.0,
        background: bool = True,
        strategies: dict[str, Strategy] | None = None,
        stock_sources: dict[str, list[str]] | None = None,
        source_counts: dict[str, int] | None = None,
        stock_markets: dict[str, str] | None = None,
        market_counts: dict[str, int] | None = None,
    ) -> dict:
        clean_stocks = list(stocks)
        if not clean_stocks:
            raise ValueError("realtime monitor requires at least one stock")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")

        with self._lock:
            if self.running:
                raise RuntimeError("realtime monitor is already running")
            self._events.clear()
            self._seen_bars.clear()
            self._stop_event.clear()
            self._strategy = strategy
            self._strategies = strategies or {_stock_key(stock): strategy for stock in clean_stocks}
            self._config = RealtimeMonitorConfig(
                strategy_id=strategy_id,
                stocks=clean_stocks,
                start_date=start_date,
                adjust=adjust,
                timeframe=timeframe,
                poll_interval_seconds=poll_interval_seconds,
                stock_sources=stock_sources or {_stock_key(stock): ["current"] for stock in clean_stocks},
                source_counts=source_counts or {"current": len(clean_stocks)},
                stock_markets=stock_markets or {_stock_key(stock): "a_share" for stock in clean_stocks},
                market_counts=market_counts or {"a_share": len(clean_stocks)},
            )
            self._started_at = _now_iso()
            self._stopped_at = None
            self._last_error = None
            self._last_bar_time = None
            for monitor_strategy in _unique_strategies(self._strategies.values()):
                monitor_strategy.on_init()
                monitor_strategy.on_start()
            self._append_event(
                {
                    "event": "monitor_started",
                    "strategy_id": strategy_id,
                    "symbols": [_stock_key(stock) for stock in clean_stocks],
                    "source_counts": self._config.source_counts,
                    "market_counts": self._config.market_counts,
                    "timeframe": timeframe,
                }
            )
            if background:
                self._thread = threading.Thread(target=self._run_loop, name="realtime-monitor", daemon=True)
                self._thread.start()
            else:
                self._thread = None
            return self.status()

    def stop(self) -> dict:
        strategy: Strategy | None
        with self._lock:
            strategy = self._strategy
            strategies = list(_unique_strategies(self._strategies.values()))
            if strategy is None and not self.running:
                return self.status()
            self._stop_event.set()
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=3)
        with self._lock:
            if strategy is not None:
                for monitor_strategy in strategies:
                    monitor_strategy.on_stop()
            if self._stopped_at is None:
                self._stopped_at = _now_iso()
                self._append_event({"event": "monitor_stopped"})
            self._strategy = None
            self._strategies = {}
            self._thread = None
            return self.status()

    def poll_once(self) -> dict:
        with self._lock:
            strategy = self._strategy
            config = self._config
        if strategy is None or config is None:
            raise RuntimeError("realtime monitor is not running")

        try:
            updated = 0
            signals = 0
            for stock in config.stocks:
                market = config.stock_markets.get(_stock_key(stock), "a_share")
                data_source = self._market_data_sources.get(market)
                if data_source is None:
                    raise ValueError(f"unsupported realtime market source: {market}")
                stock_strategy = self._strategies.get(_stock_key(stock), strategy)
                bars = sorted(
                    data_source.fetch_bars(
                        stock.code,
                        stock.exchange,
                        config.start_date,
                        _today_key(),
                        config.adjust,
                        config.timeframe,
                    ),
                    key=_bar_sort_key,
                )
                if not bars:
                    self._append_event(
                        {
                            "event": "data_empty",
                            "symbol": stock.code,
                            "exchange": stock.exchange,
                            "market": market,
                            "timeframe": config.timeframe,
                        }
                    )
                    continue
                stock_updates, stock_signals = self._consume_stock_bars(stock_strategy, stock, bars, config.timeframe, market)
                updated += stock_updates
                signals += stock_signals
            self._last_error = None
            self._append_event({"event": "monitor_heartbeat", "updated_bars": updated, "signals": signals})
        except Exception as exc:
            self._last_error = str(exc)
            self._append_event({"event": "monitor_error", "message": str(exc)})
        return self.status()

    def status(self) -> dict:
        with self._lock:
            config = self._config
            return {
                "running": self.running,
                "started_at": self._started_at,
                "stopped_at": self._stopped_at,
                "strategy_id": config.strategy_id if config else None,
                "symbols": [_stock_key(stock) for stock in config.stocks] if config else [],
                "stock_sources": config.stock_sources if config else {},
                "source_counts": config.source_counts if config else {},
                "stock_markets": config.stock_markets if config else {},
                "market_counts": config.market_counts if config else {},
                "timeframe": config.timeframe if config else None,
                "poll_interval_seconds": config.poll_interval_seconds if config else None,
                "event_count": len(self._events),
                "last_event_at": self._events[-1]["created_at"] if self._events else None,
                "last_bar_time": self._last_bar_time,
                "last_error": self._last_error,
            }

    def events(self, limit: int = 100) -> list[dict]:
        with self._lock:
            if limit <= 0:
                return []
            return list(self._events)[-limit:]

    @property
    def running(self) -> bool:
        return self._strategy is not None and not self._stop_event.is_set()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.poll_once()
            with self._lock:
                config = self._config
                interval = config.poll_interval_seconds if config else 30.0
            self._stop_event.wait(interval)

    def _consume_stock_bars(self, strategy: Strategy, stock: StockInfo, bars: list[Bar], timeframe: str, market: str) -> tuple[int, int]:
        existing_keys = [self._bar_key(bar) for bar in bars]
        first_poll = not any(key in self._seen_bars for key in existing_keys)
        new_bars = bars if first_poll else [bar for bar in bars if self._bar_key(bar) not in self._seen_bars]
        if not new_bars:
            return 0, 0

        signal_count = 0
        for index, bar in enumerate(new_bars):
            bar_key = self._bar_key(bar)
            self._seen_bars.add(bar_key)
            signals = strategy.on_bar(bar)
            bar_time = _bar_time(bar)
            self._last_bar_time = bar_time
            should_emit_bar = not first_poll or index == len(new_bars) - 1
            if should_emit_bar:
                self._append_event(
                    {
                        "event": "bar_updated",
                        "symbol": stock.code,
                        "name": stock.name,
                        "exchange": stock.exchange,
                        "market": market,
                        "timeframe": bar.timeframe or timeframe,
                        "bar_time": bar_time,
                        "close_price": bar.close_price,
                        "volume": bar.volume,
                        "warmup": first_poll,
                    }
                )
            if first_poll:
                continue
            for signal in signals:
                signal_count += 1
                self._append_event(
                    {
                        "event": "signal_triggered",
                        "symbol": signal.symbol,
                        "name": stock.name,
                        "exchange": stock.exchange,
                        "market": market,
                        "timeframe": bar.timeframe or timeframe,
                        "bar_time": bar_time,
                        "side": signal.action,
                        "price": signal.price,
                        "volume": signal.volume,
                        "reason": signal.reason,
                    }
                )
        return len(new_bars), signal_count

    def _bar_key(self, bar: Bar) -> tuple[str, str, str, str]:
        return (bar.symbol, bar.exchange, bar.timeframe, _bar_time(bar))

    def _append_event(self, event: dict) -> None:
        payload = {"id": uuid4().hex, "created_at": _now_iso(), **event}
        self._events.append(payload)


def _stock_key(stock: StockInfo) -> str:
    return f"{stock.code}.{stock.exchange}"


def _unique_strategies(strategies: Iterable[Strategy]) -> list[Strategy]:
    unique: list[Strategy] = []
    seen: set[int] = set()
    for strategy in strategies:
        identity = id(strategy)
        if identity in seen:
            continue
        unique.append(strategy)
        seen.add(identity)
    return unique


def _bar_time(bar: Bar) -> str:
    return (bar.timestamp or bar.trading_day).isoformat()


def _bar_sort_key(bar: Bar) -> date | datetime:
    return bar.timestamp or bar.trading_day


def _today_key() -> str:
    return datetime.now().strftime("%Y%m%d")


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()
