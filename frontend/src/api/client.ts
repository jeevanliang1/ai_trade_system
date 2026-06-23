import type {
  AIResearchResponse,
  AgentMemoriesResponse,
  AgentMemory,
  AgentMemoryResponse,
  AgentPlanPreviewResponse,
  AgentPlannerPolicy,
  AgentPlannerPolicyResponse,
  AgentSkill,
  AgentSkillResponse,
  AgentSkillsResponse,
  AgentTaskResponse,
  AgentTasksResponse,
  AgentTraceResponse,
  AgentToolsResponse,
  AutomationConfig,
  AutomationConfigRequest,
  AutomationStatus,
  BacktestResponse,
  BootstrapResponse,
  DataResponse,
  DailyJudgmentResponse,
  ManagedDataResponse,
  PaperResponse,
  PlatformSettings,
  PortfolioRequest,
  RealtimeMonitorEventsResponse,
  RealtimeMonitorStatus,
  ResearchSignalBatchScoreMode,
  ResearchSignalBatchResponse,
  ResearchSignalPreview,
  RiskStatus,
  SignalsResponse,
  Stock,
  StrategySelection,
  StrategySpec,
  WeeklyRadarResult,
  WatchlistDataUpdateRequest,
  WatchlistDataUpdateResponse,
  WatchlistResponse
} from "../types";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    let message = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      message = payload.detail ?? message;
    } catch {
      // Keep the HTTP status text when the server does not return JSON.
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export const api = {
  bootstrap: () => apiRequest<BootstrapResponse>("/api/bootstrap"),
  stocks: (query: string, limit = 20) => apiRequest<Stock[]>(`/api/stocks?query=${encodeURIComponent(query)}&limit=${limit}`),
  watchlist: () => apiRequest<WatchlistResponse>("/api/watchlist"),
  saveWatchlist: (stocks: Stock[]) => apiRequest<WatchlistResponse>("/api/watchlist", { method: "PUT", body: JSON.stringify({ stocks }) }),
  managedData: (timeframe = "daily", adjust = "qfq") =>
    apiRequest<ManagedDataResponse>(`/api/data/managed?timeframe=${encodeURIComponent(timeframe)}&adjust=${encodeURIComponent(adjust)}`),
  updateWatchlistData: (request: WatchlistDataUpdateRequest = {}) =>
    apiRequest<WatchlistDataUpdateResponse>("/api/data/update-watchlist", { method: "POST", body: JSON.stringify(request) }),
  automationStatus: () => apiRequest<AutomationStatus>("/api/automation/status"),
  automationTop10: () => apiRequest<WeeklyRadarResult>("/api/automation/radar/top10"),
  automationJudgments: (day?: string) =>
    apiRequest<DailyJudgmentResponse>(`/api/automation/judgments${day ? `?day=${encodeURIComponent(day)}` : ""}`),
  updateAutomationConfig: (request: AutomationConfigRequest) =>
    apiRequest<AutomationConfig>("/api/automation/config", { method: "PUT", body: JSON.stringify(request) }),
  agentTools: () => apiRequest<AgentToolsResponse>("/api/agent/tools"),
  agentTasks: (limit = 50) => apiRequest<AgentTasksResponse>(`/api/agent/tasks?limit=${limit}`),
  createAgentTask: (prompt: string, source = "frontend", context: Record<string, unknown> = {}) =>
    apiRequest<AgentTaskResponse>("/api/agent/tasks", {
      method: "POST",
      body: JSON.stringify({ prompt, source, context })
    }),
  approveAgentTask: (taskId: string, approval = "approved") =>
    apiRequest<AgentTaskResponse>(`/api/agent/tasks/${encodeURIComponent(taskId)}/approve`, {
      method: "POST",
      body: JSON.stringify({ approval })
    }),
  agentTaskTrace: (taskId: string) => apiRequest<AgentTraceResponse>(`/api/agent/tasks/${encodeURIComponent(taskId)}/trace`),
  agentMemories: () => apiRequest<AgentMemoriesResponse>("/api/agent/governance/memories"),
  createAgentMemory: (memory: AgentMemory) =>
    apiRequest<AgentMemoryResponse>("/api/agent/governance/memories", { method: "POST", body: JSON.stringify(memory) }),
  updateAgentMemory: (memoryId: string, patch: Partial<AgentMemory>) =>
    apiRequest<AgentMemoryResponse>(`/api/agent/governance/memories/${encodeURIComponent(memoryId)}`, {
      method: "PUT",
      body: JSON.stringify(patch)
    }),
  deleteAgentMemory: (memoryId: string) =>
    apiRequest<{ deleted: boolean; id: string }>(`/api/agent/governance/memories/${encodeURIComponent(memoryId)}`, { method: "DELETE" }),
  agentSkills: () => apiRequest<AgentSkillsResponse>("/api/agent/governance/skills"),
  createAgentSkill: (skill: AgentSkill) =>
    apiRequest<AgentSkillResponse>("/api/agent/governance/skills", { method: "POST", body: JSON.stringify(skill) }),
  updateAgentSkill: (skillId: string, patch: Partial<AgentSkill>) =>
    apiRequest<AgentSkillResponse>(`/api/agent/governance/skills/${encodeURIComponent(skillId)}`, {
      method: "PUT",
      body: JSON.stringify(patch)
    }),
  deleteAgentSkill: (skillId: string) =>
    apiRequest<{ deleted: boolean; id: string }>(`/api/agent/governance/skills/${encodeURIComponent(skillId)}`, { method: "DELETE" }),
  agentPolicy: () => apiRequest<AgentPlannerPolicyResponse>("/api/agent/governance/policy"),
  updateAgentPolicy: (policy: Partial<AgentPlannerPolicy>) =>
    apiRequest<AgentPlannerPolicyResponse>("/api/agent/governance/policy", { method: "PUT", body: JSON.stringify(policy) }),
  previewAgentPlan: (prompt: string, context: Record<string, unknown> = {}) =>
    apiRequest<AgentPlanPreviewResponse>("/api/agent/governance/plan-preview", {
      method: "POST",
      body: JSON.stringify({ prompt, context })
    }),
  runAutomationWeekly: () => apiRequest<WeeklyRadarResult>("/api/automation/run-weekly", { method: "POST" }),
  runAutomationDaily: () => apiRequest<DailyJudgmentResponse>("/api/automation/run-daily", { method: "POST" }),
  strategies: () => apiRequest<StrategySpec[]>("/api/strategies"),
  strategySource: (path: string) => apiRequest<{ path: string; source: string }>(`/api/strategies/source?path=${encodeURIComponent(path)}`),
  saveStrategySource: (filename: string, source: string) =>
    apiRequest<{ path: string; strategies: StrategySpec[] }>("/api/strategies/source", {
      method: "PUT",
      body: JSON.stringify({ filename, source })
    }),
  createStrategyTemplate: (filename: string, class_name: string) =>
    apiRequest<{ path: string; strategies: StrategySpec[] }>("/api/strategies/template", {
      method: "POST",
      body: JSON.stringify({ filename, class_name })
    }),
  demoData: (settings: PlatformSettings, count = 260) =>
    apiRequest<DataResponse>("/api/data/demo", { method: "POST", body: JSON.stringify({ settings, count }) }),
  loadData: (settings: PlatformSettings) =>
    apiRequest<DataResponse>("/api/data/load", { method: "POST", body: JSON.stringify({ settings }) }),
  downloadData: (settings: PlatformSettings) =>
    apiRequest<DataResponse>("/api/data/download", { method: "POST", body: JSON.stringify({ settings }) }),
  previewSignals: (settings: PlatformSettings, strategy: StrategySelection) =>
    apiRequest<SignalsResponse>("/api/signals/preview", { method: "POST", body: JSON.stringify({ settings, strategy }) }),
  startRealtimeMonitor: (settings: PlatformSettings, strategy: StrategySelection, poll_interval_seconds = 30) =>
    apiRequest<RealtimeMonitorStatus>("/api/realtime/start", {
      method: "POST",
      body: JSON.stringify({ settings, strategy, poll_interval_seconds })
    }),
  stopRealtimeMonitor: () => apiRequest<RealtimeMonitorStatus>("/api/realtime/stop", { method: "POST" }),
  realtimeStatus: () => apiRequest<RealtimeMonitorStatus>("/api/realtime/status"),
  realtimeEvents: (limit = 100) => apiRequest<RealtimeMonitorEventsResponse>(`/api/realtime/events?limit=${limit}`),
  previewPortfolio: (settings: PlatformSettings, portfolio: PortfolioRequest) =>
    apiRequest<SignalsResponse>("/api/portfolio/preview", { method: "POST", body: JSON.stringify({ settings, portfolio }) }),
  previewResearchSignals: (settings: PlatformSettings, min_bars = 60, lookback = 120) =>
    apiRequest<ResearchSignalPreview>("/api/research/signals/preview", {
      method: "POST",
      body: JSON.stringify({ settings, min_bars, lookback })
    }),
  batchResearchSignals: (
    settings: PlatformSettings,
    options: {
      query: string;
      limit: number;
      min_bars: number;
      lookback: number;
      universe?: "catalog" | "local_csv" | "current" | "star";
      score_mode?: ResearchSignalBatchScoreMode;
      auto_update_data?: boolean;
      if_stale?: boolean;
      adjust?: string | null;
    } = {
      query: "",
      limit: 20,
      min_bars: 60,
      lookback: 120,
      universe: "catalog",
      score_mode: "chan_multilevel_daily_anchor"
    }
  ) =>
    apiRequest<ResearchSignalBatchResponse>("/api/research/signals/batch", {
      method: "POST",
      body: JSON.stringify({ settings, ...options })
    }),
  runBacktest: (settings: PlatformSettings, strategy: StrategySelection | null, portfolio: PortfolioRequest | null, mode: "single" | "portfolio") =>
    apiRequest<BacktestResponse>("/api/backtest", { method: "POST", body: JSON.stringify({ settings, strategy, portfolio, mode }) }),
  research: (settings: PlatformSettings, information_notes: string[], prompt_mode: string, horizon: string) =>
    apiRequest<AIResearchResponse>("/api/ai/research", {
      method: "POST",
      body: JSON.stringify({ settings, information_notes, prompt_mode, horizon })
    }),
  runPaper: (settings: PlatformSettings, strategy: StrategySelection | null, portfolio: PortfolioRequest | null, mode: "single" | "portfolio") =>
    apiRequest<PaperResponse>("/api/paper/run", { method: "POST", body: JSON.stringify({ settings, strategy, portfolio, mode }) }),
  paperEvents: (path: string) => apiRequest<PaperResponse>(`/api/paper/events?path=${encodeURIComponent(path)}`),
  evaluateRisk: (metrics: Record<string, number | null>, settings: PlatformSettings) =>
    apiRequest<RiskStatus>("/api/risk/evaluate", {
      method: "POST",
      body: JSON.stringify({
        metrics,
        config: {
          max_drawdown_pct: settings.max_drawdown_pct,
          max_order_cash: settings.max_order_cash,
          min_cash_balance: settings.min_cash_balance,
          max_position_shares: settings.max_position_shares,
          cooldown_days: 0,
          enabled: settings.risk_enabled
        }
      })
    })
};
