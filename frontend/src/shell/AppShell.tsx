import { useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  Bell,
  Bot,
  CalendarDays,
  Copy,
  Database,
  FileDown,
  FlaskConical,
  Gauge,
  Home,
  Layers3,
  NotebookTabs,
  Play,
  Plus,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  Square,
  UserRound
} from "lucide-react";

import { api, ApiError } from "../api/client";
import { InspectorPanel } from "../components/InspectorPanel";
import { ToolbarButton } from "../components/ToolbarButton";
import { AIPage } from "../pages/AIPage";
import { BacktestPage } from "../pages/BacktestPage";
import { DataPage } from "../pages/DataPage";
import { OverviewPage } from "../pages/OverviewPage";
import { PaperPage } from "../pages/PaperPage";
import { PortfolioPage } from "../pages/PortfolioPage";
import { RiskPage } from "../pages/RiskPage";
import { StrategyPage } from "../pages/StrategyPage";
import { currentSelection } from "../pages/pageTypes";
import type { PlatformActions, PlatformState } from "../pages/pageTypes";
import type { BootstrapResponse, PlatformSettings, PortfolioRequest, StrategySpec } from "../types";

export const NAV_ITEMS = [
  { id: "overview", label: "总览", icon: Home },
  { id: "data", label: "数据中心", icon: Database },
  { id: "strategies", label: "策略工坊", icon: SlidersHorizontal },
  { id: "portfolio", label: "组合实验室", icon: Layers3 },
  { id: "backtest", label: "回测中心", icon: BarChart3 },
  { id: "ai", label: "AI研究员", icon: Bot },
  { id: "paper", label: "纸面交易", icon: NotebookTabs },
  { id: "risk", label: "风控", icon: ShieldCheck }
] as const;

type PageId = (typeof NAV_ITEMS)[number]["id"];

const DEFAULT_SETTINGS: PlatformSettings = {
  symbol: "000001",
  exchange: "SZSE",
  start_date: "20220101",
  end_date: "20250516",
  adjust: "qfq",
  csv_path: "data/000001_daily.csv",
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
    id: "builtin:dual_moving_average:DualMovingAverageStrategy",
    name: "DualMovingAverageStrategy",
    class_name: "DualMovingAverageStrategy",
    source: "builtin",
    path: null,
    editable: false,
    parameters: [
      { name: "symbol", annotation: "str", default: "000001" },
      { name: "fast", annotation: "int", default: 5 },
      { name: "slow", annotation: "int", default: 20 },
      { name: "size", annotation: "int", default: 100 }
    ]
  }
];

function initialState(): PlatformState {
  return {
    settings: DEFAULT_SETTINGS,
    strategies: FALLBACK_STRATEGIES,
    selectedStrategyId: FALLBACK_STRATEGIES[0].id,
    strategyParams: { symbol: "000001", fast: 5, slow: 20, size: 100 },
    bars: [],
    dataSummary: null,
    signals: null,
    portfolio: defaultPortfolio(FALLBACK_STRATEGIES[0].id),
    backtest: null,
    insight: null,
    aiPrompt: null,
    riskStatus: { ok: true, warnings: [], enabled: true },
    paper: null,
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
        try {
          const data = await api.loadData(bootstrap.settings);
          if (!mounted) return;
          setState((current) => ({ ...current, bars: data.bars, dataSummary: data.summary, message: `已加载 ${data.bars.length} 根K线` }));
        } catch {
          const demo = await api.demoData(bootstrap.settings, 260);
          if (!mounted) return;
          setState((current) => ({ ...current, bars: demo.bars, dataSummary: demo.summary, message: `已生成 ${demo.bars.length} 根演示K线` }));
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
          if (!dataRequestChanged(current.settings, settings)) {
            return { ...current, settings };
          }
          return {
            ...current,
            settings,
            bars: [],
            dataSummary: null,
            signals: null,
            backtest: null,
            paper: null,
            message: `已切换数据目标：${settings.symbol} ${settings.exchange}，请加载或下载行情`
          };
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
        runTask(setState, "下载日线数据", async (current) => {
          const data = await api.downloadData(current.settings);
          return { bars: data.bars, dataSummary: data.summary };
        }),
      previewSignals: () =>
        runTask(setState, "预览信号", async (current) => ({ signals: await api.previewSignals(current.settings, currentSelection(current)) })),
      previewPortfolio: () =>
        runTask(setState, "预览组合", async (current) => ({ signals: await api.previewPortfolio(current.settings, current.portfolio) })),
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
        }))
    }),
    [state.strategies]
  );

  const pageProps = { state, actions };
  const page = {
    overview: <OverviewPage {...pageProps} />,
    data: <DataPage {...pageProps} />,
    strategies: <StrategyPage {...pageProps} />,
    portfolio: <PortfolioPage {...pageProps} />,
    backtest: <BacktestPage {...pageProps} />,
    ai: <AIPage {...pageProps} />,
    paper: <PaperPage {...pageProps} />,
    risk: <RiskPage {...pageProps} />
  }[activePage];

  return (
    <div className="app-shell">
      <SideNav activePage={activePage} setActivePage={setActivePage} />
      <div className="app-main">
        <TopCommandBar state={state} actions={actions} />
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
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.id} className={activePage === item.id ? "active" : ""} onClick={() => setActivePage(item.id)}>
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>
      <button className="collapse-button">收起</button>
    </aside>
  );
}

