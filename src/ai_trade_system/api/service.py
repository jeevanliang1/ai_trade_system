from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, timedelta
import math
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

import pandas as pd

from ai_trade_system.analytics import calculate_backtest_metrics, calculate_signal_attribution, drawdown_series
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import fetch_akshare_daily_bars, read_bars_csv, write_bars_csv
from ai_trade_system.data_manager import (
    data_file_for_stock,
    list_watchlist_data_status,
    update_stock_data,
    update_watchlist_data as update_watchlist_data_files,
)
from ai_trade_system.indicators import latest_indicator_snapshot
from ai_trade_system.llm import LLMResearchRequest as CoreAIResearchRequest
from ai_trade_system.llm import MockLLMProvider, build_research_prompt
from ai_trade_system.market import Bar
from ai_trade_system.paper_service import PaperTradingService
from ai_trade_system.portfolio import PortfolioStrategy, StrategyAllocation
from ai_trade_system.portfolio_presets import portfolio_preset_views
from ai_trade_system.research import preview_research_signals as build_research_signal_preview
from ai_trade_system.research.chan_structure import scan_chan_structure
from ai_trade_system.research.dataframe import bars_to_frame
from ai_trade_system.risk import RiskGuardrailConfig, evaluate_risk_guardrails
from ai_trade_system.stock_catalog import StockInfo, load_stock_catalog, search_stock_catalog
from ai_trade_system.strategy import Strategy
from ai_trade_system.strategy_registry import (
    StrategySpec,
    create_strategy_template,
    discover_strategies,
    inspect_strategy_parameters,
    instantiate_strategy,
    read_strategy_source,
    save_strategy_source,
)
from ai_trade_system.watchlist import load_watchlist, save_watchlist
from ai_trade_system.web.view_models import (
    load_paper_events,
    paper_events_to_frames,
    strategy_signals_to_frame,
)

from .schemas import (
    BacktestRequest,
    DataRequest,
    DataUpdateWatchlistRequest,
    DemoDataRequest,
    PaperRunRequest,
    PlatformSettings,
    PortfolioRequest,
    ResearchSignalBatchRequest,
    ResearchSignalsRequest,
    RiskConfigView,
    StrategySelection,
)

if TYPE_CHECKING:
    from ai_trade_system.automation.scheduler import AutomationScheduler
    from ai_trade_system.automation.service import AutomationService


class ApiInputError(ValueError):
    """Raised for invalid API input that should be reported as HTTP 400."""


AI_WEIGHT_DELTA = 0.05
VOLUME_MOMENTUM_MOMENTUM_WINDOW = 20
VOLUME_MOMENTUM_MIN_MOMENTUM_PCT = 0.08
VOLUME_MOMENTUM_VOLUME_WINDOW = 20
VOLUME_MOMENTUM_VOLUME_MULTIPLIER = 1.5
VOLUME_MOMENTUM_TREND_WINDOW = 60


def default_settings(today: date | None = None) -> PlatformSettings:
    current = today or date.today()
    try:
        start = current.replace(year=current.year - 2)
    except ValueError:
        start = current.replace(year=current.year - 2, day=28)
    return PlatformSettings(start_date=start.strftime("%Y%m%d"), end_date=current.strftime("%Y%m%d"))


DEFAULT_SETTINGS = default_settings()
_AUTOMATION_SERVICE: "AutomationService | None" = None
_AUTOMATION_SCHEDULER: "AutomationScheduler | None" = None


def bootstrap() -> dict[str, Any]:
    catalog = load_stock_catalog()
    settings = default_settings()
    watchlist = list_watchlist()["stocks"]
    strategies = discover_strategies()
    return {
        "settings": settings.model_dump(),
        "catalog_available": bool(catalog),
        "catalog_size": len(catalog),
        "stocks": [_stock_view(stock) for stock in catalog[:20]],
        "strategies": [_strategy_view(strategy) for strategy in strategies],
        "portfolio_presets": portfolio_preset_views(strategies, settings.symbol),
        "watchlist": watchlist,
        "managed_data": list_managed_data()["files"],
        "limits": {
            "live_trading": False,
            "broker_gateway": "not_configured",
            "provider": "MockLLMProvider",
        },
    }


def list_stocks(query: str = "", limit: int = 20) -> list[dict[str, Any]]:
    return [_stock_view(stock) for stock in search_stock_catalog(load_stock_catalog(), query, limit)]


def list_watchlist() -> dict[str, Any]:
    return {"stocks": [_stock_view(stock) for stock in load_watchlist()]}


def put_watchlist(stocks: Iterable[Any]) -> dict[str, Any]:
    return {"stocks": [_stock_view(stock) for stock in save_watchlist(stocks)]}


