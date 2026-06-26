import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AgentGovernancePage } from "./AgentGovernancePage";

const apiMock = vi.hoisted(() => ({
  api: {
    agentMemories: vi.fn(),
    createAgentMemory: vi.fn(),
    updateAgentMemory: vi.fn(),
    deleteAgentMemory: vi.fn(),
    agentSkills: vi.fn(),
    createAgentSkill: vi.fn(),
    updateAgentSkill: vi.fn(),
    deleteAgentSkill: vi.fn(),
    agentPolicy: vi.fn(),
    updateAgentPolicy: vi.fn(),
    previewAgentPlan: vi.fn()
  }
}));

vi.mock("../api/client", () => apiMock);

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.api.agentMemories.mockResolvedValue({
    memories: [
      {
        id: "mem_weekly_scan_reuse",
        type: "workflow_rule",
        scope: "agent",
        title: "本周扫描结果优先复用",
        content: "优先读取 automation.weekly_result",
        tags: ["weekly", "scan"],
        source: "system_default",
        confidence: "high",
        enabled: true,
        expires_at: null
      }
    ]
  });
  apiMock.api.agentSkills.mockResolvedValue({
    skills: [
      {
        id: "weekly_scan_share",
        title: "周度扫描研究分享",
        description: "复用周榜并生成分享文本",
        trigger_terms: ["这周", "分享"],
        steps: ["automation.weekly_result", "research.batch_fundamental", "share.weixin"],
        allowed_tools: ["automation.weekly_result", "research.batch_fundamental", "share.weixin"],
        required_confirmations: ["research.batch_fundamental"],
        output_format: "weixin_ready_report",
        enabled: true
      }
    ]
  });
  apiMock.api.agentPolicy.mockResolvedValue({
    policy: {
      max_steps: 8,
      blocked_intents: ["实盘", "下单"],
      tool_permissions: { "research.batch_fundamental": "confirm" },
      default_output_format: "agent_report"
    }
  });
  apiMock.api.previewAgentPlan.mockResolvedValue({
    preview: {
      status: "ok",
      intent: "weekly_scan_share",
      selected_skill: { id: "weekly_scan_share", title: "周度扫描研究分享" },
      matched_memories: [{ id: "mem_weekly_scan_reuse", title: "本周扫描结果优先复用" }],
      steps: [
        { index: 1, tool: "automation.weekly_result", permission: "auto", reason: "读取周榜" },
        { index: 2, tool: "research.batch_fundamental", permission: "confirm", reason: "外部研究" },
        { index: 3, tool: "share.weixin", permission: "auto", reason: "准备分享" }
      ],
      stop_conditions: ["live_trading_blocked", "requires_confirmation"],
      final_output: "weixin_ready_report",
      blocked_reason: null,
      ignored_tools: []
    }
  });
});

test("renders memory skill policy and plan preview governance areas", async () => {
  const user = userEvent.setup();
  render(<AgentGovernancePage />);

  expect(await screen.findByText("Agent治理")).toBeInTheDocument();
  expect(screen.getByText("Memory")).toBeInTheDocument();
  expect(screen.getByText("Skills")).toBeInTheDocument();
  expect(screen.getByText("Planner Policy")).toBeInTheDocument();
  expect(screen.getByText("Plan Preview")).toBeInTheDocument();
  expect(await screen.findByText("本周扫描结果优先复用")).toBeInTheDocument();
  expect(await screen.findByText("weekly_scan_share")).toBeInTheDocument();
  expect(await screen.findByDisplayValue("8")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "预览计划" }));

  await waitFor(() => expect(apiMock.api.previewAgentPlan).toHaveBeenCalled());
  expect(await screen.findByText("automation.weekly_result")).toBeInTheDocument();
  expect(screen.getByText("research.batch_fundamental")).toBeInTheDocument();
  expect(screen.getByText("share.weixin")).toBeInTheDocument();
  expect(screen.getByText("本周扫描结果优先复用")).toBeInTheDocument();
});
