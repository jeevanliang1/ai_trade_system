import type {
  AIResearchResponse,
  BacktestResponse,
  BootstrapResponse,
  DataResponse,
  PaperResponse,
  PlatformSettings,
  PortfolioRequest,
  RiskStatus,
  SignalsResponse,
  Stock,
  StrategySelection,
  StrategySpec
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
  previewPortfolio: (settings: PlatformSettings, portfolio: PortfolioRequest) =>
    apiRequest<SignalsResponse>("/api/portfolio/preview", { method: "POST", body: JSON.stringify({ settings, portfolio }) }),
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
