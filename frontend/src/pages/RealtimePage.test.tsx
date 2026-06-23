import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { api } from "../api/client";
import { RealtimePage } from "./RealtimePage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

vi.mock("../api/client", () => ({
  api: {
    realtimeStatus: vi.fn(),
    realtimeEvents: vi.fn(),
    startRealtimeMonitor: vi.fn(),
    stopRealtimeMonitor: vi.fn()
  }
}));

function makeProps(): PageProps {
  const state: PlatformState = {
    settings: {
      symbol: "000001",
      exchange: "SZSE",
      start_date: "20260601",
      end_date: "20260622",
      adjust: "qfq",
      timeframe: "1m",
      csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_1m_qfq_latest.csv",
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
    strategies: [
      {
        id: "builtin:dual_moving_average:DualMovingAverageStrategy",
        name: "DualMovingAverageStrategy",
        display_name: "双均线趋势",
        description: "快慢均线交叉",
        class_name: "DualMovingAverageStrategy",
        source: "builtin",
        path: null,
        editable: false,
        parameters: []
      }
    ],
    portfolioPresets: [],
    selectedStrategyId: "builtin:dual_moving_average:DualMovingAverageStrategy",
    strategyParams: { symbol: "000001", fast_window: 5, slow_window: 20, size: 100 },
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
    realtime: null,
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
    evaluateRisk: vi.fn(),
    startRealtimeMonitor: vi.fn(),
    stopRealtimeMonitor: vi.fn(),
    refreshRealtimeMonitor: vi.fn()
  };
  return { state, actions };
}

beforeEach(() => {
  vi.mocked(api.realtimeStatus).mockResolvedValue({
    running: false,
    started_at: null,
    stopped_at: null,
    strategy_id: null,
    symbols: [],
    timeframe: null,
    poll_interval_seconds: null,
    event_count: 0,
    last_event_at: null,
    last_bar_time: null,
    last_error: null
  });
  vi.mocked(api.realtimeEvents).mockResolvedValue({
    events: [
      {
        id: "evt-1",
        event: "signal_triggered",
        created_at: "2026-06-22T10:02:00",
        symbol: "000001",
        name: "平安银行",
        exchange: "SZSE",
        timeframe: "1m",
        bar_time: "2026-06-22T10:02:00",
        side: "buy",
        price: 14,
        volume: 100,
        reason: "threshold reached"
      }
    ]
  });
  vi.mocked(api.startRealtimeMonitor).mockResolvedValue({
    running: true,
    started_at: "2026-06-22T10:00:00",
    stopped_at: null,
    strategy_id: "builtin:dual_moving_average:DualMovingAverageStrategy",
    symbols: ["000001.SZSE"],
    timeframe: "1m",
    poll_interval_seconds: 30,
    event_count: 1,
    last_event_at: "2026-06-22T10:00:00",
    last_bar_time: null,
    last_error: null
  });
  vi.mocked(api.stopRealtimeMonitor).mockResolvedValue({
    running: false,
    started_at: "2026-06-22T10:00:00",
    stopped_at: "2026-06-22T10:03:00",
    strategy_id: null,
    symbols: [],
    timeframe: null,
    poll_interval_seconds: null,
    event_count: 2,
    last_event_at: "2026-06-22T10:03:00",
    last_bar_time: "2026-06-22T10:02:00",
    last_error: null
  });
});

test("RealtimePage refreshes events and wires monitor controls", async () => {
  const props = makeProps();
  render(<RealtimePage {...props} />);

  expect(await screen.findByText("实时盯盘")).toBeVisible();
  expect(screen.getByText("threshold reached")).toBeVisible();
  expect(screen.getAllByText("000001 SZSE").length).toBeGreaterThan(0);

  await userEvent.click(screen.getByRole("button", { name: "启动盯盘" }));
  expect(props.actions.startRealtimeMonitor).toHaveBeenCalledWith(30);

  await userEvent.click(screen.getByRole("button", { name: "停止盯盘" }));
  expect(props.actions.stopRealtimeMonitor).toHaveBeenCalled();
});