def list_managed_data(adjust: str = "qfq") -> dict[str, Any]:
    return {"files": list_watchlist_data_status(load_watchlist(), adjust=adjust, as_of=date.today())}


def update_watchlist_data(request: DataUpdateWatchlistRequest) -> dict[str, Any]:
    settings = default_settings()
    start_date = request.start_date or settings.start_date
    end_date = request.end_date or settings.end_date
    return update_watchlist_data_files(
        load_watchlist(),
        start_date=start_date,
        end_date=end_date,
        adjust=request.adjust or settings.adjust,
        if_stale=request.if_stale,
    )


def get_automation_service() -> AutomationService:
    from ai_trade_system.automation.service import AutomationService

    global _AUTOMATION_SERVICE
    if _AUTOMATION_SERVICE is None:
        _AUTOMATION_SERVICE = AutomationService()
    return _AUTOMATION_SERVICE


def get_automation_scheduler(automation_service: AutomationService | None = None) -> AutomationScheduler:
    from ai_trade_system.automation.scheduler import AutomationScheduler

    global _AUTOMATION_SCHEDULER
    if _AUTOMATION_SCHEDULER is None:
        service_instance = automation_service or get_automation_service()
        _AUTOMATION_SCHEDULER = AutomationScheduler(service=service_instance)
    return _AUTOMATION_SCHEDULER


def automation_status() -> dict[str, Any]:
    return get_automation_service().status().as_dict()


def automation_top10() -> dict[str, Any]:
    weekly = get_automation_service().store.load_weekly_result()
    if weekly is None:
        return {"status": "missing", "generated_at": None, "top": []}
    return weekly.as_dict()


def automation_judgments(day: str | None = None) -> dict[str, Any]:
    service_instance = get_automation_service()
    target_day = day or date.today().isoformat()
    judgments = service_instance.store.load_daily_judgments(target_day)
    return {"date": target_day, "judgments": [judgment.as_dict() for judgment in judgments]}


def run_automation_weekly() -> dict[str, Any]:
    return get_automation_service().run_weekly_full_maintenance().as_dict()


def run_automation_daily() -> dict[str, Any]:
    judgments = get_automation_service().run_daily_top10_judgment()
    return {"date": date.today().isoformat(), "judgments": [judgment.as_dict() for judgment in judgments]}


def update_automation_config(payload: dict[str, Any]) -> dict[str, Any]:
    return get_automation_service().update_config(payload).as_dict()


def list_strategies() -> list[dict[str, Any]]:
    return [_strategy_view(spec) for spec in discover_strategies()]


def get_strategy_source(path: str) -> dict[str, str]:
    source_path = _safe_strategy_path(path)
    return {"path": str(source_path), "source": read_strategy_source(source_path)}


def put_strategy_source(filename: str, source: str) -> dict[str, Any]:
    path = save_strategy_source("strategies", filename, source)
    return {"path": str(path), "strategies": list_strategies()}


def create_strategy_file(filename: str, class_name: str) -> dict[str, Any]:
    path = save_strategy_source("strategies", filename, create_strategy_template(class_name))
    return {"path": str(path), "strategies": list_strategies()}


def load_data(request: DataRequest) -> dict[str, Any]:
    bars = _load_bars(request.settings)
    return _data_payload(bars, request.settings)


def download_data(request: DataRequest) -> dict[str, Any]:
    settings = request.settings
    bars = fetch_akshare_daily_bars(
        symbol=settings.symbol,
        start_date=settings.start_date,
        end_date=settings.end_date,
        exchange=settings.exchange,
        adjust=settings.adjust,
    )
    write_bars_csv(bars, _safe_data_path(settings.csv_path))
    payload = _data_payload(bars, settings)
    payload["managed_file"] = _managed_file_for_settings(settings)
    return payload


def demo_data(request: DemoDataRequest) -> dict[str, Any]:
    bars = _demo_bars(request.settings.symbol, request.settings.exchange, request.count)
    write_bars_csv(bars, _safe_data_path(request.settings.csv_path))
    return _data_payload(bars, request.settings)


def preview_signals(request) -> dict[str, Any]:
    bars = _load_bars(request.settings)
    strategy = _build_strategy(request.strategy)
    frame = strategy_signals_to_frame(bars, strategy)
    return {"bars": _serialize_many(bars), "signals": _frame_records(frame), "summary": _signal_summary(frame)}


def preview_portfolio(request) -> dict[str, Any]:
    bars = _load_bars(request.settings)
    allocations, allocation_views = _portfolio_allocations(request.portfolio)
    portfolio = PortfolioStrategy(allocations, mode=request.portfolio.mode)
    frame = strategy_signals_to_frame(bars, portfolio)
    return {
        "bars": _serialize_many(bars),
        "signals": _frame_records(frame),
        "summary": _signal_summary(frame),
        "breakdown": _serialize(portfolio.last_breakdown),
        "allocations": allocation_views,
        "ai_adjustment": _ai_adjustment_summary(request.portfolio),
    }


