from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_trade_system.strategy_defaults import DEFAULT_SCAN_SCORE_MODE


class PlatformSettings(BaseModel):
    symbol: str = "000001"
    exchange: str = "SZSE"
    start_date: str = "20220101"
    end_date: str = "20250516"
    adjust: str = "qfq"
    timeframe: str = "daily"
    csv_path: str = "data/000001_daily.csv"
    log_path: str = "logs/paper_events.jsonl"
    initial_cash: float = 100_000.0
    commission_rate: float = 0.0003
    slippage: float = 0.01
    max_order_cash: float = 50_000.0
    max_drawdown_pct: float = 20.0
    min_cash_balance: float = 0.0
    max_position_shares: int = 50_000
    risk_enabled: bool = True
    stop_loss_mode: str = "fixed_pct"


class StrategyParameterView(BaseModel):
    name: str
    default: Any = None
    annotation: str
    display_name: str = ""
    description: str = ""
    increase_effect: str = ""
    decrease_effect: str = ""
    options: list[str] = Field(default_factory=list)
    multiple: bool = False


class StrategySpecView(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    class_name: str
    source: str
    path: str | None = None
    editable: bool
    parameters: list[StrategyParameterView] = Field(default_factory=list)


class StockView(BaseModel):
    code: str
    name: str
    exchange: str


class WatchlistRequest(BaseModel):
    stocks: list[StockView] = Field(default_factory=list)


class StrategySelection(BaseModel):
    id: str
    params: dict[str, Any] = Field(default_factory=dict)


class PortfolioAllocationRequest(BaseModel):
    strategy: StrategySelection
    weight: float = 1.0
    enabled: bool = True


class PortfolioRequest(BaseModel):
    allocations: list[PortfolioAllocationRequest] = Field(default_factory=list)
    mode: Literal["weighted_vote", "equal_vote", "first_active", "primary_assist"] = "weighted_vote"
    ai_adjust: bool = False
    ai_direction: str | None = None


class RiskConfigView(BaseModel):
    max_drawdown_pct: float = 20.0
    max_order_cash: float = 50_000.0
    min_cash_balance: float = 0.0
    max_position_shares: int = 50_000
    cooldown_days: int = 0
    enabled: bool = True


class DataRequest(BaseModel):
    settings: PlatformSettings


class DemoDataRequest(DataRequest):
    count: int = 260


class DataUpdateWatchlistRequest(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    adjust: str = "qfq"
    timeframe: str = "daily"
    if_stale: bool = True


class StrategySourceRequest(BaseModel):
    filename: str
    source: str


class StrategyTemplateRequest(BaseModel):
    filename: str = "my_strategy.py"
    class_name: str = "MyStrategy"


class SignalsRequest(DataRequest):
    strategy: StrategySelection


class RealtimeStartRequest(DataRequest):
    strategy: StrategySelection
    poll_interval_seconds: float = Field(default=30.0, gt=0, le=3600)


class PortfolioPreviewRequest(DataRequest):
    portfolio: PortfolioRequest


class BacktestRequest(DataRequest):
    strategy: StrategySelection | None = None
    portfolio: PortfolioRequest | None = None
    mode: Literal["single", "portfolio"] = "single"


class AIResearchRequest(DataRequest):
    information_notes: list[str] = Field(default_factory=list)
    prompt_mode: Literal["balanced", "conservative", "aggressive"] = "balanced"
    horizon: str = "5个交易日"


class ResearchSignalsRequest(DataRequest):
    min_bars: int = Field(default=60, ge=20, le=500)
    lookback: int = Field(default=120, ge=20, le=500)


class ResearchSignalBatchRequest(DataRequest):
    query: str = ""
    limit: int = Field(default=20, ge=1, le=300)
    min_bars: int = Field(default=60, ge=20, le=500)
    lookback: int = Field(default=120, ge=20, le=500)
    universe: Literal["catalog", "local_csv", "current", "star"] = "catalog"
    score_mode: Literal["research", "volume_momentum", "chan_structure", "chan_multilevel_daily_anchor"] = DEFAULT_SCAN_SCORE_MODE
    auto_update_data: bool = False
    if_stale: bool = True
    adjust: str | None = None


class AutomationConfigRequest(BaseModel):
    enabled: bool | None = None
    top_n: int | None = Field(default=None, ge=1, le=50)
    chan_weight: float | None = Field(default=None, ge=0, le=5)
    volume_weight: float | None = Field(default=None, ge=0, le=5)
    weekly_analysis_enabled: bool | None = None
    weekly_analysis_top_n: int | None = Field(default=None, ge=1, le=50)
    weekly_delivery_enabled: bool | None = None
    weekly_delivery_channel: str | None = None


class PaperRunRequest(DataRequest):
    strategy: StrategySelection | None = None
    portfolio: PortfolioRequest | None = None
    mode: Literal["single", "portfolio"] = "single"


class RiskEvaluateRequest(BaseModel):
    metrics: dict[str, float | int | None] = Field(default_factory=dict)
    config: RiskConfigView


class AgentTaskRequest(BaseModel):
    prompt: str
    source: str = "frontend"
    context: dict[str, Any] = Field(default_factory=dict)


class AgentApprovalRequest(BaseModel):
    approval: str = "approved"


class AgentMemoryRequest(BaseModel):
    id: str
    type: str = "note"
    scope: str = "agent"
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)
    source: str = "user"
    confidence: str = "medium"
    enabled: bool = True
    expires_at: str | None = None


class AgentMemoryPatchRequest(BaseModel):
    type: str | None = None
    scope: str | None = None
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None
    source: str | None = None
    confidence: str | None = None
    enabled: bool | None = None
    expires_at: str | None = None


class AgentSkillRequest(BaseModel):
    id: str
    title: str
    description: str
    trigger_terms: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    allowed_tools: list[str] = Field(default_factory=list)
    required_confirmations: list[str] = Field(default_factory=list)
    output_format: str = "agent_report"
    enabled: bool = True


class AgentSkillPatchRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    trigger_terms: list[str] | None = None
    steps: list[str] | None = None
    allowed_tools: list[str] | None = None
    required_confirmations: list[str] | None = None
    output_format: str | None = None
    enabled: bool | None = None


class AgentPlannerPolicyRequest(BaseModel):
    max_steps: int | None = Field(default=None, ge=1, le=25)
    blocked_intents: list[str] | None = None
    tool_permissions: dict[str, str] | None = None
    default_output_format: str | None = None


class AgentPlanPreviewRequest(BaseModel):
    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
