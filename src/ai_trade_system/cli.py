from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import fetch_akshare_daily_bars, read_bars_csv, write_bars_csv
from ai_trade_system.data_manager import update_watchlist_data
from ai_trade_system.paper_service import PaperTradingService
from ai_trade_system.stock_catalog import (
    DEFAULT_STOCK_CATALOG_PATH,
    load_stock_catalog,
    refresh_stock_catalog,
    search_stock_catalog,
)
from ai_trade_system.strategies.dual_moving_average import DualMovingAverageStrategy
from ai_trade_system.watchlist import load_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-trade", description="A-share self-hosted quant system tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download A-share daily bars through AKShare")
    download.add_argument("--symbol", required=True)
    download.add_argument("--exchange", default="SZSE")
    download.add_argument("--start", required=True, help="YYYYMMDD")
    download.add_argument("--end", required=True, help="YYYYMMDD")
    download.add_argument("--output", required=True)
    download.add_argument("--adjust", default="qfq")

    backtest = subparsers.add_parser("backtest", help="Run dual moving average backtest from CSV")
    backtest.add_argument("--data", required=True)
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--fast", type=int, default=5)
    backtest.add_argument("--slow", type=int, default=20)
    backtest.add_argument("--size", type=int, default=100)
    backtest.add_argument("--cash", type=float, default=100_000)

    paper = subparsers.add_parser("paper", help="Replay CSV bars through paper trading service")
    paper.add_argument("--data", required=True)
    paper.add_argument("--symbol", required=True)
    paper.add_argument("--fast", type=int, default=5)
    paper.add_argument("--slow", type=int, default=20)
    paper.add_argument("--size", type=int, default=100)
    paper.add_argument("--cash", type=float, default=100_000)
    paper.add_argument("--log", default="logs/paper_events.jsonl")

    stocks = subparsers.add_parser("stocks", help="Manage local A-share stock catalog")
    stock_subparsers = stocks.add_subparsers(dest="stocks_command", required=True)
    stocks_refresh = stock_subparsers.add_parser("refresh", help="Refresh A-share stock catalog through AKShare")
    stocks_refresh.add_argument("--output", default=str(DEFAULT_STOCK_CATALOG_PATH))
    stocks_search = stock_subparsers.add_parser("search", help="Search local A-share stock catalog by code or name")
    stocks_search.add_argument("keyword")
    stocks_search.add_argument("--catalog", default=str(DEFAULT_STOCK_CATALOG_PATH))
    stocks_search.add_argument("--limit", type=int, default=20)

    data = subparsers.add_parser("data", help="Manage local market data files")
    data_subparsers = data.add_subparsers(dest="data_command", required=True)
    data_update_watchlist = data_subparsers.add_parser("update-watchlist", help="Update managed daily CSV files for watchlist stocks")
    data_update_watchlist.add_argument("--start", default=None, help="YYYYMMDD; default is two years before --end")
    data_update_watchlist.add_argument("--end", default=None, help="YYYYMMDD; default is today")
    data_update_watchlist.add_argument("--adjust", default="qfq")
    data_update_watchlist.add_argument("--if-stale", action="store_true", help="Skip stocks already fresh through --end")

    args = parser.parse_args()
    if args.command == "download":
        bars = fetch_akshare_daily_bars(args.symbol, args.start, args.end, args.exchange, args.adjust)
        write_bars_csv(bars, Path(args.output))
        print(f"wrote {len(bars)} bars to {args.output}")
    elif args.command == "backtest":
        bars = read_bars_csv(args.data)
        strategy = DualMovingAverageStrategy(args.symbol, args.fast, args.slow, args.size)
        result = run_backtest(bars, strategy, BacktestConfig(initial_cash=args.cash))
        print(f"final_equity={result.final_equity:.2f}")
        print(f"trades={len(result.trades)}")
    elif args.command == "paper":
        bars = read_bars_csv(args.data)
        strategy = DualMovingAverageStrategy(args.symbol, args.fast, args.slow, args.size)
        service = PaperTradingService(strategy=strategy, initial_cash=args.cash)
        events = service.run(bars, log_path=args.log)
        print(f"events={len(events)}")
        print(f"log={args.log}")
    elif args.command == "stocks":
        if args.stocks_command == "refresh":
            catalog = refresh_stock_catalog(args.output)
            print(f"wrote {len(catalog)} stocks to {args.output}")
        elif args.stocks_command == "search":
            catalog = load_stock_catalog(args.catalog)
            results = search_stock_catalog(catalog, args.keyword, limit=args.limit)
            for stock in results:
                print(f"{stock.code}\t{stock.name}\t{stock.exchange}")
            if not results:
                print("no matching stocks")
    elif args.command == "data":
        if args.data_command == "update-watchlist":
            end_date = args.end or date.today().strftime("%Y%m%d")
            start_date = args.start or f"{int(end_date[:4]) - 2}{end_date[4:]}"
            result = update_watchlist_data(
                load_watchlist(),
                start_date=start_date,
                end_date=end_date,
                adjust=args.adjust,
                if_stale=args.if_stale,
            )
            print(f"updated={result['updated']} skipped={result['skipped']} failed={result['failed']}")
            for item in result["files"]:
                print(f"{item['code']}\t{item['exchange']}\t{item['status']}\t{item['latest_path']}")


if __name__ == "__main__":
    main()
