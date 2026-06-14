import { render, screen } from "@testing-library/react";

import { InspectorPanel } from "./InspectorPanel";
import type { AIInsight, RiskStatus } from "../types";

test("InspectorPanel shows AI direction and risk warnings", () => {
  const insight: AIInsight = {
    symbol: "000001",
    horizon: "5个交易日",
    direction: "bullish",
    confidence: 76,
    suggested_action: "buy",
    technical_evidence: ["短均线强于长均线。"],
    information_evidence: ["政策支持流动性改善。"],
    risk_warnings: ["未触发主要风控警示。"],
    prompt_version: "ai-quant-research-v1",
    provider: "MockLLMProvider",
    created_at: "2026-06-13T00:00:00Z"
  };
  const risk: RiskStatus = { ok: false, warnings: ["最大回撤超过阈值"], enabled: true };

  render(<InspectorPanel insight={insight} riskStatus={risk} />);

  expect(screen.getByText("看多")).toBeInTheDocument();
  expect(screen.getByText("76%")).toBeInTheDocument();
  expect(screen.getByText("最大回撤超过阈值")).toBeInTheDocument();
});
