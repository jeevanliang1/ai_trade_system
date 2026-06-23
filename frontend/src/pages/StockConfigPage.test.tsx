import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { StockConfigPage } from "./StockConfigPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

vi.mock("../api/client", () => ({
  api: {
    stocks: vi.fn(),
    saveWatchlist: vi.fn()
  }
}));

function makeProps(overrides: Partial<PlatformState> = {}, actionOverrides: Partial<PlatformActions> = {}): PageProps {
  const state: PlatformState = {
    settings: {
      symbol: "000001",
      exchange: "SZSE",
      start_date: "20240618",
      end_date: "20260618",
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
    watchlist: [{ code: "000001", name: "平安银行", exchange: "SZSE" }],
    managedData: [
      {
        code: "000001",
        name: "平安银行",
        exchange: "SZSE",
        adjust: "qfq",
        timeframe: "daily",
        latest_path: "data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv",
        manifest_path: "data/market/a_share/SZSE/000001/manifest.json",
        exists: true,
        stale: false,
        latest_start: "2024-06-18",
        latest_end: "2026-06-18",
        latest_rows: 488,
        last_increment_path: "data/market/a_share/SZSE/000001/increments/000001_SZSE_daily_qfq_20260618_from_20260618_to_20260618.csv",
        last_updated_at: "2026-06-18T20:00:00",
        last_status: "updated",
        last_error: null
      }
    ],
    strategies: [],
    selectedStrategyId: "",
    strategyParams: {},
    bars: [],
    dataSummary: null,
    signals: null,
    researchSignals: null,
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
  };
  const actions: PlatformActions = {
    setSettings: vi.fn(),
    selectStock: vi.fn(),
    setWatchlist: vi.fn(),
    updateWatchlistData: vi.fn(),
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

test("StockConfigPage searches, adds, selects, and removes watchlist stocks", async () => {
  const user = userEvent.setup();
  const setWatchlist = vi.fn();
  const selectStock = vi.fn();
  vi.mocked(api.stocks).mockResolvedValue([{ code: "601318", name: "中国平安", exchange: "SSE" }]);
  vi.mocked(api.saveWatchlist).mockResolvedValue({
    stocks: [
      { code: "000001", name: "平安银行", exchange: "SZSE" },
      { code: "601318", name: "中国平安", exchange: "SSE" }
    ]
  });

  render(<StockConfigPage {...makeProps({}, { setWatchlist, selectStock })} />);

  await user.type(screen.getByLabelText("搜索股票加入自选"), "平安");
  await waitFor(() => expect(api.stocks).toHaveBeenCalledWith("平安", 10));
  await user.click(await screen.findByRole("button", { name: "添加 601318 中国平安 SSE" }));

  expect(api.saveWatchlist).toHaveBeenCalledWith([
    { code: "000001", name: "平安银行", exchange: "SZSE" },
    { code: "601318", name: "中国平安", exchange: "SSE" }
  ]);
  expect(setWatchlist).toHaveBeenCalledWith([
    { code: "000001", name: "平安银行", exchange: "SZSE" },
    { code: "601318", name: "中国平安", exchange: "SSE" }
  ]);

  await user.click(screen.getByRole("button", { name: "设为当前 000001 平安银行" }));
  expect(selectStock).toHaveBeenCalledWith({ code: "000001", name: "平安银行", exchange: "SZSE" });

  vi.mocked(api.saveWatchlist).mockResolvedValueOnce({ stocks: [] });
  await user.click(screen.getByRole("button", { name: "移除 000001 平安银行" }));

  expect(api.saveWatchlist).toHaveBeenLastCalledWith([]);
  expect(setWatchlist).toHaveBeenLastCalledWith([]);
});

test("StockConfigPage shows managed data status and triggers watchlist data update", async () => {
  const user = userEvent.setup();
  const updateWatchlistData = vi.fn();

  render(<StockConfigPage {...makeProps({}, { updateWatchlistData })} />);

  expect(screen.getByText("数据已更新至 2026-06-18")).toBeInTheDocument();
  expect(screen.getByText("488 行 · daily")).toBeInTheDocument();
  expect(screen.getByText("data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "更新全部自选股数据" }));

  expect(updateWatchlistData).toHaveBeenCalledTimes(1);
});
