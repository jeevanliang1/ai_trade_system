export type PlatformSettings = {
  symbol: string;
  exchange: string;
  start_date: string;
  end_date: string;
  adjust: string;
  timeframe: "daily" | "1m" | "5m" | "15m" | "30m" | "60m" | string;
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
  display_name?: string;
  description?: string;
  increase_effect?: string;
  decrease_effect?: string;
  options?: string[];
  multiple?: boolean;
};

export type StrategySpec = {
  id: string;
  name: string;
  display_name: string;
  description: string;
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
  timestamp?: string | null;
  timeframe?: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  turnover: number;
};

export type SignalRow = {
  trading_day: string;
  timestamp?: string | null;
  timeframe?: string;
  action: "buy" | "sell";
  symbol: string;
  price: number;
  volume: number;
  reason: string;
};

export type RealtimeMonitorStatus = {
  running: boolean;
  started_at: string | null;
  stopped_at: string | null;
  strategy_id: string | null;
  symbols: string[];
  timeframe: string | null;
  poll_interval_seconds: number | null;
  event_count: number;
  last_event_at: string | null;
  last_bar_time: string | null;
  last_error: string | null;
};

export type RealtimeMonitorEvent = {
  id: string;
  event: string;
  created_at: string;
  symbol?: string;
  name?: string;
  exchange?: string;
  timeframe?: string;
  bar_time?: string;
  close_price?: number;
  volume?: number;
  side?: "buy" | "sell" | string;
  price?: number;
  reason?: string;
  warmup?: boolean;
  message?: string;
  symbols?: string[];
  updated_bars?: number;
  signals?: number;
};

export type RealtimeMonitorEventsResponse = {
  events: RealtimeMonitorEvent[];
};

export type RealtimeMonitorState = {
  status: RealtimeMonitorStatus;
  events: RealtimeMonitorEvent[];
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
  metadata?: Record<string, string | number | boolean | null>;
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
  momentum?: ResearchSignalMomentum | null;
  chan_structure?: ResearchSignalChanStructure | null;
};

export type ResearchSignalMomentum = {
  momentum_pct: number | null;
  volume_ratio: number | null;
  trend_pass: boolean;
  entry_ready: boolean;
  latest_reason: string;
};

export type ChanFractalOverlay = {
  index: number;
  trading_day: string;
  kind: "top" | "bottom" | string;
  price: number;
  high: number;
  low: number;
};

export type ChanStrokeOverlay = {
  direction: "up" | "down" | string;
  start_index: number;
  end_index: number;
  start_day: string;
  end_day: string;
  start_price: number;
  end_price: number;
  high: number;
  low: number;
};

export type ChanPivotOverlay = {
  start_index: number;
  end_index: number;
  start_day: string;
  end_day: string;
  low: number;
  high: number;
};

export type ChanSegmentOverlay = {
  level: "segment" | string;
  sequence_index: number;
  lineage_id: string;
  direction: "up" | "down" | string;
  start_index: number;
  end_index: number;
  start_stroke_index: number;
  end_stroke_index: number;
  break_stroke_index: number | null;
  start_day: string;
  end_day: string;
  start_price: number;
  end_price: number;
  high: number;
  low: number;
  stroke_count: number;
  energy: number;
  broken_by_next: boolean;
};

export type ChanRecursivePivotOverlay = {
  level: "stroke" | "segment" | string;
  start_index: number;
  end_index: number;
  start_day: string;
  end_day: string;
  low: number;
  high: number;
  direction: "up" | "down" | string;
  component_count: number;
};

export type ChanDivergenceOverlay = {
  kind: "top" | "bottom" | string;
  action: "buy" | "sell" | string;
  start_index: number;
  end_index: number;
  reference_start_index: number;
  reference_end_index: number;
  reference_energy: number;
  current_energy: number;
  price_extreme: number;
  base_score: number;
  macd_strength: number;
  volume_strength: number;
  confirmation_score: number;
  macd_reference: number;
  macd_current: number;
  volume_reference: number;
  volume_current: number;
  pivot_level: "stroke" | "segment" | string | null;
  pivot_start_index: number | null;
  pivot_end_index: number | null;
  pivot_low: number | null;
  pivot_high: number | null;
};

export type ResearchSignalChanStructure = {
  fractal_count: number;
  stroke_count: number;
  pivot_count: number;
  segment_count?: number;
  recursive_pivot_count?: number;
  divergence_count?: number;
  latest_signal_kind: string | null;
  latest_signal_title: string | null;
  fractals?: ChanFractalOverlay[];
  strokes?: ChanStrokeOverlay[];
  pivots?: ChanPivotOverlay[];
  segments?: ChanSegmentOverlay[];
  recursive_pivots?: ChanRecursivePivotOverlay[];
  divergences?: ChanDivergenceOverlay[];
  signals?: ResearchSignal[];
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
  momentum?: ResearchSignalMomentum | null;
  chan_structure?: ResearchSignalChanStructure | null;
};

export type ResearchSignalBatchScoreMode = "research" | "volume_momentum" | "chan_structure" | "chan_multilevel_daily_anchor";

