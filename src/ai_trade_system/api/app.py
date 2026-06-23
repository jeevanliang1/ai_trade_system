from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import service
from .schemas import (
    AIResearchRequest,
    AgentApprovalRequest,
    AgentMemoryPatchRequest,
    AgentMemoryRequest,
    AgentPlanPreviewRequest,
    AgentPlannerPolicyRequest,
    AgentSkillPatchRequest,
    AgentSkillRequest,
    AgentTaskRequest,
    AutomationConfigRequest,
    BacktestRequest,
    DataRequest,
    DataUpdateWatchlistRequest,
    DemoDataRequest,
    PaperRunRequest,
    PortfolioPreviewRequest,
    RealtimeStartRequest,
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
    def managed_data(adjust: str = "qfq", timeframe: str = "daily") -> dict[str, Any]:
        return _handle(lambda: service.list_managed_data(adjust=adjust, timeframe=timeframe))

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

    @app.post("/api/realtime/start")
    def realtime_start(request: RealtimeStartRequest) -> dict[str, Any]:
        return _handle(lambda: service.start_realtime_monitor(request))

    @app.post("/api/realtime/stop")
    def realtime_stop() -> dict[str, Any]:
        return _handle(service.stop_realtime_monitor)

    @app.get("/api/realtime/status")
    def realtime_status() -> dict[str, Any]:
        return _handle(service.realtime_monitor_status)

    @app.get("/api/realtime/events")
    def realtime_events(limit: int = 100) -> dict[str, Any]:
        return _handle(lambda: service.realtime_monitor_events(limit))

    @app.get("/api/agent/tools")
    def agent_tools() -> dict[str, Any]:
        return _handle(service.agent_tools)

    @app.get("/api/agent/tasks")
    def agent_tasks(limit: int = 50) -> dict[str, Any]:
        return _handle(lambda: service.agent_tasks(limit))

    @app.post("/api/agent/tasks")
    def agent_create_task(request: AgentTaskRequest) -> dict[str, Any]:
        return _handle(lambda: service.create_agent_task(request.prompt, request.source, request.context))

    @app.get("/api/agent/tasks/{task_id}")
    def agent_task(task_id: str) -> dict[str, Any]:
        return _handle(lambda: service.agent_task(task_id))

    @app.get("/api/agent/tasks/{task_id}/trace")
    def agent_trace(task_id: str) -> dict[str, Any]:
        return _handle(lambda: service.agent_trace(task_id))

    @app.post("/api/agent/tasks/{task_id}/approve")
    def agent_approve_task(task_id: str, request: AgentApprovalRequest) -> dict[str, Any]:
        return _handle(lambda: service.approve_agent_task(task_id, request.approval))

    @app.get("/api/agent/governance/memories")
    def agent_memories() -> dict[str, Any]:
        return _handle(service.agent_memories)

    @app.post("/api/agent/governance/memories")
    def agent_create_memory(request: AgentMemoryRequest) -> dict[str, Any]:
        return _handle(lambda: service.create_agent_memory(request.model_dump()))

    @app.put("/api/agent/governance/memories/{memory_id}")
    def agent_update_memory(memory_id: str, request: AgentMemoryPatchRequest) -> dict[str, Any]:
        return _handle(lambda: service.update_agent_memory(memory_id, request.model_dump(exclude_none=True)))

    @app.delete("/api/agent/governance/memories/{memory_id}")
    def agent_delete_memory(memory_id: str) -> dict[str, Any]:
        return _handle(lambda: service.delete_agent_memory(memory_id))

    @app.get("/api/agent/governance/skills")
    def agent_skills() -> dict[str, Any]:
        return _handle(service.agent_skills)

    @app.post("/api/agent/governance/skills")
    def agent_create_skill(request: AgentSkillRequest) -> dict[str, Any]:
        return _handle(lambda: service.create_agent_skill(request.model_dump()))

    @app.put("/api/agent/governance/skills/{skill_id}")
    def agent_update_skill(skill_id: str, request: AgentSkillPatchRequest) -> dict[str, Any]:
        return _handle(lambda: service.update_agent_skill(skill_id, request.model_dump(exclude_none=True)))

    @app.delete("/api/agent/governance/skills/{skill_id}")
    def agent_delete_skill(skill_id: str) -> dict[str, Any]:
        return _handle(lambda: service.delete_agent_skill(skill_id))

    @app.get("/api/agent/governance/policy")
    def agent_policy() -> dict[str, Any]:
        return _handle(service.agent_policy)

    @app.put("/api/agent/governance/policy")
    def agent_update_policy(request: AgentPlannerPolicyRequest) -> dict[str, Any]:
        return _handle(lambda: service.update_agent_policy(request.model_dump(exclude_none=True)))

    @app.post("/api/agent/governance/plan-preview")
    def agent_plan_preview(request: AgentPlanPreviewRequest) -> dict[str, Any]:
        return _handle(lambda: service.agent_plan_preview(request.prompt, request.context))

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
