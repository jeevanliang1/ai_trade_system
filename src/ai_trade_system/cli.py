from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from ai_trade_system.agent import AgentOrchestrator
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import fetch_akshare_bars, read_bars_csv, write_bars_csv
from ai_trade_system.data_manager import update_watchlist_data
from ai_trade_system.paper_service import PaperTradingService
from ai_trade_system.stock_catalog import (
    DEFAULT_STOCK_CATALOG_PATH,
    load_stock_catalog,
    refresh_stock_catalog,
    search_stock_catalog,
)
from ai_trade_system.strategies.popular import ChanStructureStrategy
from ai_trade_system.watchlist import load_watchlist


def main() -> None:
    parser = argparse.ArgumentParser(prog="ai-trade", description="A-share self-hosted quant system tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download A-share bars through AKShare")
    download.add_argument("--symbol", required=True)
    download.add_argument("--exchange", default="SZSE")
    download.add_argument("--start", required=True, help="YYYYMMDD")
    download.add_argument("--end", required=True, help="YYYYMMDD")
    download.add_argument("--output", required=True)
    download.add_argument("--adjust", default="qfq")
    download.add_argument("--timeframe", default="daily", help="daily, 1m, 5m, 15m, 30m, or 60m")

    backtest = subparsers.add_parser("backtest", help="Run Chan structure backtest from CSV")
    backtest.add_argument("--data", required=True)
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--size", type=int, default=100)
    backtest.add_argument("--cash", type=float, default=100_000)

    paper = subparsers.add_parser("paper", help="Replay CSV bars through paper trading service")
    paper.add_argument("--data", required=True)
    paper.add_argument("--symbol", required=True)
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
    data_update_watchlist = data_subparsers.add_parser("update-watchlist", help="Update managed CSV files for watchlist stocks")
    data_update_watchlist.add_argument("--start", default=None, help="YYYYMMDD; default is two years before --end")
    data_update_watchlist.add_argument("--end", default=None, help="YYYYMMDD; default is today")
    data_update_watchlist.add_argument("--adjust", default="qfq")
    data_update_watchlist.add_argument("--timeframe", default="daily", help="daily, 1m, 5m, 15m, 30m, or 60m")
    data_update_watchlist.add_argument("--if-stale", action="store_true", help="Skip stocks already fresh through --end")

    agent = subparsers.add_parser("agent", help="Run and inspect audited AI Agent tasks")
    agent_subparsers = agent.add_subparsers(dest="agent_command", required=True)
    agent_tools = agent_subparsers.add_parser("tools", help="List Agent-callable system tools")
    agent_tools.add_argument("--json", action="store_true")
    agent_run = agent_subparsers.add_parser("run", help="Create and execute an Agent task")
    agent_run.add_argument("prompt")
    agent_run.add_argument("--source", default="cli")
    agent_run.add_argument("--symbol", default=None)
    agent_run.add_argument("--exchange", default=None)
    agent_run.add_argument("--json", action="store_true")
    agent_list = agent_subparsers.add_parser("list", help="List recent Agent tasks")
    agent_list.add_argument("--limit", type=int, default=50)
    agent_list.add_argument("--json", action="store_true")
    agent_show = agent_subparsers.add_parser("show", help="Show an Agent task")
    agent_show.add_argument("task_id")
    agent_show.add_argument("--json", action="store_true")
    agent_trace = agent_subparsers.add_parser("trace", help="Show append-only trace events for an Agent task")
    agent_trace.add_argument("task_id")
    agent_trace.add_argument("--json", action="store_true")
    agent_approve = agent_subparsers.add_parser("approve", help="Approve or reject a pending Agent action")
    agent_approve.add_argument("task_id")
    agent_approve.add_argument("--approval", default="approved")
    agent_approve.add_argument("--json", action="store_true")
    agent_subparsers.add_parser("mcp", help="Serve Agent tools over stdio MCP JSON-RPC")

    args = parser.parse_args()
    if args.command == "download":
        bars = fetch_akshare_bars(args.symbol, args.start, args.end, args.exchange, args.adjust, args.timeframe)
        write_bars_csv(bars, Path(args.output))
        print(f"wrote {len(bars)} bars to {args.output}")
    elif args.command == "backtest":
        bars = read_bars_csv(args.data)
        strategy = ChanStructureStrategy(args.symbol, trade_size=args.size)
        result = run_backtest(bars, strategy, BacktestConfig(initial_cash=args.cash))
        print(f"final_equity={result.final_equity:.2f}")
        print(f"trades={len(result.trades)}")
    elif args.command == "paper":
        bars = read_bars_csv(args.data)
        strategy = ChanStructureStrategy(args.symbol, trade_size=args.size)
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
                timeframe=args.timeframe,
                if_stale=args.if_stale,
            )
            print(f"updated={result['updated']} skipped={result['skipped']} failed={result['failed']}")
            for item in result["files"]:
                print(f"{item['code']}\t{item['exchange']}\t{item['status']}\t{item['latest_path']}")
    elif args.command == "agent":
        orchestrator = AgentOrchestrator()
        if args.agent_command == "tools":
            _print_payload({"tools": orchestrator.list_tools()}, args.json)
        elif args.agent_command == "run":
            context = {key: value for key, value in {"symbol": args.symbol, "exchange": args.exchange}.items() if value}
            task = orchestrator.create_task(args.prompt, source=args.source, context=context)
            _print_payload({"task": task.as_dict()}, args.json)
        elif args.agent_command == "list":
            _print_payload({"tasks": [task.as_dict() for task in orchestrator.list_tasks(args.limit)]}, args.json)
        elif args.agent_command == "show":
            _print_payload({"task": orchestrator.get_task(args.task_id).as_dict()}, args.json)
        elif args.agent_command == "trace":
            _print_payload({"task_id": args.task_id, "events": orchestrator.trace_task(args.task_id)}, args.json)
        elif args.agent_command == "approve":
            task = orchestrator.approve_task(args.task_id, args.approval)
            if task.status not in {"blocked", "completed", "failed", "waiting_confirmation"}:
                task = orchestrator.run_task(task.task_id)
            _print_payload({"task": task.as_dict()}, args.json)
        elif args.agent_command == "mcp":
            from ai_trade_system.agent.mcp_server import AgentMcpServer

            AgentMcpServer(orchestrator=orchestrator).serve_stdio()


def _print_payload(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False))
        return
    if "task" in payload:
        task = payload["task"]
        print(f"{task['task_id']}\t{task['status']}\t{task['source']}\t{task['result_summary']}")
        return
    if "tasks" in payload:
        for task in payload["tasks"]:
            print(f"{task['task_id']}\t{task['status']}\t{task['source']}\t{task['prompt']}")
        return
    if "tools" in payload:
        for tool in payload["tools"]:
            print(f"{tool['name']}\t{tool['permission']}\t{tool['description']}")
        return
    if "events" in payload:
        for event in payload["events"]:
            tool = event.get("tool_name") or "-"
            print(f"{event['event_id']}\t{event['type']}\t{tool}\t{event.get('status') or '-'}\t{event.get('summary') or ''}")


if __name__ == "__main__":
    main()
