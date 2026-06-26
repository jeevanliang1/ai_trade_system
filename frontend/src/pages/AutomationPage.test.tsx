import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { AutomationPage } from "./AutomationPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

vi.mock("../api/client", () => ({
  api: {
    automationStatus: vi.fn(),
    automationTop10: vi.fn(),
    automationJudgments: vi.fn(),
    updateAutomationConfig: vi.fn(),
    runAutomationWeekly: vi.fn(),
    runAutomationDaily: vi.fn()
  }
}));

function makeProps(): PageProps {
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
    watchlist: [],
    managedData: [],
    strategies: [],
    portfolioPresets: [],
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
    activePaperMode: null
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
    evaluateRisk: vi.fn()
  };
  return { state, actions };
}

beforeEach(() => {
  vi.mocked(api.automationStatus).mockResolvedValue({
    config: {
      enabled: true,
      timezone: "Asia/Shanghai",
      weekly_weekday: 5,
      weekly_time: "09:30",
      daily_time: "09:45",
      top_n: 10,
      adjust: "qfq",
      min_bars: 60,
      lookback: 120,
      chan_weight: 1,
      volume_weight: 0.35
    },
    running: false,
    last_weekly_run: null,
    last_daily_run: {
      run_id: "daily-failed",
      task: "daily",
      status: "failed",
      started_at: "2026-06-20T09:45:00",
      finished_at: "2026-06-20T09:46:00",
      message: "AKShare timeout"
    },
    recent_runs: [
      {
        run_id: "daily-failed",
        task: "daily",
        status: "failed",
        started_at: "2026-06-20T09:45:00",
        finished_at: "2026-06-20T09:46:00",
        message: "AKShare timeout"
      },
      {
        run_id: "weekly-ok",
        task: "weekly",
        status: "success",
        started_at: "2026-06-20T09:30:00",
        finished_at: "2026-06-20T09:31:00",
        message: "success"
      }
    ],
    diagnostics: [
      {
        code: "RUN_FAILED",
        severity: "high",
        task: "daily",
        message: "日判断失败：AKShare timeout",
        suggestion: "检查行情源网络后重跑日判断",
        run_id: "daily-failed",
        created_at: "2026-06-20T09:46:00"
      }
    ],
    weekly_top10_count: 1,
    latest_daily_judgment_count: 1,
    next_weekly_run: null,
    next_daily_run: null
  });
  vi.mocked(api.automationTop10).mockResolvedValue({
    run_id: "weekly-1",
    generated_at: "2026-06-20T09:30:00+08:00",
    status: "success",
    total_candidates: 2,
    scanned: 2,
    missing: 0,
    top: [
      {
        code: "688001",
        name: "华兴源创",
        exchange: "SSE",
        rank: 1,
        composite_score: 81.2,
        chan_score: 70,
        volume_score: 32,
        latest_day: "2026-06-19",
        latest_close: 42.18,
        chan_signal_title: "缠论三买",
        chan_signal_action: "buy",
        volume_entry_ready: true,
        reason: "三买结构，量价确认"
      }
    ]
  });
  vi.mocked(api.automationJudgments).mockResolvedValue({
    date: "2026-06-23",
    judgments: [
      {
        code: "688001",
        name: "华兴源创",
        exchange: "SSE",
        judgment: "aggressive_add",
        reason: "三买延续且背驰确认，量价动量保持",
        current_score: 86.5,
        baseline_score: 81.2,
        latest_day: "2026-06-23",
        latest_close: 44.2,
        chan_signal_title: "缠论三买",
        volume_entry_ready: true
      }
    ]
  });
  vi.mocked(api.updateAutomationConfig).mockImplementation(async (request) => ({
    enabled: true,
    timezone: "Asia/Shanghai",
    weekly_weekday: 5,
    weekly_time: "09:30",
    daily_time: "09:45",
    top_n: request.top_n ?? 10,
    adjust: "qfq",
    min_bars: 60,
    lookback: 120,
    chan_weight: request.chan_weight ?? 1,
    volume_weight: request.volume_weight ?? 0.35
  }));
  vi.mocked(api.runAutomationWeekly).mockResolvedValue({
    run_id: "weekly-2",
    generated_at: "2026-06-20T10:00:00+08:00",
    status: "success",
    total_candidates: 1,
    scanned: 1,
    missing: 0,
    top: []
  });
  vi.mocked(api.runAutomationDaily).mockResolvedValue({ date: "2026-06-23", judgments: [] });
});

test("AutomationPage loads automation status, weekly top10, and daily judgments", async () => {
  render(<AutomationPage {...makeProps()} />);

  expect(await screen.findByText("自动任务管理")).toBeVisible();
  expect(screen.getAllByText("华兴源创").length).toBeGreaterThan(0);
  expect(screen.getByText("三买结构，量价确认")).toBeVisible();
  expect(screen.getByText("三买延续且背驰确认，量价动量保持")).toBeVisible();
  expect(screen.getByText("周六 09:30")).toBeVisible();
  expect(screen.getByText("运行诊断")).toBeVisible();
  expect(screen.getByText("日判断失败：AKShare timeout")).toBeVisible();
  expect(screen.getByText("最近运行")).toBeVisible();
  expect(screen.getByText("daily-failed")).toBeVisible();
});

test("AutomationPage saves config and runs manual automation tasks", async () => {
  const user = userEvent.setup();
  render(<AutomationPage {...makeProps()} />);

  await screen.findByText("自动任务管理");
  const topNInput = await screen.findByLabelText("Top N 数量");
  const volumeWeightInput = await screen.findByLabelText("量价权重");
  await user.clear(topNInput);
  await user.type(topNInput, "8");
  await user.clear(volumeWeightInput);
  await user.type(volumeWeightInput, "0.5");
  await user.click(screen.getByRole("button", { name: "保存配置" }));
  await user.click(screen.getByRole("button", { name: "立即跑周扫描" }));
  await user.click(screen.getByRole("button", { name: "立即跑日判断" }));

  expect(api.updateAutomationConfig).toHaveBeenCalledWith(expect.objectContaining({ top_n: 8, volume_weight: 0.5 }));
  expect(api.runAutomationWeekly).toHaveBeenCalled();
  expect(api.runAutomationDaily).toHaveBeenCalled();
});
