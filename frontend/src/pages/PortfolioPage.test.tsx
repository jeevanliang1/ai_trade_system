import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { PortfolioPage } from "./PortfolioPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

const strategies = [
  {
    id: "builtin:dual:DualMovingAverageStrategy",
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
  },
  {
    id: "builtin:rsi:RsiMeanReversionStrategy",
    name: "RsiMeanReversionStrategy",
    class_name: "RsiMeanReversionStrategy",
    source: "builtin",
    path: null,
    editable: false,
    parameters: [
      { name: "symbol", annotation: "str", default: "000001" },
      { name: "rsi_period", annotation: "int", default: 14 },
      { name: "trade_size", annotation: "int", default: 100 }
    ]
  },
  {
    id: "user:my_strategy:MyStrategy",
    name: "MyStrategy",
    class_name: "MyStrategy",
    source: "user",
    path: "strategies/my_strategy.py",
    editable: true,
    parameters: [
      { name: "symbol", annotation: "str", default: "000001" },
      { name: "trade_size", annotation: "int", default: 100 }
    ]
  }
];

function makeProps(overrides: Partial<PlatformState> = {}, actionOverrides: Partial<PlatformActions> = {}): PageProps {
  const state: PlatformState = {
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
    strategies,
    selectedStrategyId: strategies[0].id,
    strategyParams: { symbol: "000001", fast: 5, slow: 20, size: 100 },
    bars: [],
    dataSummary: null,
    signals: null,
    portfolio: {
      mode: "weighted_vote",
      ai_adjust: false,
      ai_direction: null,
      allocations: [
        { strategy: { id: strategies[0].id, params: { symbol: "000001", fast: 5, slow: 20, size: 100 } }, weight: 2, enabled: true },
        { strategy: { id: strategies[1].id, params: { symbol: "000001", rsi_period: 14, trade_size: 100 } }, weight: 1, enabled: true }
      ]
    },
    backtest: null,
    insight: null,
    riskStatus: { ok: true, warnings: [], enabled: true },
    paper: null,
    message: "准备就绪",
    busy: false,
    activeBacktestMode: null,
    ...overrides
  };
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
    evaluateRisk: vi.fn(),
    ...actionOverrides
  };
  return { state, actions };
}

test("PortfolioPage edits allocation rows and shows normalized enabled weights", async () => {
  const user = userEvent.setup();
  const props = makeProps();

  render(<PortfolioPage {...props} />);

  expect(screen.getByText("归一化权重")).toBeInTheDocument();
  expect(screen.getByText("DualMovingAverageStrategy 66.67%")).toBeInTheDocument();
  expect(screen.getByText("RsiMeanReversionStrategy 33.33%")).toBeInTheDocument();
  expect(screen.getByText("启用权重合计 3.00")).toBeInTheDocument();

  const changedFirstAllocation = {
    strategy: { id: strategies[2].id, params: { symbol: "000001", trade_size: 100 } },
    weight: 2,
    enabled: true
  };
  const weightedSecondAllocation = { ...props.state.portfolio.allocations[1], weight: 4 };
  const disabledSecondAllocation = { ...weightedSecondAllocation, enabled: false };

  await user.selectOptions(screen.getByLabelText("第1行策略"), strategies[2].id);
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({
    ...props.state.portfolio,
    allocations: [changedFirstAllocation, props.state.portfolio.allocations[1]]
  });

  await user.clear(screen.getByLabelText("第2行权重"));
  await user.type(screen.getByLabelText("第2行权重"), "4");
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({
    ...props.state.portfolio,
    allocations: [changedFirstAllocation, weightedSecondAllocation]
  });

  await user.click(screen.getByLabelText("第2行启用"));
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({
    ...props.state.portfolio,
    allocations: [changedFirstAllocation, disabledSecondAllocation]
  });

  await user.click(screen.getByRole("button", { name: "删除第2行" }));
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({
    ...props.state.portfolio,
    allocations: [changedFirstAllocation]
  });

  await user.click(screen.getByRole("button", { name: "新增分配" }));
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({
    ...props.state.portfolio,
    allocations: [
      changedFirstAllocation,
      { strategy: { id: strategies[0].id, params: { symbol: "000001", fast: 5, slow: 20, size: 100 } }, weight: 1, enabled: true }
    ]
  });
});

test("PortfolioPage renders duplicate strategy allocations without duplicate-key summary artifacts", () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
  const duplicateAllocation = { strategy: { id: strategies[0].id, params: { symbol: "000001", fast: 5, slow: 20, size: 100 } }, weight: 1, enabled: true };

  render(
    <PortfolioPage
      {...makeProps({
        portfolio: {
          mode: "weighted_vote",
          ai_adjust: false,
          ai_direction: null,
          allocations: [duplicateAllocation, duplicateAllocation]
        }
      })}
    />
  );

  expect(screen.getAllByText("DualMovingAverageStrategy 50.00%")).toHaveLength(2);
  const consoleMessages = consoleError.mock.calls.map((call) => call.join(" "));
  expect(consoleMessages.some((message) => message.includes("Encountered two children with the same key"))).toBe(false);

  consoleError.mockRestore();
});

