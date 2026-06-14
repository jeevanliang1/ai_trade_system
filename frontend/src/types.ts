export type PlatformSettings = {
  symbol: string;
  exchange: string;
  start_date: string;
  end_date: string;
  adjust: string;
  csv_path: string;
  log_path: string;
  initial_cash: number;
  commission_rate: number;
  slippage: number;
  max_order_cash: number;
  max_drawdown_pct: number;
  min_cash_balance: number;
  max_position_shares: number;
  risk_enabled: boolean;
  stop_loss_mode: "fixed_pct" | "trailing" | "manual";
};

export type StrategyParameter = {
  name: string;
  default: unknown;
  annotation: string;
};

export type StrategySpec = {
  id: string;
  name: string;
  class_name: string;
  source: "builtin" | "user" | string;
  path: string | null;
  editable: boolean;
  parameters: StrategyParameter[];
};

export type Stock = {
  code: string;
  name: string;
  exchange: string;
};

export type Bar = {
  symbol: string;
  exchange: string;
  trading_day: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  turnover: number;
};

export type SignalRow = {
  trading_day: string;
  action: "buy" | "sell";
  symbol: string;
  price: number;
  volume: number;
  reason: string;
};

export type ResearchSignal = {
  trading_day: string;
  symbol: string;
  exchange: string;
  kind: string;
  action: "buy" | "sell" | "watch" | string;
  price: number;
  strength: number;
  score: number;
  title: string;
  reason: string;
  tags: string[];
};

export type ResearchSignalBlocker = {
  code: "NO_BARS" | "INSUFFICIENT_BARS" | "UNSUPPORTED_DATA" | "OPTIONAL_ENGINE_UNAVAILABLE" | string;
  message: string;
};

export type ResearchSignalScore = {
  total_score: number;
  direction: "bullish" | "bearish" | "neutral" | string;
  confidence: number;
  chan_score: number;
  rsi_score: number;
  summary: string;
};

export type ResearchSignalPreview = {
  symbol: string;
  exchange: string;
  start: string | null;
  end: string | null;
  bars: number;
  signals: ResearchSignal[];
  score: ResearchSignalScore;
  blockers: ResearchSignalBlocker[];
};

export type TradeRow = {
  trading_day: string;
  side: string;
  symbol: string;
  price: number;
  volume: number;
  commission: number;
};

export type EquityPoint = {
  trading_day: string;
  equity: number;
  cash: number;
  close_price?: number;
};

export type DrawdownPoint = {
  trading_day: string;
  equity: number;
  drawdown_pct: number;
};

export type BacktestMetrics = {
  final_equity: number;
  total_return_pct: number;
  annualized_return_pct: number;
  benchmark_return_pct: number;
  excess_return_pct: number;
  annual_volatility_pct: number;
  sharpe_ratio: number | null;
  max_drawdown_pct: number;
  trade_count: number;
  win_rate_pct: number | null;
  profit_factor: number | null;
  exposure_pct: number;
};

export type RiskStatus = {
  ok: boolean;
  warnings: string[];
  enabled: boolean;
};

export type AIInsight = {
  symbol: string;
  horizon: string;
  direction: "bullish" | "bearish" | "neutral" | string;
  confidence: number;
  suggested_action: string;
  technical_evidence: string[];
  information_evidence: string[];
  risk_warnings: string[];
  prompt_version: string;
  provider: string;
  created_at: string;
};

export type BacktestResponse = {
  bars: Bar[];
  metrics: BacktestMetrics;
  equity_curve: EquityPoint[];
  drawdowns: DrawdownPoint[];
  trades: TradeRow[];
  risk_status: RiskStatus;
};

export type BootstrapResponse = {
  settings: PlatformSettings;
  catalog_available: boolean;
  catalog_size: number;
  stocks: Stock[];
  strategies: StrategySpec[];
  limits: Record<string, unknown>;
};

export type StrategySelection = {
  id: string;
  params: Record<string, unknown>;
};

export type PortfolioAllocation = {
  strategy: StrategySelection;
  weight: number;
  enabled: boolean;
};

export type PortfolioRequest = {
  allocations: PortfolioAllocation[];
  mode: "weighted_vote" | "equal_vote" | "first_active";
  ai_adjust: boolean;
  ai_direction?: string | null;
};

export type DataSummary = {
  rows: number;
  csv_path: string;
  symbol: string;
  exchange: string;
  start: string | null;
  end: string | null;
  latest_close: number | null;
  latest_volume: number | null;
  latest_turnover: number | null;
};

export type DataResponse = {
  bars: Bar[];
  summary: DataSummary;
};

export type PortfolioSignalContribution = {
  allocation_index: number;
  name: string;
  action: "buy" | "sell" | string;
  score: number;
  weight: number;
  volume: number;
  reason: string;
  selected: boolean;
};

export type PortfolioSignalBreakdown = {
  buy_score: number;
  sell_score: number;
  active_signals: number;
  mode: PortfolioRequest["mode"] | string;
  reasons: string[];
  contributions: PortfolioSignalContribution[];
};

export type PortfolioPreviewAllocation = {
  index: number;
  name: string;
  weight: number;
  base_weight?: number;
  adjusted_weight?: number;
  ai_delta?: number;
  ai_adjusted?: boolean;
  enabled: boolean;
};

export type PortfolioAiAdjustment = {
  enabled: boolean;
  direction: string | null;
  applied: boolean;
  delta: number;
};

export type SignalsResponse = {
  bars: Bar[];
  signals: SignalRow[];
  summary: { signals: number; buys: number; sells: number };
  breakdown?: PortfolioSignalBreakdown;
  allocations?: PortfolioPreviewAllocation[];
  ai_adjustment?: PortfolioAiAdjustment;
};

export type AIResearchResponse = {
  snapshot: Record<string, unknown>;
  prompt: string;
  insight: AIInsight;
};

export type PaperResponse = {
  events: Record<string, unknown>[];
  orders: Record<string, unknown>[];
  equity: Record<string, unknown>[];
  summary: Record<string, unknown>;
};