export type ResearchSignalBatchDataStatus = {
  status: string;
  message: string;
  rows: number;
  start: string | null;
  end: string | null;
  path: string;
};

export type ResearchSignalBatchDataUpdate = {
  enabled: boolean;
  total: number;
  updated: number;
  skipped: number;
  failed: number;
  adjust: string;
  start_date: string;
  end_date: string;
};

export type ResearchSignalBatchRow = {
  rank: number;
  code: string;
  name: string;
  exchange: string;
  csv_path: string;
  status: "scanned" | "missing_data" | string;
  score: ResearchSignalScore | null;
  latest_signal: ResearchSignal | null;
  preview: ResearchSignalPreview | null;
  momentum?: ResearchSignalMomentum | null;
  data_status?: ResearchSignalBatchDataStatus | null;
  blockers: ResearchSignalBlocker[];
};

export type ResearchSignalBatchResponse = {
  query: string;
  universe: "catalog" | "local_csv" | "current" | string;
  score_mode: ResearchSignalBatchScoreMode | string;
  scanned: number;
  available: number;
  missing: number;
  data_update?: ResearchSignalBatchDataUpdate | null;
  rows: ResearchSignalBatchRow[];
};

export type TradeRow = {
  trading_day: string;
  side: string;
  symbol: string;
  price: number;
  volume: number;
  commission: number;
};

export type TradeAttributionRow = TradeRow & {
  signal_reason: string;
  signal_family: string;
  signal_label: string;
};

export type SignalAttributionRow = {
  family: string;
  label: string;
  trade_count: number;
  buy_count: number;
  sell_count: number;
  entry_closed_trades: number;
  entry_realized_pnl: number;
  entry_return_pct: number;
  entry_win_rate_pct: number | null;
  entry_profit_factor: number | null;
  entry_realized_drawdown_pct: number;
  exit_closed_trades: number;
  exit_realized_pnl: number;
  exit_return_pct: number;
  exit_win_rate_pct: number | null;
  exit_profit_factor: number | null;
  exit_realized_drawdown_pct: number;
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
  trade_attributions?: TradeAttributionRow[];
  signal_attribution?: SignalAttributionRow[];
  risk_status: RiskStatus;
};

export type BootstrapResponse = {
  settings: PlatformSettings;
  catalog_available: boolean;
  catalog_size: number;
  stocks: Stock[];
  watchlist?: Stock[];
  managed_data?: ManagedDataFile[];
  strategies: StrategySpec[];
  portfolio_presets?: PortfolioPreset[];
  limits: Record<string, unknown>;
};

export type WatchlistResponse = {
  stocks: Stock[];
};

export type ManagedDataFile = {
  code: string;
  name: string;
  exchange: string;
  adjust: string;
  timeframe: string;
  latest_path: string;
  manifest_path: string;
  exists: boolean;
  stale: boolean;
  latest_start: string | null;
  latest_end: string | null;
  latest_rows: number;
  last_increment_path: string | null;
  last_updated_at: string | null;
  last_status: string | null;
  last_error: string | null;
};

export type WatchlistDataUpdateRequest = {
  start_date?: string;
  end_date?: string;
  adjust?: string;
  timeframe?: string;
  if_stale?: boolean;
};

export type WatchlistDataUpdateResult = {
  code: string;
  name: string;
  exchange: string;
  adjust: string;
  timeframe: string;
  status: "updated" | "skipped" | "failed" | string;
  requested_start: string;
  requested_end: string;
  fetched_start: string | null;
  fetched_end: string | null;
  fetched_rows: number;
  latest_rows: number;
  latest_start: string | null;
  latest_end: string | null;
  latest_path: string;
  increment_path: string | null;
  message: string;
};

export type ManagedDataResponse = {
  files: ManagedDataFile[];
};

export type WatchlistDataUpdateResponse = {
  updated: number;
  skipped: number;
  failed: number;
  files: WatchlistDataUpdateResult[];
};

export type AutomationConfig = {
  enabled: boolean;
  timezone: string;
  weekly_weekday: number;
  weekly_time: string;
  daily_time: string;
  top_n: number;
  adjust: string;
  min_bars: number;
  lookback: number;
  chan_weight: number;
  volume_weight: number;
  weekly_analysis_enabled: boolean;
  weekly_analysis_top_n: number;
  weekly_delivery_enabled: boolean;
  weekly_delivery_channel: string;
};

export type AutomationConfigRequest = Partial<
  Pick<
    AutomationConfig,
    | "enabled"
    | "top_n"
    | "chan_weight"
    | "volume_weight"
    | "weekly_analysis_enabled"
    | "weekly_analysis_top_n"
    | "weekly_delivery_enabled"
    | "weekly_delivery_channel"
  >
>;

export type AutomationRunRecord = {
  run_id: string;
  task: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  message: string;
};

export type AutomationDiagnostic = {
  code: string;
  severity: "info" | "medium" | "high" | string;
  task: string;
  message: string;
  suggestion: string;
  run_id: string | null;
  created_at: string | null;
};

