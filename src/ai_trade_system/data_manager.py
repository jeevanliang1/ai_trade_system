from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import inspect
from pathlib import Path
from typing import Callable, Iterable

from ai_trade_system.data import fetch_akshare_bars, fetch_akshare_daily_bars, fetch_public_market_bars, normalize_timeframe, read_bars_csv, write_bars_csv
from ai_trade_system.market import Bar
from ai_trade_system.stock_catalog import StockInfo
from ai_trade_system.watchlist import normalize_watchlist


DEFAULT_MARKET_DATA_ROOT = Path("data/market")
DEFAULT_ADJUST = "qfq"

BarFetcher = Callable[..., list[Bar]]


@dataclass(frozen=True)
class ManagedDataFile:
    code: str
    name: str
    exchange: str
    adjust: str
    timeframe: str
    directory: Path
    latest_path: Path
    increments_dir: Path
    manifest_path: Path

    def increment_path(self, run_date: str, start_date: str, end_date: str) -> Path:
        return self.increments_dir / f"{self.code}_{self.exchange}_{self.timeframe}_{self.adjust}_{run_date}_from_{start_date}_to_{end_date}.csv"

    def load_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, payload: dict) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def status(self, as_of: date | None = None) -> dict:
        manifest = self.load_manifest()
        exists = self.latest_path.exists()
        latest_end = manifest.get("latest_end")
        stale = True
        if latest_end and as_of is not None:
            stale = latest_end < as_of.isoformat()
        elif exists:
            stale = False
        return {
            "code": self.code,
            "name": self.name,
            "exchange": self.exchange,
            "adjust": self.adjust,
            "timeframe": self.timeframe,
            "latest_path": self.latest_path.as_posix(),
            "manifest_path": self.manifest_path.as_posix(),
            "exists": exists,
            "stale": stale,
            "latest_start": manifest.get("latest_start"),
            "latest_end": latest_end,
            "latest_rows": manifest.get("latest_rows", 0),
            "last_increment_path": manifest.get("last_increment_path"),
            "last_updated_at": manifest.get("last_updated_at"),
            "last_status": manifest.get("last_status"),
            "last_error": manifest.get("last_error"),
        }


@dataclass(frozen=True)
class DataUpdateResult:
    code: str
    name: str
    exchange: str
    adjust: str
    status: str
    requested_start: str
    requested_end: str
    fetched_start: str | None
    fetched_end: str | None
    fetched_rows: int
    latest_rows: int
    latest_start: str | None
    latest_end: str | None
    latest_path: str
    increment_path: str | None
    message: str
    timeframe: str = "daily"

    def as_dict(self) -> dict:
        return asdict(self)


def data_file_for_stock(
    stock: object,
    adjust: str = DEFAULT_ADJUST,
    root: str | Path = DEFAULT_MARKET_DATA_ROOT,
    timeframe: str = "daily",
) -> ManagedDataFile:
    normalized = normalize_watchlist([stock])
    if not normalized:
        raise ValueError("stock requires code, name, and exchange")
    item = normalized[0]
    clean_adjust = str(adjust or DEFAULT_ADJUST).strip().lower()
    clean_timeframe = normalize_timeframe(timeframe)
    directory = Path(root) / _market_group(item.exchange) / item.exchange / item.code
    latest_path = directory / f"{item.code}_{item.exchange}_{clean_timeframe}_{clean_adjust}_latest.csv"
    increments_dir = directory / "increments"
    manifest_name = "manifest.json" if clean_timeframe == "daily" and clean_adjust == DEFAULT_ADJUST else f"manifest_{clean_timeframe}_{clean_adjust}.json"
    return ManagedDataFile(
        code=item.code,
        name=item.name,
        exchange=item.exchange,
        adjust=clean_adjust,
        timeframe=clean_timeframe,
        directory=directory,
        latest_path=latest_path,
        increments_dir=increments_dir,
        manifest_path=directory / manifest_name,
    )


def list_watchlist_data_status(
    stocks: Iterable[object],
    *,
    adjust: str = DEFAULT_ADJUST,
    timeframe: str = "daily",
    as_of: date | None = None,
    root: str | Path = DEFAULT_MARKET_DATA_ROOT,
) -> list[dict]:
    return [
        data_file_for_stock(stock, adjust=adjust, timeframe=timeframe, root=root).status(as_of=as_of)
        for stock in normalize_watchlist(stocks)
    ]


