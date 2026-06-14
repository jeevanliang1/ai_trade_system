import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { InspectorPanel } from "./InspectorPanel";
import type { AIInsight, PlatformSettings, PortfolioRequest, RiskStatus } from "../types";

const insight: AIInsight = {
  symbol: "000001",
  horizon: "5个交易日",
  direction: "bullish",
  confidence: 76,
  suggested_action: "buy",
  technical_evidence: ["短均线强于长均线。"],
  information_evidence: ["资金面流入改善。", "政策支持流动性改善。"],
  risk_warnings: ["未触发主要风控警示。"],
  prompt_version: "ai-quant-research-v1",
  provider: "MockLLMProvider",
  created_at: "2026-06-13T00:00:00Z"
};

const settings: PlatformSettings = {
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
};

const portfolio: PortfolioRequest = {
  ai_adjust: false,
  ai_direction: null,
  mode: "weighted_vote",
  allocations: [
    {
      strategy: { id: "builtin:dual", params: { symbol: "000001" } },
      weight: 1,
      enabled: true
    }
  ]
};

test("InspectorPanel shows AI direction, information summary, and risk warnings", () => {
  const risk: RiskStatus = { ok: false, warnings: ["最大回撤超过阈值"], enabled: true };

  render(
    <InspectorPanel
      insight={insight}
      riskStatus={risk}
      settings={settings}
      portfolio={portfolio}
      onSettingsChange={vi.fn()}
      onPortfolioChange={vi.fn()}
    />
  );

  expect(screen.getByText("看多")).toBeInTheDocument();
  expect(screen.getByText("76%")).toBeInTheDocument();
  expect(screen.getByText("资金面流入改善。")).toBeInTheDocument();
  expect(screen.getByText("高")).toBeInTheDocument();
  expect(screen.getByText("最大回撤超过阈值")).toBeInTheDocument();
  expect(screen.getByText("未通过：最大回撤超过阈值")).toBeInTheDocument();
});

test("InspectorPanel edits AI scoring and risk thresholds", async () => {
  const user = userEvent.setup();
  const onSettingsChange = vi.fn();
  const onPortfolioChange = vi.fn();

  render(
    <InspectorPanel
      insight={insight}
      riskStatus={{ ok: true, warnings: [], enabled: true }}
      settings={settings}
      portfolio={portfolio}
      onSettingsChange={onSettingsChange}
      onPortfolioChange={onPortfolioChange}
    />
  );

  await user.click(screen.getByLabelText("AI参与评分"));
  expect(onPortfolioChange).toHaveBeenLastCalledWith({ ...portfolio, ai_adjust: true, ai_direction: "bullish" });

  fireEvent.change(screen.getByLabelText("最大回撤阈值"), { target: { value: "12" } });
  expect(onSettingsChange).toHaveBeenLastCalledWith({ ...settings, max_drawdown_pct: 12 });

  await user.selectOptions(screen.getByLabelText("止损模式"), "trailing");
  expect(onSettingsChange).toHaveBeenLastCalledWith({ ...settings, stop_loss_mode: "trailing" });

  await user.click(screen.getByLabelText("启用风控"));
  expect(onSettingsChange).toHaveBeenLastCalledWith({ ...settings, risk_enabled: false });
});
