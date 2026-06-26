import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BarChart3,
  Bot,
  BrainCircuit,
  Command,
  Database,
  Gauge,
  Home,
  Layers3,
  NotebookTabs,
  RadioTower,
  Radar,
  ShieldCheck,
  SlidersHorizontal,
  Star,
  TimerReset,
} from "lucide-react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { InspectorPanel } from "../components/InspectorPanel";
import { StockQuickSelect } from "../components/StockQuickSelect";
import { ToolbarButton } from "../components/ToolbarButton";
import { AIPage } from "../pages/AIPage";
import { AgentGovernancePage } from "../pages/AgentGovernancePage";
import { AgentPage } from "../pages/AgentPage";
import { AutomationPage } from "../pages/AutomationPage";
import { BacktestPage } from "../pages/BacktestPage";
import { DataPage } from "../pages/DataPage";
import { OverviewPage } from "../pages/OverviewPage";
import { PaperPage } from "../pages/PaperPage";
import { PortfolioPage } from "../pages/PortfolioPage";
import { RiskPage } from "../pages/RiskPage";
import { RealtimePage } from "../pages/RealtimePage";
import { SignalRadarPage } from "../pages/SignalRadarPage";
import { StockConfigPage } from "../pages/StockConfigPage";
import { StrategyPage } from "../pages/StrategyPage";
import { currentSelection, strategyDisplayName } from "../pages/pageTypes";
import type { PlatformActions, PlatformState } from "../pages/pageTypes";
import { defaultTwoYearDateRange } from "../utils/dateRange";
import type {
  BootstrapResponse,
  PlatformSettings,
  PortfolioPreset,
  PortfolioRequest,
  RealtimeMarketSource,
  RealtimeMonitorSource,
  Stock,
  StrategySpec,
  WatchlistDataUpdateRequest
} from "../types";

export const NAV_GROUPS = [
  {
    label: "准备",
    items: [
      { id: "overview", label: "总览", icon: Home },
      { id: "stocks", label: "股票配置", icon: Star },
      { id: "data", label: "数据中心", icon: Database },
      { id: "radar", label: "信号雷达", icon: Radar }
    ]
  },
  {
    label: "策略",
    items: [
      { id: "strategies", label: "策略工坊", icon: SlidersHorizontal },
      { id: "portfolio", label: "组合实验室", icon: Layers3 }
    ]
  },
  {
    label: "验证",
    items: [
      { id: "backtest", label: "回测中心", icon: BarChart3 },
      { id: "realtime", label: "实时盯盘", icon: RadioTower },
      { id: "paper", label: "纸面交易", icon: NotebookTabs }
    ]
  },
  {
    label: "辅助",
    items: [
      { id: "agent", label: "AI指挥台", icon: Command },
      { id: "agent-governance", label: "Agent治理", icon: BrainCircuit },
      { id: "ai", label: "AI研究员", icon: Bot },
      { id: "risk", label: "风控", icon: ShieldCheck },
      { id: "automation", label: "自动任务", icon: TimerReset }
    ]
  }
] as const;

export const NAV_ITEMS = [
  ...NAV_GROUPS[0].items,
  ...NAV_GROUPS[1].items,
  ...NAV_GROUPS[2].items,
  ...NAV_GROUPS[3].items
] as const;

type PageId = (typeof NAV_GROUPS)[number]["items"][number]["id"];

const DEFAULT_RANGE = defaultTwoYearDateRange();

const DEFAULT_SETTINGS: PlatformSettings = {
  symbol: "",
  exchange: "",
  start_date: DEFAULT_RANGE.start_date,
  end_date: DEFAULT_RANGE.end_date,
  adjust: "qfq",
  timeframe: "daily",
  csv_path: "",
  log_path: "logs/paper_events.jsonl",
  initial_cash: 100000,
  commission_rate: 0.0003,
  slippage: 0.01,
  max_order_cash: 50000,
  max_drawdown_pct: 20,
  min_cash_balance: 0,
  max_position_shares: 50000,
  risk_enabled: true,
  stop_loss_mode: "fixed_pct"
};

