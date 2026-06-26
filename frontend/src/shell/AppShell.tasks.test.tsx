import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AppShell } from "./AppShell";

const apiMock = vi.hoisted(() => {
  class MockApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
      super(message);
      this.name = "ApiError";
      this.status = status;
    }
  }

  return {
    ApiError: MockApiError,
    api: {
      bootstrap: vi.fn(),
      stocks: vi.fn(),
      watchlist: vi.fn(),
      saveWatchlist: vi.fn(),
      managedData: vi.fn(),
      updateWatchlistData: vi.fn(),
      loadData: vi.fn(),
      demoData: vi.fn(),
      downloadData: vi.fn(),
      agentTools: vi.fn(),
      agentTasks: vi.fn(),
      createAgentTask: vi.fn(),
      approveAgentTask: vi.fn(),
      strategies: vi.fn(),
      previewSignals: vi.fn(),
      previewPortfolio: vi.fn(),
      previewResearchSignals: vi.fn(),
      runBacktest: vi.fn(),
      research: vi.fn(),
      runPaper: vi.fn(),
      paperEvents: vi.fn(),
      evaluateRisk: vi.fn()
    }
  };
});

vi.mock("../api/client", () => apiMock);

const settings = {
  symbol: "000001",
  exchange: "SZSE",
  start_date: "20240101",
  end_date: "20241231",
  adjust: "qfq",
  timeframe: "daily",
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

const strategy = {
  id: "builtin:dual:DualMovingAverageStrategy",
  name: "DualMovingAverageStrategy",
  display_name: "双均线趋势",
  description: "快慢均线金叉买入、死叉卖出，适合趋势行情。",
  class_name: "DualMovingAverageStrategy",
  source: "builtin",
  path: null,
  editable: false,
  parameters: [{ name: "symbol", annotation: "str", default: "000001" }]
};

beforeEach(() => {
  vi.clearAllMocks();
});

function loadedDataResponse() {
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
    summary: {
      rows: 1,
      csv_path: settings.csv_path,
      timeframe: "daily",
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

function backtestResponse() {
  return {
    bars: [],
    metrics: {
      final_equity: 100000,
      total_return_pct: 0,
      annualized_return_pct: 0,
      benchmark_return_pct: 0,
      excess_return_pct: 0,
      annual_volatility_pct: 0,
      sharpe_ratio: null,
      max_drawdown_pct: 0,
      trade_count: 0,
      win_rate_pct: null,
      profit_factor: null,
      exposure_pct: 0
    },
    equity_curve: [],
    drawdowns: [],
    trades: [],
    risk_status: { ok: true, warnings: [], enabled: true }
  };
}

function paperResponse() {
  return {
    events: [
      { event: "service_started" },
      { event: "order_accepted", trading_day: "2024-01-05", side: "buy", symbol: "000001", price: 10.5, volume: 100 },
      { event: "service_stopped", final_equity: 100800 }
    ],
    orders: [{ event: "order_accepted", trading_day: "2024-01-05", side: "buy", symbol: "000001", price: 10.5, volume: 100 }],
    equity: [{ trading_day: "2024-01-05", equity: 100800, cash: 99750 }],
    summary: { event: "service_stopped", final_equity: 100800 }
  };
}

function researchSignalResponse() {
  return {
    symbol: "000001",
    exchange: "SZSE",
    start: "2024-01-02",
    end: "2024-01-02",
    bars: 1,
    score: { total_score: 32, direction: "bullish", confidence: 0.58, chan_score: 32, rsi_score: 0, summary: "发现 1 个研究信号，综合方向为 bullish" },
    blockers: [],
    signals: [
      {
        trading_day: "2024-01-02",
        symbol: "000001",
        exchange: "SZSE",
        kind: "CHAN_BUY_T2",
        action: "buy",
        price: 10.2,
        strength: 0.62,
        score: 32,
        title: "缠论二买",
        reason: "回落低点抬高后向上修复",
        tags: ["chan", "second-buy"]
      }
    ]
  };
}

test("AppShell clears busy state and shows backend detail when a data task rejects", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [],
    limits: {}
  });
  apiMock.api.loadData
    .mockResolvedValueOnce({ bars: [], summary: { rows: 0, csv_path: settings.csv_path } })
    .mockRejectedValueOnce(new apiMock.ApiError(400, "CSV data not found: data/missing.csv"));

  render(<AppShell />);

  await screen.findByText("已加载 0 根K线");

  await user.click(screen.getByRole("button", { name: "数据中心" }));
  await user.click(screen.getByRole("button", { name: "加载CSV" }));

  await waitFor(() => expect(screen.getAllByText("请求失败：CSV data not found: data/missing.csv").length).toBeGreaterThan(0));
  expect(screen.queryByText("加载CSV中...")).not.toBeInTheDocument();
});