export type RadarCandidateScore = {
  code: string;
  name: string;
  exchange: string;
  rank: number;
  composite_score: number;
  chan_score: number;
  volume_score: number;
  latest_day: string | null;
  latest_close: number | null;
  chan_signal_title: string | null;
  chan_signal_action: string | null;
  volume_entry_ready: boolean;
  reason: string;
};

export type WeeklyRadarResult = {
  run_id?: string;
  generated_at: string | null;
  status: string;
  total_candidates?: number;
  scanned?: number;
  missing?: number;
  top: RadarCandidateScore[];
};

export type DailyJudgment = {
  code: string;
  name: string;
  exchange: string;
  judgment: string;
  reason: string;
  current_score: number;
  baseline_score: number;
  latest_day: string | null;
  latest_close: number | null;
  chan_signal_title: string | null;
  volume_entry_ready: boolean;
};

export type DailyJudgmentResponse = {
  date: string;
  judgments: DailyJudgment[];
};

export type AutomationStatus = {
  config: AutomationConfig;
  running: boolean;
  last_weekly_run: AutomationRunRecord | null;
  last_daily_run: AutomationRunRecord | null;
  weekly_top10_count: number;
  latest_daily_judgment_count: number;
  weekly_analysis_status: string | null;
  weekly_analysis_run_id: string | null;
  weekly_delivery_status: string | null;
  next_weekly_run: string | null;
  next_daily_run: string | null;
  recent_runs: AutomationRunRecord[];
  diagnostics: AutomationDiagnostic[];
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
  mode: "weighted_vote" | "equal_vote" | "first_active" | "primary_assist";
  ai_adjust: boolean;
  ai_direction?: string | null;
};

export type PortfolioPresetAllocation = PortfolioAllocation & {
  role: string;
  display_name: string;
};

export type PortfolioPreset = {
  id: string;
  name: string;
  description: string;
  mode: PortfolioRequest["mode"];
  allocations: PortfolioPresetAllocation[];
};

export type DataSummary = {
  rows: number;
  csv_path: string;
  timeframe: string;
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
  managed_file?: ManagedDataFile | null;
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

export type AgentTool = {
  name: string;
  description: string;
  permission: "auto" | "confirm" | "blocked" | string;
  category: string;
};

export type AgentStep = {
  tool_name: string;
  title: string;
  status: string;
  started_at?: string | null;
  finished_at?: string | null;
  summary: string;
  output: Record<string, unknown>;
};

export type AgentConfirmation = {
  code: string;
  message: string;
  risk_level: string;
  status: string;
  tool_name?: string | null;
  created_at: string;
  resolved_at?: string | null;
};

export type AgentTask = {
  task_id: string;
  source: string;
  prompt: string;
  status: "pending" | "queued" | "running" | "completed" | "waiting_confirmation" | "blocked" | "failed" | string;
  context: Record<string, unknown>;
  plan: string[];
  steps: AgentStep[];
  evidence: Record<string, unknown>[];
  result_summary: string;
  confirmations: AgentConfirmation[];
  report_path?: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentTraceEvent = {
  event_id: string;
  task_id: string;
  type: string;
  created_at: string;
  tool_name?: string | null;
  status?: string | null;
  summary: string;
  payload: Record<string, unknown>;
};

export type AgentToolsResponse = {
  tools: AgentTool[];
};

export type AgentTasksResponse = {
  tasks: AgentTask[];
};

export type AgentTaskResponse = {
  task: AgentTask;
};

export type AgentTraceResponse = {
  task_id: string;
  events: AgentTraceEvent[];
};

export type AgentMemory = {
  id: string;
  type: string;
  scope: string;
  title: string;
  content: string;
  tags: string[];
  source: string;
  confidence: string;
  enabled: boolean;
  expires_at?: string | null;
};

export type AgentSkill = {
  id: string;
  title: string;
  description: string;
  trigger_terms: string[];
  steps: string[];
  allowed_tools: string[];
  required_confirmations: string[];
  output_format: string;
  enabled: boolean;
};

export type AgentPlannerPolicy = {
  max_steps: number;
  blocked_intents: string[];
  tool_permissions: Record<string, string>;
  default_output_format: string;
};

export type AgentPlanPreviewStep = {
  index: number;
  tool: string;
  title?: string;
  permission: string;
  reason: string;
};

export type AgentPlanPreview = {
  status: string;
  intent: string;
  selected_skill: Partial<AgentSkill> | null;
  matched_memories: Partial<AgentMemory>[];
  steps: AgentPlanPreviewStep[];
  stop_conditions: string[];
  final_output: string;
  blocked_reason?: string | null;
  ignored_tools: string[];
};

export type AgentMemoriesResponse = {
  memories: AgentMemory[];
};

export type AgentMemoryResponse = {
  memory: AgentMemory;
};

export type AgentSkillsResponse = {
  skills: AgentSkill[];
};

export type AgentSkillResponse = {
  skill: AgentSkill;
};

export type AgentPlannerPolicyResponse = {
  policy: AgentPlannerPolicy;
};

export type AgentPlanPreviewResponse = {
  preview: AgentPlanPreview;
};