const FALLBACK_STRATEGIES: StrategySpec[] = [
  {
    id: "builtin:popular:ChanStructureStrategy",
    name: "ChanStructureStrategy",
    display_name: "缠论结构策略",
    description: "从分型、笔和中枢结构中识别缠论买卖点。",
    class_name: "ChanStructureStrategy",
    source: "builtin",
    path: null,
    editable: false,
    parameters: [
      { name: "symbol", annotation: "str", default: "" },
      { name: "trade_size", annotation: "int", default: 100 }
    ]
  }
];

function initialState(): PlatformState {
  return {
    settings: DEFAULT_SETTINGS,
    watchlist: [],
    managedData: [],
    strategies: FALLBACK_STRATEGIES,
    portfolioPresets: [],
    selectedStrategyId: FALLBACK_STRATEGIES[0].id,
    strategyParams: { symbol: "", trade_size: 100 },
    bars: [],
    dataSummary: null,
    signals: null,
    researchSignals: null,
    portfolio: defaultPortfolio(FALLBACK_STRATEGIES[0].id),
    backtest: null,
    insight: null,
    aiPrompt: null,
    riskStatus: { ok: true, warnings: [], enabled: true },
    paper: null,
    realtime: null,
    message: "准备就绪",
    busy: false,
    activeBacktestMode: null,
    activePaperMode: null
  };
}

