from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from ai_trade_system.market import Bar

AKSHARE_COLUMNS = {
    "日期": "trading_day",
    "开盘": "open_price",
    "最高": "high_price",
    "最低": "low_price",
    "收盘": "close_price",
    "成交量": "volume",
    "成交额": "turnover",
}

MINUTE_COLUMNS = {
    "day": "timestamp",
    "open": "open_price",
    "high": "high_price",
    "low": "low_price",
    "close": "close_price",
    "volume": "volume",
}

SUPPORTED_TIMEFRAMES = {"daily", "1m", "5m", "15m", "30m", "60m"}


def normalize_akshare_bars(frame, symbol: str, exchange: str) -> list[Bar]:
    missing = [column for column in AKSHARE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    bars: list[Bar] = []
    normalized = frame.sort_values("日期")
    for row in normalized.to_dict("records"):
        bars.append(
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=_parse_date(row["日期"]),
                open_price=float(row["开盘"]),
                high_price=float(row["最高"]),
                low_price=float(row["最低"]),
                close_price=float(row["收盘"]),
                volume=float(row["成交量"]),
                turnover=float(row["成交额"]),
            )
        )
    return bars


def normalize_akshare_minute_bars(frame, symbol: str, exchange: str, timeframe: str) -> list[Bar]:
    clean_timeframe = normalize_timeframe(timeframe)
    if clean_timeframe == "daily":
        raise ValueError("minute bars require an intraday timeframe")
    missing = [column for column in MINUTE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    bars: list[Bar] = []
    normalized = frame.sort_values("day")
    for row in normalized.to_dict("records"):
        timestamp = _parse_datetime(row["day"])
        bars.append(
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=timestamp.date(),
                open_price=float(row["open"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                close_price=float(row["close"]),
                volume=float(row["volume"]),
                turnover=float(row.get("turnover") or row.get("amount") or 0),
                timestamp=timestamp,
                timeframe=clean_timeframe,
            )
        )
    return bars


def normalize_english_bars(frame, symbol: str, exchange: str) -> list[Bar]:
    column_map = {
        "date": "trading_day",
        "open": "open_price",
        "high": "high_price",
        "low": "low_price",
        "close": "close_price",
    }
    missing = [column for column in column_map if column not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {', '.join(missing)}")

    bars: list[Bar] = []
    normalized = frame.sort_values("date")
    for row in normalized.to_dict("records"):
        volume = row.get("volume", row.get("amount", 0))
        turnover = row.get("amount", 0) if "volume" in frame.columns else 0
        bars.append(
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=_parse_date(row["date"]),
                open_price=float(row["open"]),
                high_price=float(row["high"]),
                low_price=float(row["low"]),
                close_price=float(row["close"]),
                volume=float(volume),
                turnover=float(turnover),
            )
        )
    return bars


def fetch_akshare_daily_bars(
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str,
    adjust: str = "qfq",
) -> list[Bar]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("Install optional dependency with `python -m pip install .[data]` to use AKShare.") from exc

    errors: list[str] = []
    attempts = [
        (
            "eastmoney",
            lambda: normalize_akshare_bars(
                ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                ),
                symbol=symbol,
                exchange=exchange,
            ),
        ),
        (
            "tencent",
            lambda: normalize_english_bars(
                ak.stock_zh_a_hist_tx(
                    symbol=_market_symbol(symbol, exchange),
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    timeout=10,
                ),
                symbol=symbol,
                exchange=exchange,
            ),
        ),
        (
            "sina",
            lambda: normalize_english_bars(
                ak.stock_zh_a_daily(
                    symbol=_market_symbol(symbol, exchange),
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                ),
                symbol=symbol,
                exchange=exchange,
            ),
        ),
    ]

    for source, fetch in attempts:
        try:
            bars = fetch()
            if bars:
                return bars
            errors.append(f"{source}: returned empty data")
        except (AttributeError, requests.RequestException, ValueError, KeyError, pd.errors.EmptyDataError) as exc:
            errors.append(f"{source}: {exc}")

    raise RuntimeError(
        "AKShare request failed for Eastmoney, Tencent, and Sina. "
        "Check network/proxy access, or use an existing CSV file for backtesting. "
        f"Details: {'; '.join(errors)}"
    )


def fetch_akshare_bars(
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str,
    adjust: str = "qfq",
    timeframe: str = "daily",
) -> list[Bar]:
    clean_timeframe = normalize_timeframe(timeframe)
    if clean_timeframe == "daily":
        return fetch_akshare_daily_bars(symbol, start_date, end_date, exchange, adjust)
    return fetch_akshare_minute_bars(symbol, start_date, end_date, exchange, adjust, clean_timeframe)


def fetch_public_market_bars(
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str,
    adjust: str = "qfq",
    timeframe: str = "daily",
) -> list[Bar]:
    clean_timeframe = normalize_timeframe(timeframe)
    if clean_timeframe != "daily":
        raise ValueError("public US/crypto historical maintenance currently supports daily bars only")
    clean_exchange = str(exchange or "").strip().upper()
    if clean_exchange == "CRYPTO":
        return fetch_binance_daily_bars(symbol, start_date, end_date, clean_exchange)
    return fetch_yahoo_daily_bars(symbol, start_date, end_date, clean_exchange)


def fetch_yahoo_daily_bars(symbol: str, start_date: str, end_date: str, exchange: str) -> list[Bar]:
    start = _parse_date_key(start_date)
    end = _parse_date_key(end_date) + timedelta(days=1)
    params = {
        "period1": int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp()),
        "period2": int(datetime.combine(end, datetime.min.time(), tzinfo=timezone.utc).timestamp()),
        "interval": "1d",
        "events": "history",
    }
    response = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}", params=params, timeout=10)
    response.raise_for_status()
    result = response.json().get("chart", {}).get("result") or []
    if not result:
        return []
    payload = result[0]
    timestamps = payload.get("timestamp") or []
    quote = ((payload.get("indicators") or {}).get("quote") or [{}])[0]
    bars: list[Bar] = []
    for index, timestamp in enumerate(timestamps):
        open_price = _series_value(quote, "open", index)
        high_price = _series_value(quote, "high", index)
        low_price = _series_value(quote, "low", index)
        close_price = _series_value(quote, "close", index)
        if None in {open_price, high_price, low_price, close_price}:
            continue
        volume = _series_value(quote, "volume", index) or 0
        day = datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date()
        bars.append(
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=day,
                open_price=float(open_price),
                high_price=float(high_price),
                low_price=float(low_price),
                close_price=float(close_price),
                volume=float(volume),
                turnover=0,
            )
        )
    return bars