def run_backtest_request(request: BacktestRequest) -> dict[str, Any]:
    settings = request.settings
    bars = _load_bars(settings)
    strategy = _strategy_for_mode(request.mode, request.strategy, request.portfolio)
    result = run_backtest(
        bars,
        strategy,
        BacktestConfig(
            initial_cash=settings.initial_cash,
            commission_rate=settings.commission_rate,
            slippage=settings.slippage,
            max_order_cash=settings.max_order_cash,
        ),
    )
    metrics = calculate_backtest_metrics(result.equity_curve, result.trades, settings.initial_cash)
    drawdowns = drawdown_series(result.equity_curve)
    risk_status = evaluate_risk_guardrails(
        {"max_drawdown_pct": metrics.max_drawdown_pct},
        _risk_config(settings),
        enabled=settings.risk_enabled,
    )
    return {
        "bars": _serialize_many(bars),
        "metrics": _serialize(metrics),
        "equity_curve": _serialize_many(result.equity_curve),
        "drawdowns": _serialize_many(drawdowns),
        "trades": _serialize_many(result.trades),
        "trade_attributions": _serialize_many(result.trade_attributions),
        "signal_attribution": _serialize_many(calculate_signal_attribution(result.trade_attributions, settings.initial_cash)),
        "risk_status": _serialize(risk_status),
    }


def research_ai(request) -> dict[str, Any]:
    bars = _load_bars(request.settings)
    snapshot = latest_indicator_snapshot(bars)
    core_request = CoreAIResearchRequest(
        symbol=request.settings.symbol,
        horizon=request.horizon,
        indicator_snapshot=snapshot,
        information_notes=request.information_notes,
        risk_context={
            "max_drawdown_pct": request.settings.max_drawdown_pct,
            "max_order_cash": request.settings.max_order_cash,
            "stop_loss_mode": request.settings.stop_loss_mode,
        },
        prompt_mode=request.prompt_mode,
    )
    insight = MockLLMProvider().generate_insight(core_request)
    return {
        "snapshot": _serialize(snapshot),
        "prompt": build_research_prompt(core_request),
        "insight": _serialize(insight),
    }


def preview_research_signals(request: ResearchSignalsRequest) -> dict[str, Any]:
    bars = _load_bars(request.settings)
    preview = build_research_signal_preview(bars, min_bars=request.min_bars, lookback=request.lookback)
    return _serialize(preview)


def batch_research_signals(request: ResearchSignalBatchRequest) -> dict[str, Any]:
    candidates = _research_batch_candidates(request)
    batch_adjust = _batch_adjust(request)
    update_payload = _update_batch_candidate_data(request, candidates, batch_adjust) if request.auto_update_data else None
    data_statuses = update_payload["statuses"] if update_payload else {}

    rows: list[dict[str, Any]] = []
    for index, stock in enumerate(candidates):
        csv_path = _batch_stock_csv_path(stock, request.settings, batch_adjust)
        safe_csv_path = _safe_data_path(csv_path)
        data_status = data_statuses.get(stock.code)
        base_row = {
            "code": stock.code,
            "name": stock.name,
            "exchange": stock.exchange,
            "csv_path": csv_path.as_posix(),
            "rank": None,
            "data_status": data_status,
        }
        if not safe_csv_path.exists():
            blockers = [{"code": "MISSING_CSV", "message": f"未找到本地行情 CSV：{csv_path.as_posix()}"}]
            if data_status and data_status["status"] == "failed":
                blockers.insert(0, {"code": "DATA_UPDATE_FAILED", "message": data_status["message"]})
            rows.append(
                {
                    **base_row,
                    "status": "missing_data",
                    "score": None,
                    "latest_signal": None,
                    "preview": None,
                    "momentum": None,
                    "blockers": blockers,
                    "_order": index,
                }
            )
            continue

        settings = request.settings.model_copy(
            update={"symbol": stock.code, "exchange": stock.exchange, "adjust": batch_adjust, "csv_path": csv_path.as_posix()}
        )
        bars = _load_bars(settings)
        if request.score_mode == "volume_momentum":
            rows.append(_volume_momentum_batch_row(base_row, bars, request, index))
            continue
        if request.score_mode == "chan_structure":
            rows.append(_chan_structure_batch_row(base_row, bars, request, index))
            continue

        preview = build_research_signal_preview(bars, min_bars=request.min_bars, lookback=request.lookback)
        serialized_preview = _serialize(preview)
        rows.append(
            {
                **base_row,
                "status": "scanned",
                "score": serialized_preview["score"],
                "latest_signal": serialized_preview["signals"][-1] if serialized_preview["signals"] else None,
                "preview": serialized_preview,
                "momentum": None,
                "blockers": serialized_preview["blockers"],
                "_order": index,
            }
        )

    if request.score_mode == "volume_momentum":
        rows.sort(key=lambda row: (0 if row["status"] == "scanned" else 1, -((row["score"] or {}).get("total_score", 0)), row["_order"]))
    else:
        rows.sort(key=lambda row: (0 if row["status"] == "scanned" else 1, -abs((row["score"] or {}).get("total_score", 0)), row["_order"]))
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
        row.pop("_order", None)

    available = sum(1 for row in rows if row["status"] == "scanned")
    missing = sum(1 for row in rows if row["status"] == "missing_data")
    return {
        "query": request.query,
        "universe": request.universe,
        "score_mode": request.score_mode,
        "scanned": len(rows),
        "available": available,
        "missing": missing,
        "data_update": update_payload["summary"] if update_payload else _disabled_data_update_summary(request, len(candidates), batch_adjust),
        "rows": rows,
    }