def update_watchlist_data(
    stocks: Iterable[object],
    *,
    start_date: str,
    end_date: str,
    adjust: str = DEFAULT_ADJUST,
    timeframe: str = "daily",
    if_stale: bool = True,
    fetcher: BarFetcher | None = None,
    root: str | Path = DEFAULT_MARKET_DATA_ROOT,
) -> dict:
    files: list[dict] = []
    updated = skipped = failed = 0
    for stock in normalize_watchlist(stocks):
        try:
            result = update_stock_data(
                stock,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                timeframe=timeframe,
                if_stale=if_stale,
                fetcher=fetcher,
                root=root,
            )
            files.append(result.as_dict())
            if result.status == "updated":
                updated += 1
            elif result.status == "skipped":
                skipped += 1
            else:
                failed += 1
        except Exception as exc:
            data_file = data_file_for_stock(stock, adjust=adjust, timeframe=timeframe, root=root)
            files.append(
                DataUpdateResult(
                    code=data_file.code,
                    name=data_file.name,
                    exchange=data_file.exchange,
                    adjust=data_file.adjust,
                    timeframe=data_file.timeframe,
                    status="failed",
                    requested_start=start_date,
                    requested_end=end_date,
                    fetched_start=None,
                    fetched_end=None,
                    fetched_rows=0,
                    latest_rows=0,
                    latest_start=None,
                    latest_end=None,
                    latest_path=data_file.latest_path.as_posix(),
                    increment_path=None,
                    message=str(exc),
                ).as_dict()
            )
            failed += 1
    return {"updated": updated, "skipped": skipped, "failed": failed, "files": files}


def update_stock_data(
    stock: object,
    *,
    start_date: str,
    end_date: str,
    adjust: str = DEFAULT_ADJUST,
    timeframe: str = "daily",
    if_stale: bool = False,
    fetcher: BarFetcher | None = None,
    root: str | Path = DEFAULT_MARKET_DATA_ROOT,
) -> DataUpdateResult:
    clean_timeframe = normalize_timeframe(timeframe)
    data_file = data_file_for_stock(stock, adjust=adjust, timeframe=clean_timeframe, root=root)
    fetch = fetcher or _default_fetcher(data_file.exchange, clean_timeframe)
    requested_start = _date_key(start_date)
    requested_end = _date_key(end_date)
    manifest = data_file.load_manifest()
    existing_bars = _read_existing_bars(data_file.latest_path)
    latest_end = _latest_end(manifest, existing_bars)
    latest_start = _latest_start(manifest, existing_bars)

    if if_stale and latest_end and _iso_to_key(latest_end) >= requested_end:
        return DataUpdateResult(
            code=data_file.code,
            name=data_file.name,
            exchange=data_file.exchange,
            adjust=data_file.adjust,
            timeframe=data_file.timeframe,
            status="skipped",
            requested_start=requested_start,
            requested_end=requested_end,
            fetched_start=None,
            fetched_end=None,
            fetched_rows=0,
            latest_rows=len(existing_bars),
            latest_start=latest_start,
            latest_end=latest_end,
            latest_path=data_file.latest_path.as_posix(),
            increment_path=None,
            message="data is already fresh",
        )

    fetch_start = requested_start
    if latest_end:
        next_day = _parse_manifest_date(latest_end) + timedelta(days=1)
        fetch_start = max(requested_start, next_day.strftime("%Y%m%d"))

    if fetch_start > requested_end:
        return DataUpdateResult(
            code=data_file.code,
            name=data_file.name,
            exchange=data_file.exchange,
            adjust=data_file.adjust,
            timeframe=data_file.timeframe,
            status="skipped",
            requested_start=requested_start,
            requested_end=requested_end,
            fetched_start=None,
            fetched_end=None,
            fetched_rows=0,
            latest_rows=len(existing_bars),
            latest_start=latest_start,
            latest_end=latest_end,
            latest_path=data_file.latest_path.as_posix(),
            increment_path=None,
            message="no missing date range",
        )

    try:
        fetched_bars = _call_fetcher(fetch, data_file.code, fetch_start, requested_end, data_file.exchange, data_file.adjust, data_file.timeframe)
    except Exception as exc:
        if not existing_bars:
            raise
        return DataUpdateResult(
            code=data_file.code,
            name=data_file.name,
            exchange=data_file.exchange,
            adjust=data_file.adjust,
            timeframe=data_file.timeframe,
            status="skipped",
            requested_start=requested_start,
            requested_end=requested_end,
            fetched_start=fetch_start,
            fetched_end=requested_end,
            fetched_rows=0,
            latest_rows=len(existing_bars),
            latest_start=latest_start,
            latest_end=latest_end,
            latest_path=data_file.latest_path.as_posix(),
            increment_path=None,
            message=f"using existing local data; incremental fetch failed: {exc}",
        )
    if not fetched_bars:
        return DataUpdateResult(
            code=data_file.code,
            name=data_file.name,
            exchange=data_file.exchange,
            adjust=data_file.adjust,
            timeframe=data_file.timeframe,
            status="skipped",
            requested_start=requested_start,
            requested_end=requested_end,
            fetched_start=fetch_start,
            fetched_end=requested_end,
            fetched_rows=0,
            latest_rows=len(existing_bars),
            latest_start=latest_start,
            latest_end=latest_end,
            latest_path=data_file.latest_path.as_posix(),
            increment_path=None,
            message="fetch returned no bars",
        )

    merged_bars = _merge_bars(existing_bars, fetched_bars)
    increment_path = data_file.increment_path(requested_end, fetch_start, requested_end)
    write_bars_csv(fetched_bars, increment_path)
    write_bars_csv(merged_bars, data_file.latest_path)
    manifest_payload = _manifest_payload(data_file, merged_bars, increment_path, "updated", None)
    data_file.write_manifest(manifest_payload)
    return DataUpdateResult(
        code=data_file.code,
        name=data_file.name,
        exchange=data_file.exchange,
        adjust=data_file.adjust,
        timeframe=data_file.timeframe,
        status="updated",
        requested_start=requested_start,
        requested_end=requested_end,
        fetched_start=fetch_start,
        fetched_end=requested_end,
        fetched_rows=len(fetched_bars),
        latest_rows=len(merged_bars),
        latest_start=manifest_payload["latest_start"],
        latest_end=manifest_payload["latest_end"],
        latest_path=data_file.latest_path.as_posix(),
        increment_path=increment_path.as_posix(),
        message=f"updated {len(fetched_bars)} bars",
    )