export function AppShell() {
  const [activePage, setActivePage] = useState<PageId>("strategies");
  const [state, setState] = useState<PlatformState>(() => initialState());

  useEffect(() => {
    let mounted = true;
    async function hydrate() {
      try {
        const bootstrap = await api.bootstrap();
        if (!mounted) return;
        setState((current) => fromBootstrap(current, bootstrap));
        if (bootstrap.settings.symbol && bootstrap.settings.csv_path) {
          try {
            const data = await api.loadData(bootstrap.settings);
            if (!mounted) return;
            setState((current) => ({ ...current, bars: data.bars, dataSummary: data.summary, message: `已加载 ${data.bars.length} 根K线` }));
          } catch {
            const demo = await api.demoData(bootstrap.settings, 260);
            if (!mounted) return;
            setState((current) => ({ ...current, bars: demo.bars, dataSummary: demo.summary, message: `已生成 ${demo.bars.length} 根演示K线` }));
          }
        }
      } catch (error) {
        if (!mounted) return;
        setState((current) => ({ ...current, message: formatError(error) }));
      }
    }
    void hydrate();
    return () => {
      mounted = false;
    };
  }, []);

  const actions = useMemo<PlatformActions>(
    () => ({
      setSettings: (settings) =>
        setState((current) => {
          return applySettings(current, settings);
        }),
      selectStock: (stock) => {
        let request: WatchlistDataUpdateRequest | null = null;
        setState((current) => {
          request = fiveYearMaintenanceRequest(current.settings);
          return applyStockSelection(current, stock);
        });
        if (request) void refreshManagedData(setState, request);
      },
      setWatchlist: (watchlist) => setState((current) => ({ ...current, watchlist })),
      updateWatchlistData: (request = {}) =>
        runTask(setState, "更新自选股数据", async (current) => {
          const updateRequest = {
            start_date: current.settings.start_date,
            end_date: current.settings.end_date,
            adjust: current.settings.adjust,
            timeframe: current.settings.timeframe,
            if_stale: true,
            ...request
          };
          await api.updateWatchlistData(updateRequest);
          const managed = await api.managedData(updateRequest.timeframe ?? "daily", updateRequest.adjust ?? "qfq");
          return { managedData: managed.files };
        }),
      setSelectedStrategyId: (id) => {
        setState((current) => {
          const strategy = current.strategies.find((item) => item.id === id);
          return {
            ...current,
            selectedStrategyId: id,
            strategyParams: paramsFromStrategy(strategy, current.settings.symbol)
          };
        });
      },
      setStrategyParams: (strategyParams) => setState((current) => ({ ...current, strategyParams })),
      setPortfolio: (portfolio) => setState((current) => ({ ...current, portfolio })),
      refreshStrategies: (selectedId) =>
        runTask(setState, "刷新策略", async (current) => {
          const strategies = await api.strategies();
          if (!selectedId) return { strategies };
          const selected = strategies.find((item) => item.id === selectedId);
          if (!selected) return { strategies };
          return {
            strategies,
            selectedStrategyId: selected.id,
            strategyParams: paramsFromStrategy(selected, current.settings.symbol)
          };
        }),
      loadData: () =>
        runTask(setState, "加载CSV", async (current) => {
          const data = await api.loadData(current.settings);
          return { bars: data.bars, dataSummary: data.summary };
        }),
      demoData: () =>
        runTask(setState, "生成演示数据", async (current) => {
          const data = await api.demoData(current.settings, 260);
          return { bars: data.bars, dataSummary: data.summary };
        }),
      downloadData: () =>
        runTask(setState, "下载行情数据", async (current) => {
          const data = await api.downloadData(current.settings);
          const patch: Partial<PlatformState> = { bars: data.bars, dataSummary: data.summary };
          if (data.managed_file) {
            patch.managedData = upsertManagedData(current.managedData, data.managed_file);
          }
          return patch;
        }),
      previewSignals: () =>
        runTask(setState, "预览信号", async (current) => ({ signals: await api.previewSignals(current.settings, currentSelection(current)) })),
      previewPortfolio: () =>
        runTask(setState, "预览组合", async (current) => ({ signals: await api.previewPortfolio(current.settings, current.portfolio) })),
      previewResearchSignals: () =>
        runTask(setState, "生成缠论/RSI研判", async (current) => ({ researchSignals: await api.previewResearchSignals(current.settings) })),
      runBacktest: (mode = "single") =>
        runTask(setState, `运行${backtestModeLabel(mode)}回测`, async (current) => {
          const backtest = await api.runBacktest(current.settings, currentSelection(current), current.portfolio, mode);
          return { backtest, riskStatus: backtest.risk_status };
        }, { startPatch: { activeBacktestMode: mode }, finishPatch: { activeBacktestMode: null } }),
      researchAI: (notes, promptMode, horizon) =>
        runTask(setState, "生成AI观点", async (current) => {
          const research = await api.research(current.settings, notes, promptMode, horizon);
          const patch: Partial<PlatformState> = { insight: research.insight, aiPrompt: research.prompt };
          if (current.portfolio.ai_adjust) {
            patch.portfolio = { ...current.portfolio, ai_direction: research.insight.direction };
          }
          return patch;
        }),
      runPaper: (mode = "single") =>
        runTask(setState, "运行纸面交易", async (current) => ({
          paper: await api.runPaper(current.settings, currentSelection(current), current.portfolio, mode)
        }), { startPatch: { activePaperMode: mode }, finishPatch: { activePaperMode: null } }),
      loadPaperEvents: () =>
        runTask(setState, "加载纸面事件", async (current) => ({
          paper: await api.paperEvents(current.settings.log_path)
        })),
      evaluateRisk: () =>
        runTask(setState, "检查风控", async (current) => ({
          riskStatus: await api.evaluateRisk({ max_drawdown_pct: current.backtest?.metrics.max_drawdown_pct ?? 0 }, current.settings)
        })),
      startRealtimeMonitor: (
        pollIntervalSeconds = 30,
        monitorSources: RealtimeMonitorSource[] = ["current"],
        marketSources: RealtimeMarketSource[] = ["a_share"]
      ) =>
        runTask(setState, "启动实时盯盘", async (current) => {
          const status = await api.startRealtimeMonitor(current.settings, currentSelection(current), pollIntervalSeconds, monitorSources, marketSources);
          const events = await api.realtimeEvents(100);
          return { realtime: { status, events: events.events } };
        }),
      stopRealtimeMonitor: () =>
        runTask(setState, "停止实时盯盘", async () => {
          const status = await api.stopRealtimeMonitor();
          const events = await api.realtimeEvents(100);
          return { realtime: { status, events: events.events } };
        }),
      refreshRealtimeMonitor: () =>
        runTask(setState, "刷新实时盯盘", async () => {
          const [status, events] = await Promise.all([api.realtimeStatus(), api.realtimeEvents(100)]);
          return { realtime: { status, events: events.events } };
        })
    }),
    [state.strategies]
  );

  const pageProps = { state, actions };
  const page = {
    overview: <OverviewPage {...pageProps} />,
    stocks: <StockConfigPage {...pageProps} />,
    data: <DataPage {...pageProps} />,
    strategies: <StrategyPage {...pageProps} />,
    portfolio: <PortfolioPage {...pageProps} />,
    backtest: <BacktestPage {...pageProps} />,
    radar: <SignalRadarPage {...pageProps} />,
    realtime: <RealtimePage {...pageProps} />,
    agent: <AgentPage />,
    "agent-governance": <AgentGovernancePage />,
    ai: <AIPage {...pageProps} />,
    paper: <PaperPage {...pageProps} />,
    risk: <RiskPage {...pageProps} />,
    automation: <AutomationPage {...pageProps} />
  }[activePage];

  return (
    <div className="app-shell">
      <SideNav activePage={activePage} setActivePage={setActivePage} />
      <div className="app-main">
        <TopCommandBar state={state} activePage={activePage} setActivePage={setActivePage} onStockSelect={actions.selectStock} />
        <div className="content-shell">
          <div className="content-area">{page}</div>
          <InspectorPanel
            insight={state.insight}
            riskStatus={state.riskStatus}
            settings={state.settings}
            portfolio={state.portfolio}
            onSettingsChange={actions.setSettings}
            onPortfolioChange={actions.setPortfolio}
          />
        </div>
        <StatusBar state={state} />
      </div>
    </div>
  );
}

