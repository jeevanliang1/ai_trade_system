import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { StrategyPage } from "./StrategyPage";
import type { PageProps, PlatformState } from "./pageTypes";
import type { PlatformActions } from "./pageTypes";

vi.mock("../api/client", () => ({
  api: {
    strategySource: vi.fn(),
    saveStrategySource: vi.fn(),
    createStrategyTemplate: vi.fn()
  }
}));

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
    id: "user:rsi:RsiStrategy",
    name: "RsiStrategy",
    class_name: "RsiStrategy",
    source: "user",
    path: "strategies/rsi.py",
    editable: true,
    parameters: [{ name: "symbol", annotation: "str", default: "000001" }]
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
    signals: { bars: [], signals: [], summary: { signals: 3, buys: 2, sells: 1 } },
    backtest: {
      bars: [],
      metrics: {
        final_equity: 108800,
        total_return_pct: 8.8,
        annualized_return_pct: 11.4,
        benchmark_return_pct: 5.2,
        excess_return_pct: 3.6,
        annual_volatility_pct: 18.5,
        sharpe_ratio: 0.62,
        max_drawdown_pct: -4.2,
        trade_count: 6,
        win_rate_pct: 66.67,
        profit_factor: 1.7,
        exposure_pct: 38
      },
      equity_curve: [],
      drawdowns: [{ trading_day: "2024-02-01", equity: 100000, drawdown_pct: -2.1 }],
      trades: [{ trading_day: "2024-02-05", side: "buy", symbol: "000001", price: 10.5, volume: 100, commission: 0.32 }],
      risk_status: { ok: true, warnings: [], enabled: true }
    },
    insight: null,
    riskStatus: { ok: true, warnings: [], enabled: true },
    paper: null,
    message: "准备就绪",
    busy: false,
    activeBacktestMode: null,
    activePaperMode: null,
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

beforeEach(() => {
  vi.clearAllMocks();
});

test("StrategyPage filters strategies and exposes screenshot workshop controls", async () => {
  const user = userEvent.setup();
  render(<StrategyPage {...makeProps()} />);

  expect(screen.getByRole("button", { name: "策略" })).toHaveClass("selected");
  await user.click(screen.getByRole("button", { name: "组合" }));
  expect(screen.getByRole("button", { name: "组合" })).toHaveClass("selected");

  await user.type(screen.getByLabelText("搜索策略名称或来源"), "rsi");
  expect(screen.queryByText("DualMovingAverageStrategy")).not.toBeInTheDocument();
  expect(screen.getByText("RsiStrategy")).toBeInTheDocument();

  expect(screen.getByLabelText("显示信号标记")).toBeChecked();
  expect(screen.getByText("MA20")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重置视图" })).toBeInTheDocument();
  expect(screen.getByText("回撤曲线")).toBeInTheDocument();
  expect(screen.getByText("策略表现对比")).toBeInTheDocument();
  expect(screen.getAllByText("策略回测").length).toBeGreaterThan(0);
  expect(screen.getAllByText("基准收益").length).toBeGreaterThan(0);
  expect(screen.getAllByText("超额收益").length).toBeGreaterThan(0);
  expect(screen.getByText("长持")).toBeInTheDocument();
});

test("StrategyPage switches dense result tabs for trades, risk, and attribution", async () => {
  const user = userEvent.setup();
  render(<StrategyPage {...makeProps()} />);

  expect(screen.getByRole("button", { name: "回测结果" })).toHaveClass("active");
  expect(screen.getByText("策略表现对比")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "交易明细" }));
  expect(screen.getByText("2024-02-05")).toBeInTheDocument();
  expect(screen.getByText("buy")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "风险分析" }));
  expect(screen.getByText("风控状态")).toBeInTheDocument();
  expect(screen.getByText("通过")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "绩效归因" }));
  expect(screen.getByText("策略收益")).toBeInTheDocument();
  expect(screen.getAllByText("基准收益").length).toBeGreaterThan(0);
});

test("StrategyPage loads editable source into a line-numbered safe editor", async () => {
  vi.mocked(api.strategySource).mockResolvedValue({
    path: "strategies/rsi.py",
    source: "class RsiStrategy:\n    pass\n"
  });

  render(<StrategyPage {...makeProps({ selectedStrategyId: strategies[1].id })} />);

  expect(await screen.findByLabelText("策略源码编辑器")).toHaveValue("class RsiStrategy:\n    pass\n");
  expect(screen.getByLabelText("源码行号")).toHaveTextContent("1");
  expect(screen.getByLabelText("源码行号")).toHaveTextContent("2");
});

test("StrategyPage auto-selects a newly created strategy template", async () => {
  const user = userEvent.setup();
  const refreshStrategies = vi.fn().mockResolvedValue(undefined);
  const newStrategy = {
    id: "user:my_strategy:MyStrategy",
    name: "MyStrategy",
    class_name: "MyStrategy",
    source: "user",
    path: "strategies/my_strategy.py",
    editable: true,
    parameters: [{ name: "symbol", annotation: "str", default: "000001" }]
  };
  vi.mocked(api.createStrategyTemplate).mockResolvedValue({
    path: "strategies/my_strategy.py",
    strategies: [...strategies, newStrategy]
  });

  render(<StrategyPage {...makeProps({}, { refreshStrategies })} />);

  await user.click(screen.getByText("新建策略"));
  await user.click(screen.getByRole("button", { name: "创建模板" }));

  expect(api.createStrategyTemplate).toHaveBeenCalledWith("my_strategy.py", "MyStrategy");
  expect(refreshStrategies).toHaveBeenCalledWith(newStrategy.id);
  expect(await screen.findByText("已创建并选中 MyStrategy")).toBeInTheDocument();
});

test("StrategyPage shows inline source save and template create errors", async () => {
  const user = userEvent.setup();
  vi.mocked(api.strategySource).mockResolvedValue({
    path: "strategies/rsi.py",
    source: "class RsiStrategy:\n    pass\n"
  });
  vi.mocked(api.saveStrategySource).mockRejectedValueOnce(new Error("path must stay under strategies"));
  vi.mocked(api.createStrategyTemplate).mockRejectedValueOnce(new Error("filename must end with .py"));

  render(<StrategyPage {...makeProps({ selectedStrategyId: strategies[1].id })} />);

  await screen.findByLabelText("策略源码编辑器");
  await user.click(screen.getByRole("button", { name: "保存源码" }));
  expect(await screen.findByText("保存源码失败：path must stay under strategies")).toBeInTheDocument();

  await user.click(screen.getByText("新建策略"));
  await user.clear(screen.getByLabelText("新策略文件名"));
  await user.type(screen.getByLabelText("新策略文件名"), "bad.txt");
  await user.click(screen.getByRole("button", { name: "创建模板" }));
  expect(await screen.findByText("创建策略失败：filename must end with .py")).toBeInTheDocument();
});

test("StrategyPage blocks preview when numeric strategy parameters are empty", async () => {
  const user = userEvent.setup();
  const previewSignals = vi.fn();

  render(<StrategyPage {...makeProps({}, { previewSignals })} />);

  const fastInput = screen.getByLabelText("fast");
  await user.clear(fastInput);
  await user.click(screen.getByRole("button", { name: "预览信号" }));

  expect(previewSignals).not.toHaveBeenCalled();
  expect(screen.getByText("fast 不能为空")).toBeInTheDocument();
});