def _market_group(exchange: str) -> str:
    clean_exchange = str(exchange or "").strip().upper()
    if clean_exchange == "CRYPTO":
        return "crypto"
    if clean_exchange in {"NASDAQ", "NYSE", "AMEX", "US"}:
        return "us_stock"
    return "a_share"


def _default_fetcher(exchange: str, timeframe: str) -> BarFetcher:
    clean_exchange = str(exchange or "").strip().upper()
    if clean_exchange == "CRYPTO" or clean_exchange in {"NASDAQ", "NYSE", "AMEX", "US"}:
        return fetch_public_market_bars
    return fetch_akshare_daily_bars if timeframe == "daily" else fetch_akshare_bars


def _read_existing_bars(path: Path) -> list[Bar]:
    if not path.exists():
        return []
    return read_bars_csv(path)


def _merge_bars(existing: Iterable[Bar], incoming: Iterable[Bar]) -> list[Bar]:
    by_day: dict[date | datetime, Bar] = {}
    for bar in existing:
        by_day[_bar_key(bar)] = bar
    for bar in incoming:
        by_day[_bar_key(bar)] = bar
    return [by_day[day] for day in sorted(by_day)]


def _manifest_payload(data_file: ManagedDataFile, bars: list[Bar], increment_path: Path | None, status: str, error: str | None) -> dict:
    return {
        "code": data_file.code,
        "name": data_file.name,
        "exchange": data_file.exchange,
        "adjust": data_file.adjust,
        "timeframe": data_file.timeframe,
        "latest_path": data_file.latest_path.as_posix(),
        "latest_start": _format_bar_key(bars[0]) if bars else None,
        "latest_end": _format_bar_key(bars[-1]) if bars else None,
        "latest_rows": len(bars),
        "last_increment_path": increment_path.as_posix() if increment_path else None,
        "last_updated_at": datetime.now().replace(microsecond=0).isoformat(),
        "last_status": status,
        "last_error": error,
    }


def _latest_start(manifest: dict, bars: list[Bar]) -> str | None:
    if manifest.get("latest_start"):
        return manifest["latest_start"]
    if bars:
        return _format_bar_key(bars[0])
    return None


def _latest_end(manifest: dict, bars: list[Bar]) -> str | None:
    if manifest.get("latest_end"):
        return manifest["latest_end"]
    if bars:
        return _format_bar_key(bars[-1])
    return None


def _bar_key(bar: Bar) -> date | datetime:
    return bar.timestamp or bar.trading_day


def _format_bar_key(bar: Bar) -> str:
    key = _bar_key(bar)
    if isinstance(key, datetime):
        return key.isoformat(sep=" ")
    return key.isoformat()


def _call_fetcher(
    fetch: BarFetcher,
    symbol: str,
    start_date: str,
    end_date: str,
    exchange: str,
    adjust: str,
    timeframe: str,
) -> list[Bar]:
    try:
        signature = inspect.signature(fetch)
    except (TypeError, ValueError):
        return fetch(symbol, start_date, end_date, exchange, adjust, timeframe)
    parameters = signature.parameters.values()
    accepts_varargs = any(parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in parameters)
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind in {inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD}
    ]
    if accepts_varargs or "timeframe" in signature.parameters or len(positional) >= 6:
        return fetch(symbol, start_date, end_date, exchange, adjust, timeframe)
    return fetch(symbol, start_date, end_date, exchange, adjust)


def _date_key(value: str) -> str:
    clean = str(value).strip().replace("-", "")
    if len(clean) != 8 or not clean.isdigit():
        raise ValueError(f"date must use YYYYMMDD or YYYY-MM-DD: {value}")
    return clean


def _iso_to_key(value: str) -> str:
    return _parse_manifest_date(value).strftime("%Y%m%d")


def _parse_manifest_date(value: str) -> date:
    text = str(value).strip().replace("T", " ")
    return datetime.strptime(text[:10], "%Y-%m-%d").date()