def fetch_binance_daily_bars(symbol: str, start_date: str, end_date: str, exchange: str = "CRYPTO") -> list[Bar]:
    start = _parse_date_key(start_date)
    end = _parse_date_key(end_date)
    start_ms = int(datetime.combine(start, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000) - 1
    rows: list[list] = []
    while start_ms <= end_ms:
        response = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol.upper(), "interval": "1d", "startTime": start_ms, "endTime": end_ms, "limit": 1000},
            timeout=10,
        )
        response.raise_for_status()
        chunk = response.json()
        if not chunk:
            break
        rows.extend(chunk)
        next_start = int(chunk[-1][0]) + 24 * 60 * 60 * 1000
        if next_start <= start_ms:
            break
        start_ms = next_start
    bars: list[Bar] = []
    for row in rows:
        day = datetime.fromtimestamp(int(row[0]) / 1000, tz=timezone.utc).date()
        bars.append(
            Bar(
                symbol=symbol.upper(),
                exchange=exchange,
                trading_day=day,
                open_price=float(row[1]),
                high_price=float(row[2]),
                low_price=float(row[3]),
                close_price=float(row[4]),
                volume=float(row[5]),
                turnover=float(row[7]) if len(row) > 7 else 0,
            )
        )
    return bars


def fetch_akshare_minute_bars(
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str,
    adjust: str = "qfq",
    timeframe: str = "5m",
) -> list[Bar]:
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("Install optional dependency with `python -m pip install .[data]` to use AKShare.") from exc

    clean_timeframe = normalize_timeframe(timeframe)
    if clean_timeframe == "daily":
        raise ValueError("minute fetch requires one of 1m/5m/15m/30m/60m")
    period = clean_timeframe.removesuffix("m")
    try:
        frame = ak.stock_zh_a_minute(
            symbol=_market_symbol(symbol, exchange),
            period=period,
            adjust=adjust or "",
        )
        bars = normalize_akshare_minute_bars(frame, symbol=symbol, exchange=exchange, timeframe=clean_timeframe)
        return _filter_bars_by_day(bars, start_date, end_date)
    except (AttributeError, requests.RequestException, ValueError, KeyError, pd.errors.EmptyDataError) as exc:
        raise RuntimeError(
            "AKShare minute request failed. Check network/proxy access, minute timeframe availability, "
            "or use an existing CSV file for backtesting. "
            f"Details: {exc}"
        ) from exc