test("AppShell explains fetch failures as local API connection issues", async () => {
  apiMock.api.bootstrap.mockRejectedValueOnce(new TypeError("Failed to fetch"));

  render(<AppShell />);

  await waitFor(() =>
    expect(screen.getAllByText("请求失败：本地 API 未连接，请确认 ./scripts/run_app.sh 正在运行。").length).toBeGreaterThan(0)
  );
});

test("AppShell clears stale bars and summaries when Data Center selects a different stock target", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce({
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
    summary: {
      rows: 1,
      csv_path: settings.csv_path,
      timeframe: "daily",
      symbol: "000001",
      exchange: "SZSE",
      start: "2024-01-02",
      end: "2024-01-02",
      latest_close: 10.2,
      latest_volume: 1000,
      latest_turnover: 10200
    }
  });
  apiMock.api.stocks.mockResolvedValue([{ code: "601318", name: "中国平安", exchange: "SSE" }]);

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "数据中心" }));
  expect(screen.getByText("1 行")).toBeInTheDocument();

  await user.type(screen.getByLabelText("搜索股票名称或代码"), "平安");
  await user.click(await screen.findByRole("button", { name: "601318 中国平安 SSE" }));

  await waitFor(() => expect(screen.getByDisplayValue("data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv")).toBeInTheDocument());
  expect(screen.getByText("0 行")).toBeInTheDocument();
  expect(screen.getByText("暂无数据")).toBeInTheDocument();
  expect(screen.queryByText("000001")).not.toBeInTheDocument();
});

test("AppShell disables duplicate backtest runs and shows the active mode while pending", async () => {
  const user = userEvent.setup();
  let resolveBacktest: (value: ReturnType<typeof backtestResponse>) => void = () => undefined;
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.runBacktest.mockImplementation(
    () =>
      new Promise((resolve) => {
        resolveBacktest = resolve;
      })
  );

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "回测中心" }));
  const backtestSettings = screen.getAllByText("回测设置").at(-1)!.closest("section")!;
  await user.click(within(backtestSettings).getByRole("button", { name: "运行回测" }));

  await waitFor(() => expect(screen.getByLabelText("回测运行状态")).toHaveTextContent("单策略回测运行中"));
  expect(within(backtestSettings).getByRole("button", { name: "运行中..." })).toBeDisabled();

  await user.click(within(backtestSettings).getByRole("button", { name: "运行中..." }));

  expect(apiMock.api.runBacktest).toHaveBeenCalledTimes(1);

  resolveBacktest(backtestResponse());

  await waitFor(() => expect(within(backtestSettings).getByRole("button", { name: "运行回测" })).toBeEnabled());
  expect(screen.getByLabelText("回测运行状态")).toHaveTextContent("等待运行");
});

test("AppShell top next-step button navigates without running a backtest", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  expect(screen.getByText("策略工坊")).toHaveClass("active");

  await user.click(screen.getByRole("button", { name: "去回测中心" }));

  expect(screen.getByText("回测中心")).toHaveClass("active");
  expect(screen.getByText("回测设置")).toBeInTheDocument();
  expect(apiMock.api.runBacktest).not.toHaveBeenCalled();
});

test("AppShell exposes a global watchlist selector that changes the current stock target", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    watchlist: [
      { code: "000001", name: "平安银行", exchange: "SZSE" },
      { code: "601318", name: "中国平安", exchange: "SSE" }
    ],
    catalog_available: true,
    catalog_size: 2,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.stocks.mockResolvedValueOnce([{ code: "601318", name: "中国平安", exchange: "SSE" }]);
  apiMock.api.updateWatchlistData.mockResolvedValueOnce({ updated: 1, skipped: 0, failed: 0, files: [] });
  apiMock.api.managedData.mockResolvedValueOnce({ files: [] });

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "全局自选股票 000001 平安银行 SZSE" }));
  await user.click(screen.getByRole("button", { name: "选择 601318 中国平安 SSE" }));

  await waitFor(() => expect(screen.getByText("路径：data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv")).toBeInTheDocument());
  expect(screen.getByText("601318 SSE")).toBeInTheDocument();
  expect(screen.getByText("已切换数据目标：601318 SSE，请加载或下载行情")).toBeInTheDocument();
  expect(apiMock.api.updateWatchlistData).toHaveBeenCalledWith(
    expect.objectContaining({ start_date: "20191231", end_date: "20241231", if_stale: true })
  );
});

