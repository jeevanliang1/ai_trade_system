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
      score_mode: "research",
	    scanned: 2,
    available: 1,
    missing: 1,
    rows: [
      {
        rank: 1,
        code: "000001",
        name: "平安银行",
        exchange: "SZSE",
        csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv",
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
        momentum: null,
        blockers: []
      },
      {
        rank: 2,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv",
        status: "missing_data",
        score: null,
        latest_signal: null,
        preview: null,
        momentum: null,
        blockers: [{ code: "MISSING_CSV", message: "未找到本地行情 CSV：data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv" }]
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(
    makeProps().state.settings,
    expect.objectContaining({
      query: "",
      limit: 20,
      min_bars: 60,
      lookback: 120,
      universe: "catalog",
      score_mode: "research",
      auto_update_data: false
    })
  );
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
    score_mode: "research",
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

test("SignalRadarPage submits STAR universe with auto data update", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "star",
    score_mode: "research",
    scanned: 0,
    available: 0,
    missing: 0,
    data_update: {
      enabled: true,
      total: 0,
      updated: 0,
      skipped: 0,
      failed: 0,
      adjust: "qfq",
      start_date: "20240101",
      end_date: "20241231"
    },
    rows: []
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.selectOptions(screen.getByLabelText("扫描范围"), "star");
  await user.click(screen.getByLabelText("扫描前自动更新数据"));
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(
    makeProps().state.settings,
    expect.objectContaining({
      universe: "star",
      auto_update_data: true,
      if_stale: true
    })
  );
});

test("SignalRadarPage renders batch data maintenance summary", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "star",
    score_mode: "volume_momentum",
    scanned: 2,
    available: 1,
    missing: 1,
    data_update: {
      enabled: true,
      total: 2,
      updated: 1,
      skipped: 0,
      failed: 1,
      adjust: "qfq",
      start_date: "20240101",
      end_date: "20241231"
    },
    rows: [
      {
        rank: 1,
        code: "688001",
        name: "华兴源创",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688001/688001_SSE_daily_qfq_latest.csv",
        status: "scanned",
        score: {
          total_score: 60,
          direction: "bullish",
          confidence: 0.7,
          chan_score: 0,
          rsi_score: 0,
          summary: "动量通过"
        },
        latest_signal: null,
        preview: null,
        momentum: null,
        blockers: [],
        data_status: {
          status: "updated",
          message: "updated 80 bars",
          rows: 80,
          start: "2026-01-01",
          end: "2026-03-21",
          path: "data/market/a_share/SSE/688001/688001_SSE_daily_qfq_latest.csv"
        }
      },
      {
        rank: 2,
        code: "688002",
        name: "睿创微纳",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688002/688002_SSE_daily_qfq_latest.csv",
        status: "missing_data",
        score: null,
        latest_signal: null,
        preview: null,
        momentum: null,
        blockers: [{ code: "DATA_UPDATE_FAILED", message: "network down" }],
        data_status: {
          status: "failed",
          message: "network down",
          rows: 0,
          start: null,
          end: null,
          path: "data/market/a_share/SSE/688002/688002_SSE_daily_qfq_latest.csv"
        }
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.selectOptions(screen.getByLabelText("评分模式"), "volume_momentum");
  await user.click(screen.getByLabelText("扫描前自动更新数据"));
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(await screen.findByText("数据维护")).toBeVisible();
  expect(screen.getByText("已更新")).toBeVisible();
  expect(screen.getAllByText("1").length).toBeGreaterThan(0);
  expect(screen.getByText("失败")).toBeVisible();
  expect(screen.getByText(/数据 updated · 80 根/)).toBeVisible();
  expect(screen.getByText(/数据 failed · 0 根/)).toBeVisible();
});

test("SignalRadarPage prepares missing-data candidates in shared data settings", async () => {
  const user = userEvent.setup();
  const props = makeProps();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "catalog",
    score_mode: "research",
    scanned: 1,
    available: 0,
    missing: 1,
    rows: [
      {
        rank: 1,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv",
        status: "missing_data",
        score: null,
        latest_signal: null,
        preview: null,
        momentum: null,
        blockers: [{ code: "MISSING_CSV", message: "未找到本地行情 CSV：data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv" }]
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
      csv_path: "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"
    })
  );
});

test("SignalRadarPage keeps scan history and exposes a CSV export link", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "平安",
    universe: "catalog",
    score_mode: "research",
    scanned: 1,
    available: 1,
    missing: 0,
    rows: [
      {
        rank: 1,
        code: "000001",
        name: "平安银行",
        exchange: "SZSE",
        csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv",
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
        momentum: null,
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
  expect(exportLink.getAttribute("href")).toContain(
    encodeURIComponent("rank,code,name,exchange,status,total_score,direction,confidence,latest_signal,momentum_pct,volume_ratio,trend_pass,latest_reason,csv_path")
  );
  expect(exportLink.getAttribute("href")).toContain(
    encodeURIComponent("1,000001,平安银行,SZSE,scanned,32,bullish,0.44,,,,,,data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv")
  );
});

test("SignalRadarPage submits volume momentum score mode and renders diagnostics", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "catalog",
    score_mode: "volume_momentum",
    scanned: 1,
    available: 1,
    missing: 0,
    rows: [
      {
        rank: 1,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv",
        status: "scanned",
        score: {
          total_score: 92,
          direction: "bullish",
          confidence: 0.86,
          chan_score: 0,
          rsi_score: 0,
          summary: "动量 18.20%，放量 2.10倍，趋势通过",
          momentum: {
            momentum_pct: 18.2,
            volume_ratio: 2.1,
            trend_pass: true,
            entry_ready: true,
            latest_reason: "volume_confirmed_momentum_entry"
          }
        },
        latest_signal: {
          trading_day: "2026-06-18",
          symbol: "688981",
          exchange: "SSE",
          kind: "volume_momentum",
          action: "buy",
          price: 50.2,
          strength: 0.86,
          score: 92,
          title: "量价动量触发",
          reason: "volume_confirmed_momentum_entry",
          tags: ["volume_momentum"]
        },
        preview: null,
        momentum: {
          momentum_pct: 18.2,
          volume_ratio: 2.1,
          trend_pass: true,
          entry_ready: true,
          latest_reason: "volume_confirmed_momentum_entry"
        },
        blockers: []
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.selectOptions(screen.getByLabelText("评分模式"), "volume_momentum");
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(makeProps().state.settings, expect.objectContaining({ score_mode: "volume_momentum" }));
  expect(await screen.findByText("量价动量排行")).toBeVisible();
  expect(screen.getAllByText(/动量 18.20%/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/放量 2.10倍/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/趋势通过/).length).toBeGreaterThan(0);
});


test("SignalRadarPage submits chan structure score mode and renders diagnostics", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "catalog",
    score_mode: "chan_structure",
    scanned: 1,
    available: 1,
    missing: 0,
    rows: [
      {
        rank: 1,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv",
        status: "scanned",
        score: {
          total_score: 44,
          direction: "bullish",
          confidence: 0.79,
          chan_score: 44,
          rsi_score: 0,
          summary: "分型 7 个，笔 4 条，中枢 2 个，缠论三买",
          chan_structure: {
            fractal_count: 7,
            stroke_count: 4,
            pivot_count: 2,
            latest_signal_kind: "CHAN_STRUCT_BUY_T3",
            latest_signal_title: "缠论三买"
          }
        },
        latest_signal: {
          trading_day: "2026-06-18",
          symbol: "688981",
          exchange: "SSE",
          kind: "CHAN_STRUCT_BUY_T3",
          action: "buy",
          price: 130.5,
          strength: 0.78,
          score: 44,
          title: "缠论三买",
          reason: "向上离开中枢后的回抽未跌回中枢上沿",
          tags: ["chan", "structure", "third-buy"]
        },
        preview: null,
        momentum: null,
        blockers: []
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.selectOptions(screen.getByLabelText("评分模式"), "chan_structure");
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(makeProps().state.settings, expect.objectContaining({ score_mode: "chan_structure" }));
  expect(await screen.findByText("缠论结构排行")).toBeVisible();
  expect(screen.getAllByText(/分型 7/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/笔 4/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/中枢 2/).length).toBeGreaterThan(0);
  expect(screen.getAllByText("缠论三买").length).toBeGreaterThan(0);
});