def _research_batch_candidates(request: ResearchSignalBatchRequest) -> list[StockInfo]:
    if request.universe == "current":
        return [StockInfo(request.settings.symbol, request.settings.symbol, request.settings.exchange)]

    catalog = load_stock_catalog()
    if request.universe == "star":
        star_candidates = [stock for stock in catalog if stock.exchange == "SSE" and stock.code.startswith("688")]
        return search_stock_catalog(star_candidates, request.query, request.limit)

    candidates = search_stock_catalog(catalog, request.query, request.limit)
    if request.universe == "local_csv":
        candidates = [
            stock
            for stock in candidates
            if _safe_data_path(_batch_stock_csv_path(stock, request.settings, _batch_adjust(request))).exists()
        ]

    if not candidates and request.universe == "catalog":
        return [StockInfo(request.settings.symbol, request.settings.symbol, request.settings.exchange)]
    return candidates


def _batch_adjust(request: ResearchSignalBatchRequest) -> str:
    return (request.adjust or request.settings.adjust or "qfq").strip().lower()


def _batch_stock_csv_path(stock: StockInfo, settings: PlatformSettings, adjust: str | None = None) -> Path:
    return data_file_for_stock(stock, adjust=adjust or settings.adjust).latest_path


def _update_batch_candidate_data(request: ResearchSignalBatchRequest, candidates: list[StockInfo], adjust: str) -> dict[str, Any]:
    files: list[dict[str, Any]] = []
    statuses: dict[str, dict[str, Any]] = {}
    updated = skipped = failed = 0
    for stock in candidates:
        try:
            result = update_stock_data(
                stock,
                start_date=request.settings.start_date,
                end_date=request.settings.end_date,
                adjust=adjust,
                if_stale=request.if_stale,
            ).as_dict()
        except Exception as exc:
            data_file = data_file_for_stock(stock, adjust=adjust)
            result = {
                "code": stock.code,
                "name": stock.name,
                "exchange": stock.exchange,
                "adjust": adjust,
                "status": "failed",
                "requested_start": request.settings.start_date,
                "requested_end": request.settings.end_date,
                "fetched_start": None,
                "fetched_end": None,
                "fetched_rows": 0,
                "latest_rows": 0,
                "latest_start": None,
                "latest_end": None,
                "latest_path": data_file.latest_path.as_posix(),
                "increment_path": None,
                "message": str(exc),
            }
        files.append(result)
        statuses[stock.code] = _data_status_from_update_result(result)
        if result["status"] == "updated":
            updated += 1
        elif result["status"] == "skipped":
            skipped += 1
        else:
            failed += 1
    return {
        "summary": {
            "enabled": True,
            "total": len(candidates),
            "updated": updated,
            "skipped": skipped,
            "failed": failed,
            "adjust": adjust,
            "start_date": request.settings.start_date,
            "end_date": request.settings.end_date,
        },
        "statuses": statuses,
        "files": files,
    }


def _disabled_data_update_summary(request: ResearchSignalBatchRequest, total: int, adjust: str) -> dict[str, Any]:
    return {
        "enabled": False,
        "total": total,
        "updated": 0,
        "skipped": 0,
        "failed": 0,
        "adjust": adjust,
        "start_date": request.settings.start_date,
        "end_date": request.settings.end_date,
    }


def _data_status_from_update_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": result.get("status", "failed"),
        "message": result.get("message", ""),
        "rows": result.get("latest_rows", 0),
        "start": result.get("latest_start"),
        "end": result.get("latest_end"),
        "path": result.get("latest_path", ""),
    }


