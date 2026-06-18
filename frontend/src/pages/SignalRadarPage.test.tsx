import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { SignalRadarPage } from "./SignalRadarPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

vi.mock("../api/client", () => ({
  api: {
    batchResearchSignals: vi.fn()
  }
}));

function makeProps(overrides: Partial<PlatformState> = {}): PageProps {
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
    evaluateRisk: vi.fn()
  };
  return { state, actions };
}

test("SignalRadarPage runs a batch scan and renders ranked local CSV results", async () => {
  const user = userEvent.setup();
	  vi.mocked(api.batchResearchSignals).mockResolvedValue({
	    query: "",
	    universe: "catalog",
	    scanned: 2,
    available: 1,
    missing: 1,
    rows: [
      {
        rank: 1,
        code: "000001",
        name: "平安银行",
        exchange: "SZSE",
        csv_path: "data/000001_daily.csv",
        status: "scanned",
        score: {
          total_score: 32,
          direction: "bullish",
          confidence: 0.44,
          chan_score: 24,
          rsi_score: 8,
          summary: "发现 2 个研究信号，综合方向为 bullish"
        },
        latest_signal: {
          trading_day: "2024-05-01",
          symbol: "000001",
          exchange: "SZSE",
          kind: "CHAN_BUY_T2",
          action: "buy",
          price: 12.3,
          strength: 0.8,
          score: 24,
          title: "二买观察",
          reason: "低点抬高后重新转强",
          tags: ["chan"]
        },
        preview: null,
        blockers: []
      },
      {
        rank: 2,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/688981_daily.csv",
        status: "missing_data",
        score: null,
        latest_signal: null,
        preview: null,
        blockers: [{ code: "MISSING_CSV", message: "未找到本地行情 CSV：data/688981_daily.csv" }]
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(makeProps().state.settings, { query: "", limit: 20, min_bars: 60, lookback: 120, universe: "catalog" });
  expect((await screen.findAllByText(/全部目录 · 可扫描 1 \/ 缺数据 1/)).length).toBeGreaterThan(0);
  expect(screen.getByText("平安银行")).toBeVisible();
  expect(screen.getAllByText("看多").length).toBeGreaterThan(0);
  expect(screen.getAllByText("二买观察").length).toBeGreaterThan(0);
  expect(screen.getAllByText("缺少CSV").length).toBeGreaterThan(0);
});

test("SignalRadarPage submits the selected scan universe", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "local_csv",
    scanned: 0,
    available: 0,
    missing: 0,
    rows: []
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.selectOptions(screen.getByLabelText("扫描范围"), "local_csv");
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(makeProps().state.settings, expect.objectContaining({ universe: "local_csv" }));
});

test("SignalRadarPage prepares missing-data candidates in shared data settings", async () => {
  const user = userEvent.setup();
  const props = makeProps();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "catalog",
    scanned: 1,
    available: 0,
    missing: 1,
    rows: [
      {
        rank: 1,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/688981_daily.csv",
        status: "missing_data",
        score: null,
        latest_signal: null,
        preview: null,
        blockers: [{ code: "MISSING_CSV", message: "未找到本地行情 CSV：data/688981_daily.csv" }]
      }
    ]
  });

  render(<SignalRadarPage {...props} />);

  await user.click(screen.getByRole("button", { name: "批量扫描" }));
  await user.click(await screen.findByRole("button", { name: "准备 688981 数据" }));

  expect(props.actions.setSettings).toHaveBeenCalledWith(
    expect.objectContaining({
      symbol: "688981",
      exchange: "SSE",
      csv_path: "data/688981_daily.csv"
    })
  );
});

test("SignalRadarPage keeps scan history and exposes a CSV export link", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "平安",
    universe: "catalog",
    scanned: 1,
    available: 1,
    missing: 0,
    rows: [
      {
        rank: 1,
        code: "000001",
        name: "平安银行",
        exchange: "SZSE",
        csv_path: "data/000001_daily.csv",
        status: "scanned",
        score: {
          total_score: 32,
          direction: "bullish",
          confidence: 0.44,
          chan_score: 24,
          rsi_score: 8,
          summary: "发现 2 个研究信号，综合方向为 bullish"
        },
        latest_signal: null,
        preview: null,
        blockers: []
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.type(screen.getByLabelText("雷达搜索股票名称或代码"), "平安");
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(await screen.findByText(/历史扫描/)).toBeVisible();
  expect(screen.getByText("平安")).toBeVisible();
  expect(screen.getAllByText(/全部目录 · 可扫描 1 \/ 缺数据 0/).length).toBeGreaterThan(0);
  expect(screen.getByText(/候选 1/)).toBeVisible();
  const exportLink = screen.getByRole("link", { name: "导出CSV" });
  expect(exportLink).toHaveAttribute("download", "signal-radar-scan.csv");
  expect(exportLink.getAttribute("href")).toContain(encodeURIComponent("rank,code,name,exchange,status,total_score,direction,confidence,latest_signal,csv_path"));
  expect(exportLink.getAttribute("href")).toContain(encodeURIComponent("1,000001,平安银行,SZSE,scanned,32,bullish,0.44,,data/000001_daily.csv"));
});
