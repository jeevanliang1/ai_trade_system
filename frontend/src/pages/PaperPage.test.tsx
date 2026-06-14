import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PaperPage } from "./PaperPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

function makeProps(overrides: Partial<PlatformState> = {}): PageProps {
  const state = {
    settings: {
      symbol: "000001",
      exchange: "SZSE",
      start_date: "20240101",
      end_date: "20241231",
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
    },
    strategies: [
      {
        id: "dual_ma",
        name: "Dual Moving Average",
        class_name: "DualMovingAverageStrategy",
        source: "builtin",
        path: null,
        editable: false,
        parameters: []
      }
    ],
    selectedStrategyId: "dual_ma",
    strategyParams: { symbol: "000001", fast: 5, slow: 20, size: 100 },
    bars: [],
    dataSummary: null,
    signals: null,
    portfolio: { allocations: [], mode: "weighted_vote", ai_adjust: false, ai_direction: null },
    backtest: null,
    insight: null,
    aiPrompt: null,
    riskStatus: null,
    paper: null,
    message: "准备就绪",
    busy: false,
    activeBacktestMode: null,
    activePaperMode: null,
    ...overrides
  } as PlatformState;
  const actions: PlatformActions = {
    setSettings: vi.fn(),
    setSelectedStrategyId: vi.fn(),
    setStrategyParams: vi.fn(),
    setPortfolio: vi.fn(),
    refreshStrategies: vi.fn(),
    loadData: vi.fn(),
    demoData: vi.fn(),
    downloadData: vi.fn(),
    previewSignals: vi.fn(),
    previewPortfolio: vi.fn(),
    runBacktest: vi.fn(),
    researchAI: vi.fn(),
    runPaper: vi.fn(),
    evaluateRisk: vi.fn()
  };
  return { state, actions };
}

test("PaperPage shows run configuration and idle status before starting", async () => {
  const user = userEvent.setup();
  const props = makeProps();

  render(<PaperPage {...props} />);

  expect(screen.getByText("运行配置")).toBeVisible();
  expect(screen.getByText(/标的 000001 SZSE/)).toBeVisible();
  expect(screen.getByText(/区间 20240101 - 20241231/)).toBeVisible();
  expect(screen.getByText(/策略\/组合 单策略：Dual Moving Average/)).toBeVisible();
  expect(screen.getByText(/初始资金 100000/)).toBeVisible();
  expect(screen.getByText(/手续费 0.0003/)).toBeVisible();
  expect(screen.getByText(/滑点 0.01/)).toBeVisible();
  expect(screen.getByText(/日志 logs\/paper_events.jsonl/)).toBeVisible();
  expect(screen.getByText("纸面交易状态")).toBeVisible();
  expect(screen.getByText("待运行")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "运行纸面交易" }));

  expect(props.actions.runPaper).toHaveBeenCalledWith("single");
});

test("PaperPage disables duplicate run clicks while a paper run is active", async () => {
  const user = userEvent.setup();
  const props = makeProps({ busy: true, activePaperMode: "single", message: "运行纸面交易中..." } as Partial<PlatformState>);

  render(<PaperPage {...props} />);

  expect(screen.getByText("运行中：单策略")).toBeVisible();
  const runButton = screen.getByRole("button", { name: "运行中..." });
  expect(runButton).toBeDisabled();

  await user.click(runButton);

  expect(props.actions.runPaper).not.toHaveBeenCalled();
});
