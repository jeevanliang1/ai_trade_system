import { fireEvent, render, screen } from "@testing-library/react";

import { RiskPage } from "./RiskPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

function makeProps(overrides: Partial<PlatformState> = {}): PageProps {
  const state = {
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
      min_cash_balance: 10000,
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
    portfolio: { allocations: [], mode: "weighted_vote", ai_adjust: false, ai_direction: null },
    backtest: null,
    insight: null,
    aiPrompt: null,
    riskStatus: { ok: true, warnings: [], enabled: true },
    paper: null,
    message: "准备就绪",
    busy: false,
    activeBacktestMode: null,
    activePaperMode: null,
    ...overrides
  } as PlatformState;
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
    loadPaperEvents: vi.fn(),
    evaluateRisk: vi.fn()
  };
  return { state, actions };
}

test("RiskPage renders the full threshold editor", () => {
  render(<RiskPage {...makeProps()} />);

  expect(screen.getByLabelText("启用风控")).toBeChecked();
  expect(screen.getByLabelText("最大回撤阈值")).toHaveValue(20);
  expect(screen.getByLabelText("单笔最大金额")).toHaveValue(50000);
  expect(screen.getByLabelText("最小现金余额")).toHaveValue(10000);
  expect(screen.getByLabelText("最大持仓股数")).toHaveValue(50000);
  expect(screen.getByLabelText("止损模式")).toHaveValue("fixed_pct");
});

test("RiskPage updates settings through the single setSettings path", () => {
  const props = makeProps();
  render(<RiskPage {...props} />);

  fireEvent.click(screen.getByLabelText("启用风控"));
  expect(props.actions.setSettings).toHaveBeenLastCalledWith({ ...props.state.settings, risk_enabled: false });

  fireEvent.change(screen.getByLabelText("最大回撤阈值"), { target: { value: "12.5" } });
  expect(props.actions.setSettings).toHaveBeenLastCalledWith({ ...props.state.settings, max_drawdown_pct: 12.5 });

  fireEvent.change(screen.getByLabelText("单笔最大金额"), { target: { value: "25000" } });
  expect(props.actions.setSettings).toHaveBeenLastCalledWith({ ...props.state.settings, max_order_cash: 25000 });

  fireEvent.change(screen.getByLabelText("最小现金余额"), { target: { value: "5000" } });
  expect(props.actions.setSettings).toHaveBeenLastCalledWith({ ...props.state.settings, min_cash_balance: 5000 });

  fireEvent.change(screen.getByLabelText("最大持仓股数"), { target: { value: "8000" } });
  expect(props.actions.setSettings).toHaveBeenLastCalledWith({ ...props.state.settings, max_position_shares: 8000 });

  fireEvent.change(screen.getByLabelText("止损模式"), { target: { value: "trailing" } });
  expect(props.actions.setSettings).toHaveBeenLastCalledWith({ ...props.state.settings, stop_loss_mode: "trailing" });
});