def _volume_momentum_batch_row(base_row: dict[str, Any], bars: list[Bar], request: ResearchSignalBatchRequest, order: int) -> dict[str, Any]:
    score, latest_signal, blockers, momentum = _volume_momentum_score(bars, request.min_bars)
    preview = {
        "symbol": base_row["code"],
        "exchange": base_row["exchange"],
        "bars": len(bars),
        "score": score,
        "signals": [latest_signal] if latest_signal else [],
        "blockers": blockers,
        "momentum": momentum,
    }
    return {
        **base_row,
        "status": "scanned",
        "score": score,
        "latest_signal": latest_signal,
        "preview": preview,
        "momentum": momentum,
        "blockers": blockers,
        "_order": order,
    }


def _chan_structure_batch_row(base_row: dict[str, Any], bars: list[Bar], request: ResearchSignalBatchRequest, order: int) -> dict[str, Any]:
    score, latest_signal, blockers, preview = _chan_structure_score(bars, request.min_bars, request.lookback)
    return {
        **base_row,
        "status": "scanned",
        "score": score,
        "latest_signal": latest_signal,
        "preview": preview,
        "momentum": None,
        "blockers": blockers,
        "_order": order,
    }


def _chan_structure_score(
    bars: list[Bar],
    min_bars: int,
    lookback: int,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, str]], dict[str, Any]]:
    if len(bars) < min_bars:
        diagnostics = _chan_structure_diagnostics(0, 0, 0, 0, 0, 0, None)
        blockers = [{"code": "INSUFFICIENT_BARS", "message": f"至少需要 {min_bars} 根K线，当前 {len(bars)} 根"}]
        score = _chan_structure_score_payload(0.0, "neutral", 0.0, "缠论结构样本不足", diagnostics)
        preview = {
            "symbol": bars[-1].symbol if bars else "",
            "exchange": bars[-1].exchange if bars else "",
            "bars": len(bars),
            "signals": [],
            "score": score,
            "blockers": blockers,
            "chan_structure": diagnostics,
        }
        return score, None, blockers, preview

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=5, min_rebound_pct=0.03, lookback=lookback)
    latest_signal = _serialize(result.signals[-1]) if result.signals else None
    total_score = result.chan_score
    direction = "bullish" if total_score > 0 else "bearish" if total_score < 0 else "neutral"
    confidence = round(min(1.0, max(0.0, 0.35 + abs(total_score) / 100.0)), 4)
    diagnostics = _chan_structure_diagnostics(
        len(result.fractals),
        len(result.strokes),
        len(result.pivots),
        len(result.segments),
        len(result.recursive_pivots),
        len(result.divergences),
        latest_signal,
    )
    summary = (
        f"分型 {diagnostics['fractal_count']} 个，笔 {diagnostics['stroke_count']} 条，"
        f"中枢 {diagnostics['pivot_count']} 个，线段 {diagnostics['segment_count']} 条，"
        f"递归中枢 {diagnostics['recursive_pivot_count']} 个，背驰 {diagnostics['divergence_count']} 个，"
        f"{diagnostics['latest_signal_title'] or '暂无结构触发'}"
    )
    score = _chan_structure_score_payload(total_score, direction, confidence, summary, diagnostics)
    blockers = [] if latest_signal else [{"code": "NO_CHAN_STRUCTURE_SIGNAL", "message": summary}]
    preview = {
        "symbol": bars[-1].symbol,
        "exchange": bars[-1].exchange,
        "bars": len(bars),
        "signals": _serialize_many(result.signals),
        "score": score,
        "blockers": blockers,
        "chan_structure": diagnostics,
    }
    return score, latest_signal, blockers, preview


def _chan_structure_diagnostics(
    fractal_count: int,
    stroke_count: int,
    pivot_count: int,
    segment_count: int,
    recursive_pivot_count: int,
    divergence_count: int,
    latest_signal: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "fractal_count": fractal_count,
        "stroke_count": stroke_count,
        "pivot_count": pivot_count,
        "segment_count": segment_count,
        "recursive_pivot_count": recursive_pivot_count,
        "divergence_count": divergence_count,
        "latest_signal_kind": latest_signal["kind"] if latest_signal else None,
        "latest_signal_title": latest_signal["title"] if latest_signal else None,
    }


def _chan_structure_score_payload(
    total_score: float,
    direction: str,
    confidence: float,
    summary: str,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "total_score": total_score,
        "direction": direction,
        "confidence": confidence,
        "chan_score": total_score,
        "rsi_score": 0,
        "summary": summary,
        "chan_structure": diagnostics,
    }


