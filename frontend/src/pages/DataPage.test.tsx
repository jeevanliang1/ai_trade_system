import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { DataPage } from "./DataPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

vi.mock("../api/client", () => ({
  api: {
    stocks: vi.fn()
  }
}));

const bars = [
  {
    symbol: "000001",
    exchange: "SZSE",
    trading_day: "2024-01-02",
    open_price: 10,
    high_price: 10.4,
    low_price: 9.8,
    close_price: 10.2,
    volume: 1000,
    turnover: 10200
  },
  {
    symbol: "000001",
    exchange: "SZSE",
    trading_day: "2024-01-03",
    open_price: 10.2,
    high_price: 10.8,
    low_price: 10.1,
    close_price: null as unknown as number,
    volume: 1200,
    turnover: 0
  },
  {
    symbol: "000001",
    exchange: "SZSE",
    trading_day: "2024-01-04",
    open_price: 10.3,
    high_price: 10.9,
    low_price: 10.2,
    close_price: 10.7,
    volume: 1300,
    turnover: 13910
  }
];

function makeProps(overrides: Partial<PlatformState> = {}): PageProps {
  const state: PlatformState = {
    settings: {
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
    },
    watchlist: [
      { code: "000001", name: "平安银行", exchange: "SZSE" },
      { code: "601318", name: "中国平安", exchange: "SSE" }
    ],
    strategies: [],
    selectedStrategyId: "",
    strategyParams: {},
    bars,
    dataSummary: {
      rows: 3,
      csv_path: "data/000001_daily.csv",
      symbol: "000001",
      exchange: "SZSE",
      start: "2024-01-02",
      end: "2024-01-04",
      latest_close: 10.7,
      latest_volume: 1300,
      latest_turnover: 13910,
      timeframe: "daily"
    },
    signals: null,
    portfolio: { allocations: [], mode: "weighted_vote", ai_adjust: false, ai_direction: null },
    backtest: null,
    insight: null,
    riskStatus: null,
    aiPrompt: null,
    researchSignals: null,
    paper: null,
    message: "准备就绪",
    busy: false,
    activeBacktestMode: null,
    activePaperMode: null,
    ...overrides
  };
  const actions: PlatformActions = {
    setSettings: vi.fn(),
    selectStock: vi.fn(),
    setWatchlist: vi.fn(),
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
    loadPaperEvents: vi.fn(),
    evaluateRisk: vi.fn()
  };
  return { state, actions };
}

test("DataPage searches stocks and selecting a result updates symbol exchange and CSV path", async () => {
  const user = userEvent.setup();
  vi.mocked(api.stocks).mockResolvedValue([{ code: "601318", name: "中国平安", exchange: "SSE" }]);
  const props = makeProps();

  render(<DataPage {...props} />);

  await user.type(screen.getByLabelText("搜索股票名称或代码"), "平安");

  await waitFor(() => expect(api.stocks).toHaveBeenCalledWith("平安", 8));
  await user.click(await screen.findByRole("button", { name: "601318 中国平安 SSE" }));

  expect(props.actions.selectStock).toHaveBeenCalledWith({ code: "601318", name: "中国平安", exchange: "SSE" });
});

test("DataPage can switch the current stock from the shared watchlist dropdown", async () => {
  const user = userEvent.setup();
  const props = makeProps();

  render(<DataPage {...props} />);

  await user.selectOptions(screen.getByLabelText("数据中心自选股票"), "SSE:601318");

  expect(props.actions.selectStock).toHaveBeenCalledWith({ code: "601318", name: "中国平安", exchange: "SSE" });
});

test("DataPage explains stock search network failures as local API connection issues", async () => {
  const user = userEvent.setup();
  vi.mocked(api.stocks).mockRejectedValue(new TypeError("Failed to fetch"));
  const props = makeProps();

  render(<DataPage {...props} />);

  await user.type(screen.getByLabelText("搜索股票名称或代码"), "平安");

  expect(await screen.findByText("股票搜索失败：本地 API 未连接，请确认 ./scripts/run_app.sh 正在运行。")).toBeInTheDocument();
});

test("DataPage validates date range and CSV path before load or download actions", async () => {
  const user = userEvent.setup();
  const props = makeProps({
    settings: {
      ...makeProps().state.settings,
      start_date: "20250101",
      end_date: "20240101",
      csv_path: ""
    }
  });

  render(<DataPage {...props} />);

  expect(screen.getByText("开始日期不能晚于结束日期")).toBeInTheDocument();
  expect(screen.getByText("CSV路径不能为空")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "加载CSV" }));
  await user.click(screen.getByRole("button", { name: "下载日线数据" }));

  expect(props.actions.loadData).not.toHaveBeenCalled();
  expect(props.actions.downloadData).not.toHaveBeenCalled();
});

test("DataPage renders CSV health, missing values, error recovery, and fallback demo action", async () => {
  const user = userEvent.setup();
  const props = makeProps({ message: "请求失败：AKShare timeout" });

  render(<DataPage {...props} />);

  expect(screen.getByText("数据健康")).toBeInTheDocument();
  expect(screen.getByText("3 行")).toBeInTheDocument();
  expect(screen.getByText("2024-01-02 至 2024-01-04")).toBeInTheDocument();
  expect(screen.getByText("1 处")).toBeInTheDocument();
  expect(screen.getByText("data/000001_daily.csv")).toBeInTheDocument();
  expect(screen.getByText("请求失败：AKShare timeout")).toBeInTheDocument();
  expect(screen.getByText("重试下载，或生成演示数据继续验证后续流程。")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "重试下载" }));
  await user.click(screen.getByRole("button", { name: "生成演示数据" }));

  expect(props.actions.downloadData).toHaveBeenCalled();
  expect(props.actions.demoData).toHaveBeenCalled();
});

test("DataPage health panel shows the current target CSV path when settings differ from loaded summary", () => {
  const props = makeProps({
    settings: {
      ...makeProps().state.settings,
      symbol: "601318",
      exchange: "SSE",
      csv_path: "data/601318_daily.csv"
    }
  });

  render(<DataPage {...props} />);

  expect(screen.getByText("data/601318_daily.csv")).toBeInTheDocument();
  expect(screen.getByText("待加载新路径")).toBeInTheDocument();
});

test("DataPage lets users select minute timeframe and labels download action", async () => {
  const user = userEvent.setup();
  const props = makeProps({
    settings: {
      ...makeProps().state.settings,
      timeframe: "5m",
      csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_5m_qfq_latest.csv"
    },
    dataSummary: {
      ...makeProps().state.dataSummary!,
      timeframe: "5m"
    }
  });

  render(<DataPage {...props} />);

  expect(screen.getByLabelText("行情周期")).toHaveValue("5m");
  expect(screen.getByRole("button", { name: "下载5分钟数据" })).toBeInTheDocument();
  expect(screen.getAllByText("5m").length).toBeGreaterThanOrEqual(2);

  await user.selectOptions(screen.getByLabelText("行情周期"), "15m");

  expect(props.actions.setSettings).toHaveBeenCalledWith({
    ...props.state.settings,
    timeframe: "15m",
    csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_15m_qfq_latest.csv"
  });
});
