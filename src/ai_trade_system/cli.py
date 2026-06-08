from __future__ import annotations

import argparse
from pathlib import Path

from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import fetch_akshare_daily_bars, read_bars_csv, write_bars_csv
from ai_trade_system.paper_service import PaperTradingService
from ai_trade_system.strategies.dual_moving_average import DualMovingAverageStrategy


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


if __name__ == "__main__":
    main()