def _volume_momentum_score(bars: list[Bar], min_bars: int) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, str]], dict[str, Any]]:
    latest = bars[-1] if bars else None
    required_previous = max(VOLUME_MOMENTUM_MOMENTUM_WINDOW, VOLUME_MOMENTUM_VOLUME_WINDOW, VOLUME_MOMENTUM_TREND_WINDOW)
    required_total = max(min_bars, required_previous + 1)
    if latest is None or len(bars) < required_total:
        reason = "insufficient_bars"
        blockers = [{"code": "INSUFFICIENT_BARS", "message": f"至少需要 {required_total} 根K线，当前 {len(bars)} 根"}]
        momentum = {
            "momentum_pct": None,
            "volume_ratio": None,
            "trend_pass": False,
            "entry_ready": False,
            "latest_reason": reason,
        }
        return _volume_momentum_score_payload(0.0, "neutral", 0.0, "量价动量样本不足", momentum), None, blockers, momentum

    previous = bars[:-1]
    previous_closes = [bar.close_price for bar in previous]
    previous_volumes = [bar.volume for bar in previous]
    base_close = previous_closes[-VOLUME_MOMENTUM_MOMENTUM_WINDOW]
    volume_baseline = sum(previous_volumes[-VOLUME_MOMENTUM_VOLUME_WINDOW:]) / VOLUME_MOMENTUM_VOLUME_WINDOW
    trend_average = sum(previous_closes[-VOLUME_MOMENTUM_TREND_WINDOW:]) / VOLUME_MOMENTUM_TREND_WINDOW

    momentum_pct = (latest.close_price / base_close - 1) * 100 if base_close > 0 else 0.0
    volume_ratio = latest.volume / volume_baseline if volume_baseline > 0 else 0.0
    trend_pass = latest.close_price > trend_average
    price_pass = momentum_pct >= VOLUME_MOMENTUM_MIN_MOMENTUM_PCT * 100
    volume_pass = volume_ratio >= VOLUME_MOMENTUM_VOLUME_MULTIPLIER
    entry_ready = price_pass and volume_pass and trend_pass
    latest_reason = _volume_momentum_reason(price_pass, volume_pass, trend_pass)

    momentum = {
        "momentum_pct": round(momentum_pct, 4),
        "volume_ratio": round(volume_ratio, 4),
        "trend_pass": trend_pass,
        "entry_ready": entry_ready,
        "latest_reason": latest_reason,
    }
    momentum_component = max(0.0, min(60.0, momentum_pct * 2.5))
    volume_component = max(0.0, min(25.0, (volume_ratio - 1) * 20.0))
    trend_component = 15.0 if trend_pass else 0.0
    total_score = round(momentum_component + volume_component + trend_component, 2)
    confidence = round(min(1.0, max(0.0, 0.35 + total_score / 120.0)), 4)
    if entry_ready:
        direction = "bullish"
    elif momentum_pct <= -VOLUME_MOMENTUM_MIN_MOMENTUM_PCT * 100:
        direction = "bearish"
    else:
        direction = "neutral"

    summary = f"动量 {momentum_pct:.2f}%，放量 {volume_ratio:.2f}倍，趋势{'通过' if trend_pass else '未通过'}"
    score = _volume_momentum_score_payload(total_score, direction, confidence, summary, momentum)
    latest_signal = None
    if entry_ready:
        latest_signal = {
            "title": "量价动量触发",
            "kind": "volume_momentum",
            "symbol": latest.symbol,
            "exchange": latest.exchange,
            "action": "buy",
            "reason": "volume_confirmed_momentum_entry",
            "trading_day": latest.trading_day,
            "price": latest.close_price,
            "strength": confidence,
            "score": total_score,
            "tags": ["volume_momentum"],
        }
    blockers = [] if entry_ready else [{"code": latest_reason.upper(), "message": summary}]
    return score, latest_signal, blockers, momentum


def _volume_momentum_reason(price_pass: bool, volume_pass: bool, trend_pass: bool) -> str:
    if price_pass and volume_pass and trend_pass:
        return "volume_confirmed_momentum_entry"
    if not price_pass:
        return "momentum_not_enough"
    if not volume_pass:
        return "volume_not_enough"
    return "trend_filter_failed"


def _volume_momentum_score_payload(total_score: float, direction: str, confidence: float, summary: str, momentum: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_score": total_score,
        "direction": direction,
        "confidence": confidence,
        "chan_score": 0,
        "rsi_score": 0,
        "summary": summary,
        "momentum": momentum,
    }


def run_paper_request(request: PaperRunRequest) -> dict[str, Any]:
    settings = request.settings
    bars = _load_bars(settings)
    strategy = _strategy_for_mode(request.mode, request.strategy, request.portfolio)
    service = PaperTradingService(
        strategy=strategy,
        initial_cash=settings.initial_cash,
        commission_rate=settings.commission_rate,
        slippage=settings.slippage,
        max_order_cash=settings.max_order_cash,
    )
    events = service.run(bars, log_path=_safe_log_path(settings.log_path))
    return _paper_payload(events)