function TopCommandBar({ state, actions }: { state: PlatformState; actions: PlatformActions }) {
  return (
    <header className="topbar">
      <div className="market-status">
        <strong>沪深A股</strong>
        <span className="dot" />
        <span>已连接</span>
        <span>数据日期：{state.bars.at(-1)?.trading_day ?? state.settings.end_date}</span>
      </div>
      <div className="toolbar">
        <ToolbarButton icon={<Plus size={15} />} variant="primary">
          新建策略
        </ToolbarButton>
        <ToolbarButton icon={<Save size={15} />}>保存</ToolbarButton>
        <ToolbarButton icon={<Copy size={15} />}>另存为</ToolbarButton>
        <ToolbarButton disabled={state.busy} icon={<Play size={15} />} variant="success" onClick={() => actions.runBacktest("single")}>
          {state.activeBacktestMode ? "运行中..." : "运行回测"}
        </ToolbarButton>
        <ToolbarButton icon={<Square size={15} />}>停止</ToolbarButton>
        <ToolbarButton icon={<SlidersHorizontal size={15} />}>回测设置</ToolbarButton>
        <ToolbarButton icon={<FileDown size={15} />}>导出报告</ToolbarButton>
      </div>
      <div className="top-actions">
        <Bell size={17} />
        <CalendarDays size={17} />
        <FlaskConical size={17} />
        <UserRound size={18} />
        <span>研究员</span>
      </div>
    </header>
  );
}

function StatusBar({ state }: { state: PlatformState }) {
  const selectedStrategy = state.strategies.find((item) => item.id === state.selectedStrategyId)?.name ?? "-";
  const health = state.riskStatus?.ok === false ? "告警" : "正常";
  return (
    <footer className="statusbar">
      <span>数据：本地CSV</span>
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
    strategies,
    selectedStrategyId,
    strategyParams: paramsFromStrategy(strategies[0], bootstrap.settings.symbol),
    portfolio: defaultPortfolio(selectedStrategyId),
    message: `已连接 MockProvider，发现 ${strategies.length} 个策略`
  };
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
    allocations: [{ strategy: { id: strategyId, params: { symbol: "000001", fast: 5, slow: 20, size: 100 } }, weight: 1, enabled: true }]
  };
}

function dataRequestChanged(previous: PlatformSettings, next: PlatformSettings): boolean {
  return (
    previous.symbol !== next.symbol ||
    previous.exchange !== next.exchange ||
    previous.start_date !== next.start_date ||
    previous.end_date !== next.end_date ||
    previous.adjust !== next.adjust ||
    previous.csv_path !== next.csv_path
  );
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
  if (error instanceof ApiError) return `请求失败：${error.message}`;
  if (error instanceof Error) return `请求失败：${error.message}`;
  return "请求失败";
}
