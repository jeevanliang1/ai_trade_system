from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from ai_trade_system.stock_catalog import StockInfo, infer_exchange


DEFAULT_WATCHLIST_PATH = Path("config/watchlist.json")


def load_watchlist(path: str | Path = DEFAULT_WATCHLIST_PATH) -> list[StockInfo]:
    watchlist_path = Path(path)
    if not watchlist_path.exists():
        return []
    payload = json.loads(watchlist_path.read_text(encoding="utf-8"))
    rows = payload.get("stocks", []) if isinstance(payload, dict) else []
    return normalize_watchlist(rows)


def save_watchlist(stocks: Iterable[object], path: str | Path = DEFAULT_WATCHLIST_PATH) -> list[StockInfo]:
    normalized = normalize_watchlist(stocks)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"stocks": [_stock_payload(stock) for stock in normalized]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return normalized


def normalize_watchlist(stocks: Iterable[object]) -> list[StockInfo]:
    normalized: list[StockInfo] = []
    seen: set[tuple[str, str]] = set()
    for item in stocks:
        stock = _normalize_stock(item)
        if not stock.code or not stock.name:
            continue
        key = (stock.exchange, stock.code)
        if key in seen:
            continue
        normalized.append(stock)
        seen.add(key)
    return normalized


def _normalize_stock(item: object) -> StockInfo:
    if isinstance(item, StockInfo):
        return StockInfo(code=item.code.zfill(6), name=item.name.strip(), exchange=(item.exchange or infer_exchange(item.code)).upper())
    if isinstance(item, dict):
        code = str(item.get("code", "")).strip().zfill(6)
        name = str(item.get("name", "")).strip()
        exchange = str(item.get("exchange", "") or infer_exchange(code)).strip().upper()
        return StockInfo(code=code, name=name, exchange=exchange)
    return StockInfo(code="", name="", exchange="")


def _stock_payload(stock: StockInfo) -> dict[str, str]:
    return {"code": stock.code, "name": stock.name, "exchange": stock.exchange}
