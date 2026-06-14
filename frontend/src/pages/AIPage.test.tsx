import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AIPage } from "./AIPage";
import type { PageProps, PlatformActions, PlatformState } from "./pageTypes";

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
    runBacktest: vi.fn(),
    researchAI: vi.fn(),
    runPaper: vi.fn(),
    loadPaperEvents: vi.fn(),
    evaluateRisk: vi.fn()
  };
  return { state, actions };
}

test("AIPage edits information notes as separate recent-note rows before generating research", async () => {
  const user = userEvent.setup();
  const props = makeProps();

  render(<AIPage {...props} />);

  const noteInputs = screen.getAllByRole("textbox", { name: /信息面摘要/ });
  expect(noteInputs).toHaveLength(3);

  await user.clear(noteInputs[0]);
  await user.type(noteInputs[0], "  北向资金连续净流入  ");
  await user.clear(noteInputs[1]);
  await user.clear(noteInputs[2]);
  await user.type(noteInputs[2], "关注短线追高风险");
  await user.click(screen.getByRole("button", { name: "生成AI观点" }));

  expect(props.actions.researchAI).toHaveBeenCalledWith(["北向资金连续净流入", "关注短线追高风险"], "balanced", "5个交易日");
});

test("AIPage shows generated prompt snapshot in a collapsible audit panel", async () => {
  const user = userEvent.setup();
  const prompt = "你是 A 股量化研究员\\n标的：000001\\n信息面：北向资金连续净流入";

  render(<AIPage {...makeProps({ aiPrompt: prompt })} />);

  const promptPanel = screen.getByText("生成 Prompt 快照").closest("details");
  expect(promptPanel).not.toBeNull();
  expect(promptPanel).not.toHaveAttribute("open");

  await user.click(screen.getByText("生成 Prompt 快照"));

  expect(promptPanel).toHaveAttribute("open");
  expect(screen.getByText(/标的：000001/)).toBeVisible();
  expect(screen.getByText(/信息面：北向资金连续净流入/)).toBeVisible();
});

test("AIPage groups generated evidence into technical information and risk sections", () => {
  render(
    <AIPage
      {...makeProps({
        insight: {
          symbol: "000001",
          horizon: "5个交易日",
          direction: "bullish",
          confidence: 79,
          suggested_action: "保持观察，等待回踩确认。",
          technical_evidence: ["短均线 23.22，高于长均线 22.66。"],
          information_evidence: ["政策支持流动性改善"],
          risk_warnings: ["关注短线追高风险"],
          prompt_version: "mock-v1",
          provider: "MockLLMProvider",
          created_at: "2026-06-14T00:00:00Z"
        }
      })}
    />
  );

  expect(screen.getByText("技术证据")).toBeVisible();
  expect(screen.getByText("信息面证据")).toBeVisible();
  expect(screen.getByText("风险提示")).toBeVisible();
  expect(screen.getByText("短均线 23.22，高于长均线 22.66。")).toBeVisible();
  expect(screen.getByText("政策支持流动性改善")).toBeVisible();
  expect(screen.getByText("关注短线追高风险")).toBeVisible();
});

test("AIPage shows the MockLLMProvider research-only boundary", () => {
  render(<AIPage {...makeProps()} />);

  expect(screen.getByText("Provider边界")).toBeVisible();
  expect(screen.getByText(/MockLLMProvider/)).toBeVisible();
  expect(screen.getByText(/研究观点/)).toBeVisible();
  expect(screen.getByText(/不会下单/)).toBeVisible();
  expect(screen.getByText(/不能绕过风控/)).toBeVisible();
});

test("AIPage adds and removes recent-note rows before generating research", async () => {
  const user = userEvent.setup();
  const props = makeProps();

  render(<AIPage {...props} />);

  await user.click(screen.getByRole("button", { name: "新增信息面摘要" }));
  const noteInputs = screen.getAllByRole("textbox", { name: /信息面摘要/ });
  expect(noteInputs).toHaveLength(4);

  await user.type(noteInputs[3], "业绩预告上修");
  await user.click(screen.getByRole("button", { name: "删除信息面摘要 2" }));
  await user.click(screen.getByRole("button", { name: "生成AI观点" }));

  expect(props.actions.researchAI).toHaveBeenCalledWith(["政策支持流动性改善", "关注短线追高风险", "业绩预告上修"], "balanced", "5个交易日");
});