function SideNav({ activePage, setActivePage }: { activePage: PageId; setActivePage: (page: PageId) => void }) {
  return (
    <aside className="side-nav">
      <div className="brand">
        <div className="brand-mark">
          <Gauge size={22} />
        </div>
        <strong>AI量化平台</strong>
      </div>
      <nav>
        {NAV_GROUPS.map((group) => (
          <div className="nav-group" key={group.label}>
            <div className="nav-group-label">{group.label}</div>
            {group.items.map((item) => {
              const Icon = item.icon;
              return (
                <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => setActivePage(item.id)}>
                  <Icon size={18} />
                  {item.label}
                </button>
              );
            })}
          </div>
        ))}
      </nav>
    </aside>
  );
}

function TopCommandBar({
  state,
  activePage,
  setActivePage,
  onStockSelect
}: {
  state: PlatformState;
  activePage: PageId;
  setActivePage: (page: PageId) => void;
  onStockSelect: (stock: Stock) => void;
}) {
  const selectedStrategy = strategyDisplayName(state.strategies.find((item) => item.id === state.selectedStrategyId)) ?? "-";
  const selectedStockLabel = state.settings.symbol && state.settings.exchange ? `${state.settings.symbol} ${state.settings.exchange}` : "请选择股票";
  const nextStep = nextStepFor(activePage);
  return (
    <header className="topbar">
      <div className="market-status">
        <strong>{selectedStockLabel}</strong>
        <span className="dot" />
        <span>已连接</span>
        <span>数据日期：{state.bars.at(-1)?.trading_day ?? state.settings.end_date}</span>
        <span>策略：{selectedStrategy}</span>
      </div>
      <div className="toolbar">
        <StockQuickSelect label="全局自选股票" value={state.settings} stocks={state.watchlist} onSelect={onStockSelect} onSearch={api.stocks} compact />
        <ToolbarButton icon={<ArrowRight size={15} />} variant="primary" onClick={() => setActivePage(nextStep.page)}>
          {nextStep.label}
        </ToolbarButton>
      </div>
    </header>
  );
}

function nextStepFor(page: PageId): { label: string; page: PageId } {
  if (page === "overview") return { label: "去股票配置", page: "stocks" };
  if (page === "stocks") return { label: "去数据中心", page: "data" };
  if (page === "data") return { label: "去策略工坊", page: "strategies" };
  if (page === "radar") return { label: "去数据中心", page: "data" };
  if (page === "strategies") return { label: "去回测中心", page: "backtest" };
  if (page === "portfolio") return { label: "去回测中心", page: "backtest" };
  if (page === "backtest") return { label: "去实时盯盘", page: "realtime" };
  if (page === "realtime") return { label: "去纸面交易", page: "paper" };
  if (page === "agent") return { label: "去AI研究员", page: "ai" };
  if (page === "agent-governance") return { label: "去AI指挥台", page: "agent" };
  if (page === "ai") return { label: "去风控", page: "risk" };
  if (page === "risk") return { label: "去纸面交易", page: "paper" };
  if (page === "automation") return { label: "去数据中心", page: "data" };
  return { label: "回到总览", page: "overview" };
}

