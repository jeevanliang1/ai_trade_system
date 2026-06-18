from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class PlatformSettings(BaseModel):
    symbol: str = "000001"
    exchange: str = "SZSE"
    start_date: str = "20220101"
    end_date: str = "20250516"
    adjust: str = "qfq"
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
    mode: Literal["weighted_vote", "equal_vote", "first_active"] = "weighted_vote"
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
    if_stale: bool = True


class StrategySourceRequest(BaseModel):
    filename: str
    source: str


class StrategyTemplateRequest(BaseModel):
    filename: str = "my_strategy.py"
    class_name: str = "MyStrategy"


class SignalsRequest(DataRequest):
    strategy: StrategySelection


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
    limit: int = Field(default=20, ge=1, le=50)
    min_bars: int = Field(default=60, ge=20, le=500)
    lookback: int = Field(default=120, ge=20, le=500)
    universe: Literal["catalog", "local_csv", "current"] = "catalog"
    score_mode: Literal["research", "volume_momentum", "chan_structure"] = "research"


class PaperRunRequest(DataRequest):
    strategy: StrategySelection | None = None
    portfolio: PortfolioRequest | None = None
    mode: Literal["single", "portfolio"] = "single"


class RiskEvaluateRequest(BaseModel):
    metrics: dict[str, float | int | None] = Field(default_factory=dict)
    config: RiskConfigView
