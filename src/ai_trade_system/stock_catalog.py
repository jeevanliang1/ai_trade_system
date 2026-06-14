from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


DEFAULT_STOCK_CATALOG_PATH = Path("data/a_share_stocks.csv")


@dataclass(frozen=True)
class StockInfo:
    code: str
    name: str
    exchange: str


def load_stock_catalog(path: str | Path = DEFAULT_STOCK_CATALOG_PATH) -> list[StockInfo]:
    catalog_path = Path(path)
    if not catalog_path.exists():
        return []

    with catalog_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [
            _normalize_stock(row.get("code", ""), row.get("name", ""), row.get("exchange", ""))
            for row in reader
            if row.get("code") and row.get("name")
        ]


def search_stock_catalog(stocks: Iterable[StockInfo], query: str, limit: int = 20) -> list[StockInfo]:
    stock_list = list(stocks)
    normalized_query = _search_key(query)
    if not normalized_query:
        return stock_list[:limit]

    matches: list[StockInfo] = []
    for stock in stock_list:
        if stock.code.startswith(normalized_query):
            matches.append(stock)
        elif normalized_query in _search_key(stock.name):
            matches.append(stock)
        if len(matches) >= limit:
            break
    return matches


def refresh_stock_catalog(path: str | Path = DEFAULT_STOCK_CATALOG_PATH) -> list[StockInfo]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("Install optional dependency with `python -m pip install .[data]` to refresh stock catalog.") from exc

    frame = ak.stock_info_a_code_name()
    if not {"code", "name"}.issubset(frame.columns):
        raise ValueError("AKShare stock catalog must contain code and name columns")

    stocks = _stocks_from_frame(frame)
    write_stock_catalog(stocks, path)
    return stocks


def write_stock_catalog(stocks: Iterable[StockInfo], path: str | Path = DEFAULT_STOCK_CATALOG_PATH) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["code", "name", "exchange"])
        writer.writeheader()
        for stock in stocks:
            writer.writerow({"code": stock.code, "name": stock.name, "exchange": stock.exchange})


def infer_exchange(code: str) -> str:
    normalized = _normalize_code(code)
    if normalized.startswith("6"):
        return "SSE"
    if normalized.startswith(("0", "3")):
        return "SZSE"
    if normalized.startswith(("4", "8", "9")):
        return "BSE"
    return ""


def _stocks_from_frame(frame: pd.DataFrame) -> list[StockInfo]:
    stocks: list[StockInfo] = []
    seen_codes: set[str] = set()
    for row in frame.to_dict("records"):
        stock = _normalize_stock(row["code"], row["name"], "")
        if not stock.code or not stock.name or stock.code in seen_codes:
            continue
        stocks.append(stock)
        seen_codes.add(stock.code)
    return stocks


def _normalize_stock(code: object, name: object, exchange: object) -> StockInfo:
    normalized_code = _normalize_code(code)
    normalized_name = str(name).strip()
    normalized_exchange = str(exchange or "").strip().upper() or infer_exchange(normalized_code)
    return StockInfo(normalized_code, normalized_name, normalized_exchange)


def _normalize_code(code: object) -> str:
    return str(code).strip().zfill(6)


def _search_key(value: object) -> str:
    return re.sub(r"\s+", "", str(value).casefold())