function StatusBar({ state }: { state: PlatformState }) {
  const selectedStrategy = strategyDisplayName(state.strategies.find((item) => item.id === state.selectedStrategyId)) ?? "-";
  const health = state.riskStatus?.ok === false ? "告警" : "正常";
  return (
    <footer className="statusbar">
      <span>数据：本地CSV</span>
      <span>周期：{state.settings.timeframe}</span>
      <span>路径：{state.settings.csv_path}</span>
      <span>健康：{health}</span>
      <span>{state.message}</span>
      <span>策略：{selectedStrategy}</span>
      <span>回测区间：{state.settings.start_date} - {state.settings.end_date}</span>
      <span>初始资金：{state.settings.initial_cash.toLocaleString()}</span>
      <span>手续费：{(state.settings.commission_rate * 100).toFixed(2)}%</span>
      <span>滑点：{state.settings.slippage}</span>
      <span>日志：{state.settings.log_path}</span>
    </footer>
  );
}

function fromBootstrap(current: PlatformState, bootstrap: BootstrapResponse): PlatformState {
  const strategies = bootstrap.strategies.length ? bootstrap.strategies : FALLBACK_STRATEGIES;
  const selectedStrategyId = strategies[0].id;
  return {
    ...current,
    settings: bootstrap.settings,
    watchlist: bootstrap.watchlist ?? [],
    managedData: bootstrap.managed_data ?? [],
    strategies,
    portfolioPresets: syncPortfolioPresetSymbols(bootstrap.portfolio_presets ?? [], bootstrap.settings.symbol),
    selectedStrategyId,
    strategyParams: paramsFromStrategy(strategies[0], bootstrap.settings.symbol),
    portfolio: defaultPortfolio(selectedStrategyId),
    message: `已连接 MockProvider，发现 ${strategies.length} 个策略`
  };
}

function applySettings(current: PlatformState, settings: PlatformSettings): PlatformState {
  if (!dataRequestChanged(current.settings, settings)) {
    return { ...current, settings };
  }
  return {
    ...current,
    settings,
    bars: [],
    dataSummary: null,
    signals: null,
    researchSignals: null,
    backtest: null,
    paper: null,
    realtime: null,
    message: `已切换数据目标：${settings.symbol} ${settings.exchange}，请加载或下载行情`
  };
}

function applyStockSelection(current: PlatformState, stock: Stock): PlatformState {
  const settings = {
    ...current.settings,
    symbol: stock.code,
    exchange: stock.exchange,
    csv_path: managedCsvPath(stock, current.settings.adjust, current.settings.timeframe)
  };
  const next = applySettings(current, settings);
  return {
    ...next,
    strategyParams: syncSymbolParam(next.strategyParams, stock.code),
    portfolioPresets: syncPortfolioPresetSymbols(next.portfolioPresets, stock.code),
    portfolio: {
      ...next.portfolio,
      allocations: next.portfolio.allocations.map((allocation) => ({
        ...allocation,
        strategy: {
          ...allocation.strategy,
          params: syncSymbolParam(allocation.strategy.params, stock.code)
        }
      }))
    }
  };
}

function managedCsvPath(stock: Stock, adjust: string, timeframe: string): string {
  const cleanAdjust = (adjust || "qfq").toLowerCase();
  const cleanTimeframe = normalizeTimeframe(timeframe);
  const market = stock.exchange === "CRYPTO" ? "crypto" : ["NASDAQ", "NYSE", "AMEX", "US"].includes(stock.exchange) ? "us_stock" : "a_share";
  return `data/market/${market}/${stock.exchange}/${stock.code}/${stock.code}_${stock.exchange}_${cleanTimeframe}_${cleanAdjust}_latest.csv`;
}

function upsertManagedData(files: PlatformState["managedData"], file: PlatformState["managedData"][number]) {
  const key = `${file.exchange}:${file.code}:${file.adjust}:${file.timeframe}`;
  const others = files.filter((item) => `${item.exchange}:${item.code}:${item.adjust}:${item.timeframe}` !== key);
  return [...others, file];
}