def paper_events(path: str) -> dict[str, Any]:
    return _paper_payload(load_paper_events(_safe_log_path(path)))


def evaluate_risk(metrics: dict[str, float | int | None], config: RiskConfigView) -> dict[str, Any]:
    status = evaluate_risk_guardrails(
        metrics,
        RiskGuardrailConfig(
            max_drawdown_pct=config.max_drawdown_pct,
            max_order_cash=config.max_order_cash,
            min_cash_balance=config.min_cash_balance,
            max_position_shares=config.max_position_shares,
            cooldown_days=config.cooldown_days,
        ),
        enabled=config.enabled,
    )
    return _serialize(status)


def _load_bars(settings: PlatformSettings) -> list[Bar]:
    path = _safe_data_path(settings.csv_path)
    if not path.exists():
        raise ApiInputError(f"CSV data not found: {settings.csv_path}")
    try:
        return read_bars_csv(path)
    except Exception as exc:
        raise ApiInputError(f"failed to read CSV data: {exc}") from exc


def _build_strategy(selection: StrategySelection) -> Strategy:
    spec = _find_strategy(selection.id)
    params = _params_with_symbol_defaults(spec, selection.params)
    return instantiate_strategy(spec, params)


def _build_portfolio(request: PortfolioRequest) -> PortfolioStrategy:
    allocations, _ = _portfolio_allocations(request)
    return PortfolioStrategy(allocations, mode=request.mode)


def _portfolio_allocations(request: PortfolioRequest) -> tuple[list[StrategyAllocation], list[dict[str, Any]]]:
    allocations: list[StrategyAllocation] = []
    allocation_views: list[dict[str, Any]] = []
    applied = _ai_adjustment_applied(request)
    for index, item in enumerate(request.allocations):
        strategy = _build_strategy(item.strategy)
        spec = _find_strategy(item.strategy.id)
        base_weight = item.weight
        adjusted_weight = round(base_weight + AI_WEIGHT_DELTA, 10) if applied else base_weight
        ai_delta = round(adjusted_weight - base_weight, 10)
        strategy_label = _strategy_display_name(spec)
        allocations.append(StrategyAllocation(strategy_label, strategy, adjusted_weight, item.enabled))
        allocation_views.append(
            {
                "index": index,
                "name": strategy_label,
                "weight": adjusted_weight,
                "base_weight": base_weight,
                "adjusted_weight": adjusted_weight,
                "ai_delta": ai_delta,
                "ai_adjusted": bool(applied and item.enabled),
                "enabled": item.enabled,
            }
        )
    if not allocations:
        raise ApiInputError("portfolio requires at least one strategy allocation")
    return allocations, allocation_views


def _ai_adjustment_summary(request: PortfolioRequest) -> dict[str, Any]:
    return {
        "enabled": request.ai_adjust,
        "direction": request.ai_direction,
        "applied": _ai_adjustment_applied(request),
        "delta": AI_WEIGHT_DELTA,
    }


def _ai_adjustment_applied(request: PortfolioRequest) -> bool:
    return bool(request.ai_adjust and request.ai_direction == "bullish")


def _strategy_for_mode(
    mode: str,
    strategy: StrategySelection | None,
    portfolio: PortfolioRequest | None,
) -> Strategy:
    if mode == "portfolio":
        if portfolio is None:
            raise ApiInputError("portfolio mode requires portfolio")
        return _build_portfolio(portfolio)
    if strategy is None:
        raise ApiInputError("single mode requires strategy")
    return _build_strategy(strategy)


def _find_strategy(strategy_id: str) -> StrategySpec:
    for spec in discover_strategies():
        if spec.id == strategy_id:
            return spec
    raise ApiInputError(f"strategy not found: {strategy_id}")


def _params_with_symbol_defaults(spec: StrategySpec, params: dict[str, Any]) -> dict[str, Any]:
    merged = dict(params)
    for param in inspect_strategy_parameters(spec):
        if param.name == "symbol" and not merged.get("symbol"):
            merged["symbol"] = DEFAULT_SETTINGS.symbol
    return merged


def _strategy_view(spec: StrategySpec) -> dict[str, Any]:
    return {
        "id": spec.id,
        "name": spec.name,
        "display_name": _strategy_display_name(spec),
        "description": spec.description or f"自定义策略：{spec.class_name}，按本地源码定义的交易逻辑运行。",
        "class_name": spec.class_name,
        "source": spec.source,
        "path": str(spec.path) if spec.path else None,
        "editable": spec.source == "user" and spec.path is not None,
        "parameters": [_serialize(param) for param in inspect_strategy_parameters(spec)],
    }