test("AppShell does not bootstrap into the removed 000001 default when no stock is selected", async () => {
  apiMock.api.bootstrap.mockResolvedValue({
    settings: { ...settings, symbol: "", exchange: "", csv_path: "" },
    watchlist: [],
    catalog_available: true,
    catalog_size: 2,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });

  render(<AppShell />);

  await screen.findByText("请选择股票");
  expect(apiMock.api.loadData).not.toHaveBeenCalled();
  expect(apiMock.api.demoData).not.toHaveBeenCalled();
  expect(screen.queryByText("000001 SZSE")).not.toBeInTheDocument();
});

test("AppShell shows backtest API errors and clears the active run mode", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.runBacktest.mockRejectedValueOnce(new apiMock.ApiError(400, "backtest requires loaded bars"));

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "回测中心" }));
  const backtestSettings = screen.getAllByText("回测设置").at(-1)!.closest("section")!;
  await user.click(within(backtestSettings).getByRole("button", { name: "运行回测" }));

  await waitFor(() => expect(screen.getAllByText("请求失败：backtest requires loaded bars").length).toBeGreaterThan(0));
  expect(within(backtestSettings).getByRole("button", { name: "运行回测" })).toBeEnabled();
  expect(screen.getByLabelText("回测运行状态")).toHaveTextContent("等待运行");
});

test("AppShell shows AI research API errors without replacing prior insight", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.research.mockRejectedValueOnce(new apiMock.ApiError(502, "Mock provider unavailable"));

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "AI研究员" }));
  await user.click(screen.getByRole("button", { name: "生成AI观点" }));

  await waitFor(() => expect(screen.getAllByText("请求失败：Mock provider unavailable").length).toBeGreaterThan(0));
  expect(screen.getByText("生成观点后显示技术指标、价格结构和信号证据。")).toBeVisible();
});

test("AppShell loads paper events from the configured log path", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.paperEvents.mockResolvedValueOnce(paperResponse());

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "纸面交易" }));
  await user.click(screen.getByRole("button", { name: "加载最新事件" }));

  await waitFor(() => expect(apiMock.api.paperEvents).toHaveBeenCalledWith(settings.log_path));
  expect(screen.getByText("已加载 3 条事件")).toBeVisible();
  expect(screen.getByText(/最后事件 service_stopped/)).toBeVisible();
});

test("AppShell previews Chan RSI research signals from Strategy Workshop", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.previewResearchSignals.mockResolvedValueOnce(researchSignalResponse());

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "缠论/RSI研判" }));

  await waitFor(() => expect(apiMock.api.previewResearchSignals).toHaveBeenCalledWith(settings));
  expect(await screen.findByText("CHAN_BUY_T2")).toBeVisible();
  expect(screen.getByText("回落低点抬高后向上修复")).toBeVisible();
});

test("AppShell shows risk evaluation API errors and clears busy state", async () => {
  const user = userEvent.setup();
  apiMock.api.bootstrap.mockResolvedValue({
    settings,
    catalog_available: true,
    catalog_size: 1,
    stocks: [],
    strategies: [strategy],
    limits: {}
  });
  apiMock.api.loadData.mockResolvedValueOnce(loadedDataResponse());
  apiMock.api.evaluateRisk.mockRejectedValueOnce(new apiMock.ApiError(400, "risk metrics invalid"));

  render(<AppShell />);

  await screen.findByText("已加载 1 根K线");
  await user.click(screen.getByRole("button", { name: "风控" }));
  await user.click(screen.getByRole("button", { name: "检查风控" }));

  await waitFor(() => expect(screen.getAllByText("请求失败：risk metrics invalid").length).toBeGreaterThan(0));
  expect(screen.getByRole("button", { name: "检查风控" })).toBeEnabled();
});
