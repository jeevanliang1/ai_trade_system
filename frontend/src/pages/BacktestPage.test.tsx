import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BacktestPage, BacktestResultPanel } from "./BacktestPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";
import type { BacktestResponse } from "../types";

function readBlobText(blob: Blob) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => resolve(String(reader.result)));
    reader.addEventListener("error", () => reject(reader.error));
    reader.readAsText(blob);
  });
}

function makeProps(overrides: Partial<PlatformState> = {}, actionOverrides: Partial<PlatformActions> = {}): PageProps {
  const strategies = [
    {
      id: "builtin:dual:DualMovingAverageStrategy",
      name: "DualMovingAverageStrategy",
      class_name: "DualMovingAverageStrategy",
      source: "builtin",
      path: null,
      editable: false,
      parameters: [{ name: "symbol", annotation: "str", default: "000001" }]
    }
  ];
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
    strategyParams: {},
    bars: [],
    dataSummary: null,
    signals: null,
    portfolio: {
      mode: "weighted_vote",
      ai_adjust: false,
      ai_direction: null,
      allocations: []
    },
    backtest: null,
    insight: null,
    riskStatus: { ok: true, warnings: [], enabled: true },
    paper: null,
    message: "运行组合策略回测中...",
    busy: true,
    activeBacktestMode: "portfolio",
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

function loadedDataState(): Pick<PlatformState, "bars" | "dataSummary"> {
  return {
    bars: [
      {
        symbol: "000001",
        exchange: "SZSE",
        trading_day: "2024-01-02",
        open_price: 10,
        high_price: 10.5,
        low_price: 9.8,
        close_price: 10.2,
        volume: 1000,
        turnover: 10200
      }
    ],
    dataSummary: {
      rows: 1,
      csv_path: "data/000001_daily.csv",
      symbol: "000001",
      exchange: "SZSE",
      start: "2024-01-02",
      end: "2024-01-02",
      latest_close: 10.2,
      latest_volume: 1000,
      latest_turnover: 10200
    }
  };
}

test("BacktestPage disables run controls and shows the active busy mode", () => {
  render(<BacktestPage {...makeProps()} />);

  expect(screen.getByLabelText("回测运行状态")).toHaveTextContent("组合策略回测运行中");
  expect(screen.getByRole("button", { name: "运行中..." })).toBeDisabled();
  expect(screen.getByRole("button", { name: "单策略" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "组合策略" })).toBeDisabled();
});

test("BacktestPage shows run configuration summary beside results and updates mode", async () => {
  const user = userEvent.setup();
  render(<BacktestPage {...makeProps({ busy: false, activeBacktestMode: null, message: "准备就绪" })} />);

  const summary = screen.getByLabelText("回测运行配置");
  expect(summary).toBeInTheDocument();
  expect(within(summary).getByText("000001 SZSE")).toBeInTheDocument();
  expect(within(summary).getByText("20240101 - 20241231")).toBeInTheDocument();
  expect(within(summary).getByText("单策略")).toBeInTheDocument();
  expect(within(summary).getByText("DualMovingAverageStrategy")).toBeInTheDocument();
  expect(within(summary).getByText("100,000")).toBeInTheDocument();
  expect(within(summary).getByText("0.03%")).toBeInTheDocument();
  expect(within(summary).getByText("0.01")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "组合策略" }));

  expect(within(summary).getByText("组合策略")).toBeInTheDocument();
  expect(within(summary).getByText("加权投票")).toBeInTheDocument();
});

test("BacktestPage explains missing CSV data before running", () => {
  const actions = { runBacktest: vi.fn() };
  render(<BacktestPage {...makeProps({ busy: false, activeBacktestMode: null, message: "准备就绪" }, actions)} />);

  const readiness = screen.getByLabelText("回测准备状态");
  expect(within(readiness).getByText("缺少行情CSV")).toBeInTheDocument();
  expect(within(readiness).getByText(/请先在数据中心加载、下载或生成演示行情/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "运行回测" })).toBeDisabled();
  expect(screen.getByLabelText("回测结果状态")).toHaveTextContent("无法运行回测");
});

test("BacktestPage explains missing strategy before single-strategy backtest", () => {
  render(
    <BacktestPage
      {...makeProps({
        ...loadedDataState(),
        busy: false,
        activeBacktestMode: null,
        selectedStrategyId: "",
        strategies: []
      })}
    />
  );

  const readiness = screen.getByLabelText("回测准备状态");
  expect(within(readiness).getByText("缺少回测策略")).toBeInTheDocument();
  expect(within(readiness).getByText(/请先在策略工坊创建或选择一个策略/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "运行回测" })).toBeDisabled();
});