test("PortfolioPage explains portfolio aggregation modes and updates the active mode copy", async () => {
  const user = userEvent.setup();
  const props = makeProps();

  render(<PortfolioPage {...props} />);

  expect(screen.getByText("模式说明")).toBeInTheDocument();
  expect(screen.getByText("当前模式：加权投票")).toBeInTheDocument();
  expect(screen.getAllByText("按每行权重累计买入/卖出得分，权重越高的策略影响越大。").length).toBeGreaterThan(0);
  expect(screen.getByText("每个启用策略一票，忽略原始权重，只比较买卖信号数量。")).toBeInTheDocument();
  expect(screen.getByText("按分配行顺序采用第一个有效信号，适合主备策略或优先级执行。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "等权投票" }));
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({ ...props.state.portfolio, mode: "equal_vote" });
  expect(screen.getByText("当前模式：等权投票")).toBeInTheDocument();
  expect(screen.getByText("权重仅影响归一化展示，不参与投票得分。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "优先级" }));
  expect(props.actions.setPortfolio).toHaveBeenLastCalledWith({ ...props.state.portfolio, mode: "first_active" });
  expect(screen.getByText("当前模式：优先级")).toBeInTheDocument();
  expect(screen.getByText("第一条有效信号会直接成为组合信号，后续策略不会继续竞争。")).toBeInTheDocument();
});

test("PortfolioPage shows portfolio signal breakdown after preview", () => {
  const props = makeProps({
    signals: {
      bars: [],
      signals: [
        {
          trading_day: "2024-09-17",
          action: "buy",
          symbol: "000001",
          price: 12.34,
          volume: 120,
          reason: "portfolio_weighted_vote"
        }
      ],
      summary: { signals: 1, buys: 1, sells: 0 },
      breakdown: {
        buy_score: 2,
        sell_score: 1,
        active_signals: 2,
        mode: "weighted_vote",
        reasons: ["DualMovingAverageStrategy:均线金叉", "RsiMeanReversionStrategy:RSI超买"],
        contributions: [
          {
            allocation_index: 0,
            name: "DualMovingAverageStrategy",
            action: "buy",
            score: 2,
            weight: 2,
            volume: 100,
            reason: "均线金叉",
            selected: true
          },
          {
            allocation_index: 1,
            name: "RsiMeanReversionStrategy",
            action: "sell",
            score: 1,
            weight: 1,
            volume: 80,
            reason: "RSI超买",
            selected: false
          }
        ]
      },
      allocations: [
        { index: 0, name: "DualMovingAverageStrategy", weight: 2, enabled: true },
        { index: 1, name: "RsiMeanReversionStrategy", weight: 1, enabled: true }
      ]
    }
  });

  render(<PortfolioPage {...props} />);

  const breakdown = within(screen.getByLabelText("组合信号拆解"));
  expect(breakdown.getByText("信号拆解")).toBeInTheDocument();
  expect(breakdown.getByText("买入得分 2.00")).toBeInTheDocument();
  expect(breakdown.getByText("卖出得分 1.00")).toBeInTheDocument();
  expect(breakdown.getByText("参与信号 2")).toBeInTheDocument();
  expect(breakdown.getByText("DualMovingAverageStrategy")).toBeInTheDocument();
  expect(breakdown.getByText("买入")).toBeInTheDocument();
  expect(breakdown.getByText("贡献 2.00")).toBeInTheDocument();
  expect(breakdown.getByText("采用")).toBeInTheDocument();
  expect(breakdown.getByText("均线金叉")).toBeInTheDocument();
  expect(breakdown.getByText("RsiMeanReversionStrategy")).toBeInTheDocument();
  expect(breakdown.getByText("卖出")).toBeInTheDocument();
  expect(breakdown.getByText("未采用")).toBeInTheDocument();
  expect(breakdown.getByText("RSI超买")).toBeInTheDocument();
});

test("PortfolioPage shows AI-adjust before and after weights after preview", () => {
  const props = makeProps({
    portfolio: {
      mode: "weighted_vote",
      ai_adjust: true,
      ai_direction: "bullish",
      allocations: [
        { strategy: { id: strategies[0].id, params: { symbol: "000001", fast: 5, slow: 20, size: 100 } }, weight: 2, enabled: true },
        { strategy: { id: strategies[1].id, params: { symbol: "000001", rsi_period: 14, trade_size: 100 } }, weight: 1, enabled: true }
      ]
    },
    signals: {
      bars: [],
      signals: [],
      summary: { signals: 0, buys: 0, sells: 0 },
      ai_adjustment: {
        enabled: true,
        direction: "bullish",
        applied: true,
        delta: 0.05
      },
      allocations: [
        {
          index: 0,
          name: "DualMovingAverageStrategy",
          weight: 2.05,
          base_weight: 2,
          adjusted_weight: 2.05,
          ai_delta: 0.05,
          ai_adjusted: true,
          enabled: true
        },
        {
          index: 1,
          name: "RsiMeanReversionStrategy",
          weight: 1.05,
          base_weight: 1,
          adjusted_weight: 1.05,
          ai_delta: 0.05,
          ai_adjusted: true,
          enabled: true
        }
      ]
    }
  });

  render(<PortfolioPage {...props} />);

  const aiPreview = within(screen.getByLabelText("AI权重调整预览"));
  expect(aiPreview.getByText("AI权重预览")).toBeInTheDocument();
  expect(aiPreview.getByText("方向：看多")).toBeInTheDocument();
  expect(aiPreview.getByText("DualMovingAverageStrategy")).toBeInTheDocument();
  expect(aiPreview.getByText("2.00 -> 2.05")).toBeInTheDocument();
  expect(aiPreview.getAllByText("+0.05")).toHaveLength(2);
  expect(aiPreview.getByText("RsiMeanReversionStrategy")).toBeInTheDocument();
  expect(aiPreview.getByText("1.00 -> 1.05")).toBeInTheDocument();
});