function syncSymbolParam(params: Record<string, unknown>, symbol: string): Record<string, unknown> {
  if (!("symbol" in params)) return params;
  return { ...params, symbol };
}

function syncPortfolioPresetSymbols(presets: PortfolioPreset[], symbol: string): PortfolioPreset[] {
  return presets.map((preset) => ({
    ...preset,
    allocations: preset.allocations.map((allocation) => ({
      ...allocation,
      strategy: {
        ...allocation.strategy,
        params: syncSymbolParam(allocation.strategy.params, symbol)
      }
    }))
  }));
}

function paramsFromStrategy(strategy: StrategySpec | undefined, symbol: string): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const parameter of strategy?.parameters ?? []) {
    params[parameter.name] = parameter.name === "symbol" ? symbol : parameter.default;
  }
  return params;
}

function defaultPortfolio(strategyId: string): PortfolioRequest {
  return {
    mode: "weighted_vote",
    ai_adjust: false,
    ai_direction: null,
    allocations: [{ strategy: { id: strategyId, params: { symbol: "", fast: 5, slow: 20, size: 100 } }, weight: 1, enabled: true }]
  };
}

function dataRequestChanged(previous: PlatformSettings, next: PlatformSettings): boolean {
  return (
    previous.symbol !== next.symbol ||
    previous.exchange !== next.exchange ||
    previous.start_date !== next.start_date ||
    previous.end_date !== next.end_date ||
    previous.adjust !== next.adjust ||
    previous.timeframe !== next.timeframe ||
    previous.csv_path !== next.csv_path
  );
}

function normalizeTimeframe(timeframe: string): string {
  return timeframe || "daily";
}

function fiveYearMaintenanceRequest(settings: PlatformSettings): WatchlistDataUpdateRequest {
  const endDate = settings.end_date || DEFAULT_RANGE.end_date;
  return {
    start_date: shiftDateYears(endDate, -5),
    end_date: endDate,
    adjust: settings.adjust,
    timeframe: settings.timeframe,
    if_stale: true
  };
}

function shiftDateYears(dateKey: string, years: number): string {
  const year = Number(dateKey.slice(0, 4));
  const month = dateKey.slice(4, 6);
  const day = dateKey.slice(6, 8);
  if (!Number.isFinite(year) || month.length !== 2 || day.length !== 2) return dateKey;
  return `${year + years}${month}${day}`;
}

async function refreshManagedData(setState: React.Dispatch<React.SetStateAction<PlatformState>>, request: WatchlistDataUpdateRequest) {
  try {
    await api.updateWatchlistData(request);
    const managed = await api.managedData(request.timeframe ?? "daily", request.adjust ?? "qfq");
    if (!managed?.files) return;
    setState((current) => ({ ...current, managedData: managed.files }));
  } catch {
    // Keep stock selection responsive; the stock configuration page exposes manual retry details.
  }
}

function timeframeLabel(timeframe: string): string {
  return {
    daily: "日线",
    "1m": "1分钟",
    "5m": "5分钟",
    "15m": "15分钟",
    "30m": "30分钟",
    "60m": "60分钟"
  }[timeframe] ?? timeframe;
}

async function runTask(
  setState: React.Dispatch<React.SetStateAction<PlatformState>>,
  label: string,
  task: (state: PlatformState) => Promise<Partial<PlatformState>>,
  options: { startPatch?: Partial<PlatformState>; finishPatch?: Partial<PlatformState> } = {}
) {
  const taskState = await new Promise<PlatformState | null>((resolve) => {
    setState((current) => {
      if (current.busy) {
        resolve(null);
        return current;
      }
      resolve(current);
      return { ...current, ...options.startPatch, busy: true, message: `${label}中...` };
    });
  });
  if (!taskState) return;
  try {
    const patch = await task(taskState);
    setState((current) => ({ ...current, ...patch, ...options.finishPatch, busy: false, message: `${label}完成` }));
  } catch (error) {
    setState((current) => ({ ...current, ...options.finishPatch, busy: false, message: formatError(error) }));
  }
}

function backtestModeLabel(mode: "single" | "portfolio") {
  return mode === "portfolio" ? "组合策略" : "单策略";
}

function formatError(error: unknown): string {
  return `请求失败：${formatRequestError(error)}`;
}