test("BacktestPage explains invalid portfolio allocation before portfolio backtest", async () => {
  const user = userEvent.setup();
  render(
    <BacktestPage
      {...makeProps({
        ...loadedDataState(),
        busy: false,
        activeBacktestMode: null,
        portfolio: { mode: "weighted_vote", ai_adjust: false, ai_direction: null, allocations: [] }
      })}
    />
  );

  await user.click(screen.getByRole("button", { name: "组合策略" }));

  const readiness = screen.getByLabelText("回测准备状态");
  expect(within(readiness).getByText("组合分配无效")).toBeInTheDocument();
  expect(within(readiness).getByText(/至少启用一个权重大于 0 的策略分配/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "运行回测" })).toBeDisabled();
});

test("BacktestResultPanel renders metrics, chart title, and trade table", () => {
  const result: BacktestResponse = {
    bars: [],
    metrics: {
      final_equity: 112000,
      total_return_pct: 12,
      annualized_return_pct: 18,
      benchmark_return_pct: 7.5,
      excess_return_pct: 4.5,
      annual_volatility_pct: 16.2,
      sharpe_ratio: 1.11,
      max_drawdown_pct: -6,
      trade_count: 2,
      win_rate_pct: 50,
      profit_factor: 1.8,
      exposure_pct: 40
    },
    equity_curve: [{ trading_day: "2024-01-02", equity: 100000, cash: 80000, close_price: 10 }],
    drawdowns: [{ trading_day: "2024-01-02", equity: 100000, drawdown_pct: 0 }],
    trades: [{ trading_day: "2024-01-02", side: "buy", symbol: "000001", price: 10, volume: 100, commission: 0.3 }],
    risk_status: { ok: true, warnings: [], enabled: true }
  };

  render(<BacktestResultPanel result={result} />);

  expect(screen.getByText("112,000.00")).toBeInTheDocument();
  expect(screen.getByText("资金曲线")).toBeInTheDocument();
  expect(screen.getByText("交易明细")).toBeInTheDocument();
});

test("BacktestResultPanel disables exports until a result exists", () => {
  render(<BacktestResultPanel result={null} />);

  expect(screen.getByRole("button", { name: "导出交易" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "导出指标" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "导出资金曲线" })).toBeDisabled();
});

test("BacktestResultPanel exports trades metrics and equity curve", async () => {
  const user = userEvent.setup();
  const result: BacktestResponse = {
    bars: [],
    metrics: {
      final_equity: 112000,
      total_return_pct: 12,
      annualized_return_pct: 18,
      benchmark_return_pct: 7.5,
      excess_return_pct: 4.5,
      annual_volatility_pct: 16.2,
      sharpe_ratio: 1.11,
      max_drawdown_pct: -6,
      trade_count: 2,
      win_rate_pct: 50,
      profit_factor: 1.8,
      exposure_pct: 40
    },
    equity_curve: [{ trading_day: "2024-01-02", equity: 100000, cash: 80000, close_price: 10 }],
    drawdowns: [],
    trades: [{ trading_day: "2024-01-02", side: "buy", symbol: "000001", price: 10, volume: 100, commission: 0.3 }],
    risk_status: { ok: true, warnings: [], enabled: true }
  };
  const createObjectURL = vi.fn(() => "blob:backtest-export");
  const revokeObjectURL = vi.fn();
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });

  render(<BacktestResultPanel result={result} />);

  await user.click(screen.getByRole("button", { name: "导出交易" }));
  await user.click(screen.getByRole("button", { name: "导出指标" }));
  await user.click(screen.getByRole("button", { name: "导出资金曲线" }));

  expect(click).toHaveBeenCalledTimes(3);
  expect(createObjectURL).toHaveBeenCalledTimes(3);
  expect(revokeObjectURL).toHaveBeenCalledTimes(3);

  await expect(readBlobText(createObjectURL.mock.calls[0][0] as Blob)).resolves.toContain(
    "trading_day,side,symbol,price,volume,commission"
  );
  await expect(readBlobText(createObjectURL.mock.calls[1][0] as Blob)).resolves.toContain('"final_equity": 112000');
  await expect(readBlobText(createObjectURL.mock.calls[2][0] as Blob)).resolves.toContain("trading_day,equity,cash,close_price");

  click.mockRestore();
});
