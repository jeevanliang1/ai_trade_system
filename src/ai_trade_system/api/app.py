from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import service
from .schemas import (
    AIResearchRequest,
    AutomationConfigRequest,
    BacktestRequest,
    DataRequest,
    DataUpdateWatchlistRequest,
    DemoDataRequest,
    PaperRunRequest,
    PortfolioPreviewRequest,
    ResearchSignalBatchRequest,
    ResearchSignalsRequest,
    RiskEvaluateRequest,
    SignalsRequest,
    StrategySourceRequest,
    StrategyTemplateRequest,
    WatchlistRequest,
)


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        scheduler = service.get_automation_scheduler()
        scheduler.start()
        try:
            yield
        finally:
            scheduler.stop()

    app = FastAPI(title="AI Trade System API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/bootstrap")
    def bootstrap() -> dict[str, Any]:
        return _handle(service.bootstrap)

    @app.get("/api/stocks")
    def stocks(query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        return _handle(lambda: service.list_stocks(query, limit))

    @app.get("/api/watchlist")
    def watchlist() -> dict[str, Any]:
        return _handle(service.list_watchlist)

    @app.put("/api/watchlist")
    def save_watchlist(request: WatchlistRequest) -> dict[str, Any]:
        return _handle(lambda: service.put_watchlist([stock.model_dump() for stock in request.stocks]))

    @app.post("/api/data/load")
    def load_data(request: DataRequest) -> dict[str, Any]:
        return _handle(lambda: service.load_data(request))

    @app.post("/api/data/download")
    def download_data(request: DataRequest) -> dict[str, Any]:
        return _handle(lambda: service.download_data(request))

    @app.get("/api/data/managed")
    def managed_data() -> dict[str, Any]:
        return _handle(service.list_managed_data)

    @app.post("/api/data/update-watchlist")
    def update_watchlist_data(request: DataUpdateWatchlistRequest) -> dict[str, Any]:
        return _handle(lambda: service.update_watchlist_data(request))

    @app.post("/api/data/demo")
    def demo_data(request: DemoDataRequest) -> dict[str, Any]:
        return _handle(lambda: service.demo_data(request))

    @app.get("/api/automation/status")
    def automation_status() -> dict[str, Any]:
        return _handle(service.automation_status)

    @app.get("/api/automation/radar/top10")
    def automation_top10() -> dict[str, Any]:
        return _handle(service.automation_top10)

    @app.get("/api/automation/judgments")
    def automation_judgments(day: str | None = None) -> dict[str, Any]:
        return _handle(lambda: service.automation_judgments(day))

    @app.post("/api/automation/run-weekly")
    def automation_run_weekly() -> dict[str, Any]:
        return _handle(service.run_automation_weekly)

    @app.post("/api/automation/run-daily")
    def automation_run_daily() -> dict[str, Any]:
        return _handle(service.run_automation_daily)

    @app.put("/api/automation/config")
    def automation_config(request: AutomationConfigRequest) -> dict[str, Any]:
        return _handle(lambda: service.update_automation_config(request.model_dump(exclude_none=True)))

    @app.get("/api/strategies")
    def strategies() -> list[dict[str, Any]]:
        return _handle(service.list_strategies)

    @app.get("/api/strategies/source")
    def strategy_source(path: str) -> dict[str, str]:
        return _handle(lambda: service.get_strategy_source(path))

    @app.put("/api/strategies/source")
    def save_strategy_source(request: StrategySourceRequest) -> dict[str, Any]:
        return _handle(lambda: service.put_strategy_source(request.filename, request.source))

    @app.post("/api/strategies/template")
    def create_strategy_template(request: StrategyTemplateRequest) -> dict[str, Any]:
        return _handle(lambda: service.create_strategy_file(request.filename, request.class_name))

    @app.post("/api/signals/preview")
    def signals_preview(request: SignalsRequest) -> dict[str, Any]:
        return _handle(lambda: service.preview_signals(request))

    @app.post("/api/portfolio/preview")
    def portfolio_preview(request: PortfolioPreviewRequest) -> dict[str, Any]:
        return _handle(lambda: service.preview_portfolio(request))

    @app.post("/api/backtest")
    def backtest(request: BacktestRequest) -> dict[str, Any]:
        return _handle(lambda: service.run_backtest_request(request))

    @app.post("/api/ai/research")
    def ai_research(request: AIResearchRequest) -> dict[str, Any]:
        return _handle(lambda: service.research_ai(request))

    @app.post("/api/research/signals/preview")
    def research_signals_preview(request: ResearchSignalsRequest) -> dict[str, Any]:
        return _handle(lambda: service.preview_research_signals(request))

    @app.post("/api/research/signals/batch")
    def research_signals_batch(request: ResearchSignalBatchRequest) -> dict[str, Any]:
        return _handle(lambda: service.batch_research_signals(request))

    @app.post("/api/paper/run")
    def paper_run(request: PaperRunRequest) -> dict[str, Any]:
        return _handle(lambda: service.run_paper_request(request))

    @app.get("/api/paper/events")
    def paper_events(path: str = "logs/paper_events.jsonl") -> dict[str, Any]:
        return _handle(lambda: service.paper_events(path))

    @app.post("/api/risk/evaluate")
    def risk_evaluate(request: RiskEvaluateRequest) -> dict[str, Any]:
        return _handle(lambda: service.evaluate_risk(request.metrics, request.config))

    return app


def _handle(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except service.ApiInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


app = create_app()