def _strategy_display_name(spec: StrategySpec) -> str:
    return spec.display_name or spec.name


def _stock_view(stock: StockInfo) -> dict[str, str]:
    return {"code": stock.code, "name": stock.name, "exchange": stock.exchange}


def _data_payload(bars: list[Bar], settings: PlatformSettings) -> dict[str, Any]:
    frame = pd.DataFrame([_serialize(bar) for bar in bars])
    summary = {
        "rows": len(bars),
        "csv_path": settings.csv_path,
        "symbol": bars[-1].symbol if bars else settings.symbol,
        "exchange": bars[-1].exchange if bars else settings.exchange,
        "start": bars[0].trading_day.isoformat() if bars else None,
        "end": bars[-1].trading_day.isoformat() if bars else None,
        "latest_close": bars[-1].close_price if bars else None,
        "latest_volume": bars[-1].volume if bars else None,
        "latest_turnover": bars[-1].turnover if bars else None,
    }
    return {"bars": _frame_records(frame), "summary": summary}


def _managed_file_for_settings(settings: PlatformSettings) -> dict[str, Any] | None:
    data_file = data_file_for_stock({"code": settings.symbol, "name": settings.symbol, "exchange": settings.exchange}, adjust=settings.adjust)
    if Path(settings.csv_path).as_posix() != data_file.latest_path.as_posix():
        return None
    return data_file.status(as_of=date.today())


def _paper_payload(events: list[dict[str, Any]]) -> dict[str, Any]:
    orders, equity, summary = paper_events_to_frames(events)
    return {
        "events": _serialize_many(events),
        "orders": _frame_records(orders),
        "equity": _frame_records(equity),
        "summary": _serialize(summary),
    }


def _signal_summary(frame: pd.DataFrame) -> dict[str, Any]:
    if frame.empty:
        return {"signals": 0, "buys": 0, "sells": 0}
    return {
        "signals": len(frame),
        "buys": int((frame["action"] == "buy").sum()),
        "sells": int((frame["action"] == "sell").sum()),
    }


def _risk_config(settings: PlatformSettings) -> RiskGuardrailConfig:
    return RiskGuardrailConfig(
        max_drawdown_pct=settings.max_drawdown_pct,
        max_order_cash=settings.max_order_cash,
        min_cash_balance=settings.min_cash_balance,
        max_position_shares=settings.max_position_shares,
    )


def _safe_strategy_path(value: str | Path) -> Path:
    return _safe_path(value, Path("strategies"), suffix=".py")


def _safe_data_path(value: str | Path) -> Path:
    return _safe_path(value, Path("data"), suffix=".csv")


def _safe_log_path(value: str | Path) -> Path:
    return _safe_path(value, Path("logs"), suffix=".jsonl")


def _safe_path(value: str | Path, root: Path, suffix: str | None = None) -> Path:
    raw = Path(value)
    candidate = raw if raw.is_absolute() else Path.cwd() / raw
    resolved = candidate.resolve()
    root_resolved = (Path.cwd() / root).resolve()
    if resolved != root_resolved and root_resolved not in resolved.parents:
        raise ApiInputError(f"path must stay under {root.as_posix()}: {value}")
    if suffix and resolved.suffix != suffix:
        raise ApiInputError(f"path must end with {suffix}: {value}")
    return resolved


def _demo_bars(symbol: str, exchange: str, count: int = 260) -> list[Bar]:
    start = date(2024, 1, 2)
    bars: list[Bar] = []
    close = 10.0
    for index in range(max(1, count)):
        trend = 0.018 if index < count * 0.62 else -0.006
        cycle = math.sin(index / 8) * 0.035
        direction = 1 if index % 5 in (0, 1, 2) else -1
        body = direction * (0.13 + abs(math.sin(index / 5)) * 0.12)
        open_price = max(2.0, close + math.sin(index / 6) * 0.04)
        close = max(2.0, open_price + trend + cycle + body)
        wick = 0.12 + abs(math.cos(index / 7)) * 0.08
        high_price = max(open_price, close) + wick
        low_price = min(open_price, close) - wick
        volume = 1_000_000 + index * 2500 + abs(math.sin(index / 6)) * 120_000 + (40_000 if direction < 0 else 0)
        bars.append(
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=start + timedelta(days=index),
                open_price=round(open_price, 2),
                high_price=round(high_price, 2),
                low_price=round(low_price, 2),
                close_price=round(close, 2),
                volume=round(volume, 2),
                turnover=round(volume * close, 2),
            )
        )
    return bars


def _frame_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return [_serialize(row) for row in frame.to_dict("records")]


def _serialize_many(values: Iterable[Any]) -> list[Any]:
    return [_serialize(value) for value in values]


def _serialize(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _serialize(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    if pd.isna(value):
        return None
    return value
