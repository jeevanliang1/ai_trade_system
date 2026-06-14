import type {
  AIInsight,
  BacktestResponse,
  Bar,
  DataSummary,
  PaperResponse,
  PlatformSettings,
  PortfolioRequest,
  ResearchSignalPreview,
  RiskStatus,
  SignalsResponse,
  StrategySelection,
  StrategySpec
} from "../types";

export type PlatformState = {
  settings: PlatformSettings;
  strategies: StrategySpec[];
  selectedStrategyId: string;
  strategyParams: Record<string, unknown>;
  bars: Bar[];
  dataSummary: DataSummary | null;
  signals: SignalsResponse | null;
  researchSignals: ResearchSignalPreview | null;
  portfolio: PortfolioRequest;
  backtest: BacktestResponse | null;
  insight: AIInsight | null;
  aiPrompt: string | null;
  riskStatus: RiskStatus | null;
  paper: PaperResponse | null;
  message: string;
  busy: boolean;
  activeBacktestMode: "single" | "portfolio" | null;
  activePaperMode: "single" | "portfolio" | null;
};

export type PlatformActions = {
  setSettings: (settings: PlatformSettings) => void;
  setSelectedStrategyId: (id: string) => void;
  setStrategyParams: (params: Record<string, unknown>) => void;
  setPortfolio: (portfolio: PortfolioRequest) => void;
  refreshStrategies: (selectedId?: string) => Promise<void>;
  loadData: () => Promise<void>;
  demoData: () => Promise<void>;
  downloadData: () => Promise<void>;
  previewSignals: () => Promise<void>;
  previewPortfolio: () => Promise<void>;
  previewResearchSignals: () => Promise<void>;
  runBacktest: (mode?: "single" | "portfolio") => Promise<void>;
  researchAI: (notes: string[], mode: string, horizon: string) => Promise<void>;
  runPaper: (mode?: "single" | "portfolio") => Promise<void>;
  loadPaperEvents: () => Promise<void>;
  evaluateRisk: () => Promise<void>;
};

export type PageProps = {
  state: PlatformState;
  actions: PlatformActions;
};

export function currentStrategy(state: PlatformState): StrategySpec | undefined {
  return state.strategies.find((strategy) => strategy.id === state.selectedStrategyId) ?? state.strategies[0];
}

export function currentSelection(state: PlatformState): StrategySelection {
  const strategy = currentStrategy(state);
  return { id: strategy?.id ?? "", params: state.strategyParams };
}
