import { fireEvent, render, screen, within } from "@testing-library/react";

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

function backtestResult(): PlatformState["backtest"] {
  return {
    bars: [],
    metrics: {
      final_equity: 98500,
      total_return_pct: -1.5,
      annualized_return_pct: -3.2,
      benchmark_return_pct: -0.5,
      excess_return_pct: -1,
      annual_volatility_pct: 18.4,
      sharpe_ratio: -0.2,
      max_drawdown_pct: -12.4,
      trade_count: 8,
      win_rate_pct: 37.5,
      profit_factor: 0.8,
      exposure_pct: 42
    },
    equity_curve: [],
    drawdowns: [],
    trades: [],
    risk_status: { ok: false, warnings: ["最大回撤超过阈值"], enabled: true }
  };
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

test("RiskPage shows an empty deterministic example state without backtest metrics", () => {
  render(<RiskPage {...makeProps()} />);

  expect(screen.getByText("评估样例")).toBeVisible();
  expect(screen.getByText("暂无回测指标")).toBeVisible();
});

test("RiskPage shows deterministic risk inputs from current backtest metrics", () => {
  const props = makeProps({ backtest: backtestResult() });
  render(<RiskPage {...props} />);

  expect(screen.getByText("评估样例")).toBeVisible();
  const examples = screen.getByLabelText("风控评估样例");
  expect(within(examples).getByRole("table")).toHaveTextContent("max_drawdown_pct");
  expect(within(examples).getByRole("table")).toHaveTextContent("-12.40%");
  expect(within(examples).getByRole("table")).toHaveTextContent("20%");
  expect(within(examples).getByRole("table")).toHaveTextContent("8");

  fireEvent.click(screen.getByRole("button", { name: "检查风控" }));

  expect(props.actions.evaluateRisk).toHaveBeenCalledTimes(1);
});

test("RiskPage maps risk warnings to severity labels and remediation hints", () => {
  render(
    <RiskPage
      {...makeProps({
        riskStatus: {
          ok: false,
          enabled: true,
          warnings: ["最大回撤超过阈值", "单笔订单金额超过限制", "现金余额低于阈值", "持仓集中度过高"]
        }
      })}
    />
  );

  const status = screen.getByLabelText("风控状态明细");
  expect(within(status).getByText("高")).toBeVisible();
  expect(within(status).getAllByText("中")).toHaveLength(3);
  expect(within(status).getByText("降低仓位或收紧止损")).toBeVisible();
  expect(within(status).getByText("降低单笔最大金额或拆分订单")).toBeVisible();
  expect(within(status).getByText("提高现金保留或减少开仓")).toBeVisible();
  expect(within(status).getByText("降低最大持仓股数或分散标的")).toBeVisible();
});

test("RiskPage shows info remediation rows for disabled and no-warning states", () => {
  const disabled = makeProps({ riskStatus: { ok: true, enabled: false, warnings: [] } });
  const { rerender } = render(<RiskPage {...disabled} />);

  let status = screen.getByLabelText("风控状态明细");
  expect(within(status).getByText("信息")).toBeVisible();
  expect(within(status).getByText("风控已关闭")).toBeVisible();
  expect(within(status).getByText("开启风控后再评估")).toBeVisible();

  rerender(<RiskPage {...makeProps({ riskStatus: { ok: true, enabled: true, warnings: [] } })} />);

  status = screen.getByLabelText("风控状态明细");
  expect(within(status).getByText("信息")).toBeVisible();
  expect(within(status).getByText("未触发主要风控警示。")).toBeVisible();
  expect(within(status).getByText("保持当前阈值并定期复核")).toBeVisible();
});