def write_bars_csv(bars: Iterable[Bar], path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "symbol",
                "exchange",
                "trading_day",
                "timestamp",
                "timeframe",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
                "turnover",
            ],
        )
        writer.writeheader()
        for bar in bars:
            writer.writerow(
                {
                    "symbol": bar.symbol,
                    "exchange": bar.exchange,
                    "trading_day": bar.trading_day.isoformat(),
                    "timestamp": bar.timestamp.isoformat(sep=" ") if bar.timestamp else "",
                    "timeframe": bar.timeframe,
                    "open_price": bar.open_price,
                    "high_price": bar.high_price,
                    "low_price": bar.low_price,
                    "close_price": bar.close_price,
                    "volume": bar.volume,
                    "turnover": bar.turnover,
                }
            )


def read_bars_csv(path: str | Path) -> list[Bar]:
    with Path(path).open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return [
            Bar(
                symbol=row["symbol"],
                exchange=row["exchange"],
                trading_day=_parse_date(row["trading_day"]),
                timestamp=_parse_optional_datetime(row.get("timestamp")),
                timeframe=normalize_timeframe(row.get("timeframe") or "daily"),
                open_price=float(row["open_price"]),
                high_price=float(row["high_price"]),
                low_price=float(row["low_price"]),
                close_price=float(row["close_price"]),
                volume=float(row["volume"]),
                turnover=float(row.get("turnover") or 0),
            )
            for row in reader
        ]


def normalize_timeframe(value: str | None) -> str:
    raw = str(value or "daily").strip().lower()
    aliases = {
        "d": "daily",
        "day": "daily",
        "1": "1m",
        "5": "5m",
        "15": "15m",
        "30": "30m",
        "60": "60m",
        "1min": "1m",
        "5min": "5m",
        "15min": "15m",
        "30min": "30m",
        "60min": "60m",
    }
    normalized = aliases.get(raw, raw)
    if normalized not in SUPPORTED_TIMEFRAMES:
        raise ValueError(f"unsupported timeframe: {value}")
    return normalized


def _filter_bars_by_day(bars: Iterable[Bar], start_date: str, end_date: str) -> list[Bar]:
    start = _parse_date_key(start_date)
    end = _parse_date_key(end_date)
    return [bar for bar in bars if start <= bar.trading_day <= end]


def _series_value(quote: dict, key: str, index: int):
    values = quote.get(key) or []
    if index >= len(values):
        return None
    return values[index]


def _parse_date(value) -> date:
    if hasattr(value, "date"):
        return value.date()
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _parse_date_key(value: str) -> date:
    clean = str(value).strip().replace("-", "")
    return datetime.strptime(clean, "%Y%m%d").date()


def _parse_optional_datetime(value: str | None) -> datetime | None:
    if value is None or str(value).strip() == "":
        return None
    return _parse_datetime(value)


def _parse_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value.replace(second=0, microsecond=0)
    if hasattr(value, "to_pydatetime"):
        return value.to_pydatetime().replace(second=0, microsecond=0)
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y%m%d %H:%M:%S", "%Y%m%d %H:%M"):
        try:
            return datetime.strptime(text, fmt).replace(second=0, microsecond=0)
        except ValueError:
            continue
    parsed = pd.to_datetime(text)
    return parsed.to_pydatetime().replace(second=0, microsecond=0)


def _market_symbol(symbol: str, exchange: str) -> str:
    upper = exchange.upper()
    if upper in {"SSE", "SH", "SHSE"}:
        prefix = "sh"
    elif upper in {"BSE", "BJ", "BJSE"}:
        prefix = "bj"
    else:
        prefix = "sz"
    return f"{prefix}{symbol}"
