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
    display_name: "双均线趋势",
    description: "快慢均线金叉买入、死叉卖出，适合趋势行情。",
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
    display_name: "RSI自定义策略",
    description: "用户策略：按本地源码定义的 RSI 条件运行。",
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
    signals: {
      bars: [],
      signals: [
        { trading_day: "2024-02-05", action: "buy", symbol: "000001", price: 10.5, volume: 100, reason: "均线金叉" },
        { trading_day: "2024-02-08", action: "sell", symbol: "000001", price: 10.2, volume: 100, reason: "均线死叉" }
      ],
      summary: { signals: 2, buys: 1, sells: 1 }
    },
    researchSignals: null,
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
    previewResearchSignals: vi.fn(),
    runBacktest: vi.fn(),
    researchAI: vi.fn(),
    runPaper: vi.fn(),
    loadPaperEvents: vi.fn(),
    evaluateRisk: vi.fn(),
    ...actionOverrides
  };
  return { state, actions };
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("StrategyPage filters strategies and keeps only functional workshop controls", async () => {
  const user = userEvent.setup();
  render(<StrategyPage {...makeProps()} />);

  expect(screen.queryByRole("button", { name: "策略" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "组合" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "回测" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "周线" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "月线" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "日线" })).not.toBeInTheDocument();
  expect(screen.getByText("日线")).toBeInTheDocument();
  expect(document.querySelector(".favorite-icon")).not.toBeInTheDocument();
  expect(screen.getByText("双均线趋势")).toBeInTheDocument();
  expect(screen.getByText("DualMovingAverageStrategy")).toBeInTheDocument();
  expect(screen.getByText("快慢均线金叉买入、死叉卖出，适合趋势行情。")).toBeInTheDocument();

  await user.type(screen.getByLabelText("搜索策略名称或来源"), "rsi");
  expect(screen.queryByText("双均线趋势")).not.toBeInTheDocument();
  expect(screen.getByText("RSI自定义策略")).toBeInTheDocument();
  expect(screen.getByText("RsiStrategy")).toBeInTheDocument();

  expect(screen.getByLabelText("显示信号标记")).toBeChecked();
  expect(screen.getByText("MA20")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "重置视图" })).toBeInTheDocument();
  expect(screen.queryByText("回撤曲线")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "回测结果" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "交易明细" })).not.toBeInTheDocument();
  expect(screen.queryByText("策略表现对比")).not.toBeInTheDocument();
  expect(screen.queryByText("策略回测")).not.toBeInTheDocument();
  expect(screen.getByText("信号预览")).toBeInTheDocument();
  expect(screen.getByText("2024-02-05")).toBeInTheDocument();
  expect(screen.getByText("均线金叉")).toBeInTheDocument();
});

test("StrategyPage keeps full backtest result review out of the workshop", () => {
  render(<StrategyPage {...makeProps()} />);

  expect(screen.queryByRole("button", { name: "持仓分析" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "因子暴露" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "风险分析" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "绩效归因" })).not.toBeInTheDocument();
  expect(screen.queryByText("风控状态")).not.toBeInTheDocument();
  expect(screen.queryByText("策略收益")).not.toBeInTheDocument();
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
    display_name: "MyStrategy",
    description: "自定义策略：MyStrategy",
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

test("StrategyPage can request Chan RSI research preview", async () => {
  const user = userEvent.setup();
  const previewResearchSignals = vi.fn().mockResolvedValue(undefined);

  render(<StrategyPage {...makeProps({}, { previewResearchSignals })} />);

  await user.click(screen.getByRole("button", { name: "缠论/RSI研判" }));

  expect(previewResearchSignals).toHaveBeenCalled();
});

test("StrategyPage renders research blockers and populated signal rows", () => {
  render(
    <StrategyPage
      {...makeProps({
        researchSignals: {
          symbol: "000001",
          exchange: "SZSE",
          start: "2024-01-01",
          end: "2024-04-01",
          bars: 80,
          score: { total_score: 32, direction: "bullish", confidence: 0.58, chan_score: 32, rsi_score: 0, summary: "发现 1 个研究信号，综合方向为 bullish" },
          blockers: [],
          signals: [
            {
              trading_day: "2024-03-29",
              symbol: "000001",
              exchange: "SZSE",
              kind: "CHAN_BUY_T2",
              action: "buy",
              price: 12.4,
              strength: 0.62,
              score: 32,
              title: "缠论二买",
              reason: "回落低点抬高后向上修复",
              tags: ["chan", "second-buy"]
            }
          ]
        }
      })}
    />
  );

  expect(screen.getAllByText("缠论/RSI研判").length).toBeGreaterThan(0);
  expect(screen.getByText("CHAN_BUY_T2")).toBeInTheDocument();
  expect(screen.getByText("回落低点抬高后向上修复")).toBeInTheDocument();
});
