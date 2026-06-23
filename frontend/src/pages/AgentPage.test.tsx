import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { AgentPage } from "./AgentPage";

const apiMock = vi.hoisted(() => ({
  api: {
    agentTools: vi.fn(),
    agentTasks: vi.fn(),
    createAgentTask: vi.fn(),
    approveAgentTask: vi.fn(),
    agentTaskTrace: vi.fn()
  }
}));

vi.mock("../api/client", () => apiMock);

function completedTask() {
  return {
    task_id: "agt_done",
    source: "weixin",
    prompt: "帮我研究 000001",
    status: "completed",
    context: { symbol: "000001" },
    plan: ["system.snapshot", "research.fundamental", "agent.report"],
    steps: [
      { tool_name: "system.snapshot", title: "读取系统边界", status: "completed", summary: "系统状态正常", output: {} },
      { tool_name: "research.fundamental", title: "请求 OpenClaw", status: "completed", summary: "OpenClaw 未配置", output: {} }
    ],
    evidence: [{ tool: "research.fundamental", summary: "OpenClaw 未配置", status: "not_configured" }],
    result_summary: "000001 Agent 任务完成",
    confirmations: [],
    report_path: "reports/agt_done.json",
    created_at: "2026-06-20T00:00:00Z",
    updated_at: "2026-06-20T00:00:10Z"
  };
}

function blockedTask() {
  return {
    ...completedTask(),
    task_id: "agt_blocked",
    source: "openclaw",
    prompt: "帮我实盘买入 000001",
    status: "blocked",
    steps: [],
    evidence: [],
    result_summary: "任务已阻断",
    confirmations: [
      {
        code: "LIVE_TRADING_BLOCKED",
        message: "检测到实盘或下单意图",
        risk_level: "blocked",
        status: "blocked",
        tool_name: null,
        created_at: "2026-06-20T00:00:00Z",
        resolved_at: null
      }
    ]
  };
}

function waitingTask() {
  return {
    ...completedTask(),
    task_id: "agt_waiting",
    status: "waiting_confirmation",
    result_summary: "等待确认后继续执行 research.fundamental。",
    steps: [{ tool_name: "system.snapshot", title: "读取系统边界", status: "completed", summary: "系统状态正常", output: {} }],
    evidence: [{ tool: "system.snapshot", summary: "系统状态正常", status: "ok" }],
    confirmations: [
      {
        code: "TOOL_CONFIRMATION_REQUIRED",
        message: "工具 research.fundamental 需要确认后才能继续执行。",
        risk_level: "high",
        status: "pending",
        tool_name: "research.fundamental",
        created_at: "2026-06-20T00:00:00Z",
        resolved_at: null
      }
    ],
    report_path: null
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  apiMock.api.agentTools.mockResolvedValue({
    tools: [
      { name: "system.snapshot", description: "读取系统状态", permission: "auto", category: "system" },
      { name: "research.fundamental", description: "外部信息代理", permission: "confirm", category: "external_research" },
      { name: "data.update", description: "更新行情", permission: "auto", category: "market_data" },
      { name: "radar.scan", description: "信号扫描", permission: "auto", category: "research" },
      { name: "backtest.run", description: "运行回测", permission: "auto", category: "backtest" },
      { name: "risk.evaluate", description: "风控评估", permission: "auto", category: "risk" },
      { name: "paper.run", description: "纸面交易", permission: "auto", category: "paper" }
    ]
  });
  apiMock.api.agentTasks.mockResolvedValue({ tasks: [completedTask()] });
  apiMock.api.agentTaskTrace.mockResolvedValue({
    task_id: "agt_done",
    events: [
      {
        event_id: "000001",
        task_id: "agt_done",
        type: "request_received",
        created_at: "2026-06-20T00:00:00Z",
        tool_name: null,
        status: "pending",
        summary: "收到来自 weixin 的 Agent 请求。",
        payload: { source: "weixin" }
      },
      {
        event_id: "000004",
        task_id: "agt_done",
        type: "tool_finished",
        created_at: "2026-06-20T00:00:03Z",
        tool_name: "research.fundamental",
        status: "completed",
        summary: "OpenClaw 未配置",
        payload: { duration_ms: 12, output: { status: "not_configured" } }
      }
    ]
  });
});

test("renders command center task status, tools, evidence, and report path", async () => {
  render(<AgentPage />);

  expect(await screen.findByText("AI指挥台")).toBeInTheDocument();
  expect(screen.getByText("agt_done")).toBeInTheDocument();
  expect(screen.getByText("已完成")).toBeInTheDocument();
  expect(screen.getByText("research.fundamental")).toBeInTheDocument();
  expect(screen.getByText("data.update · auto")).toBeInTheDocument();
  expect(screen.getByText("backtest.run · auto")).toBeInTheDocument();
  expect(screen.getAllByText(/OpenClaw 未配置/).length).toBeGreaterThan(0);
  expect(screen.getByText("reports/agt_done.json")).toBeInTheDocument();
});

test("submits a task and shows blocked confirmation details", async () => {
  const user = userEvent.setup();
  apiMock.api.createAgentTask.mockResolvedValue({ task: blockedTask() });

  render(<AgentPage />);

  const prompt = await screen.findByLabelText("任务指令");
  await user.clear(prompt);
  await user.type(prompt, "帮我实盘买入 000001");
  await user.selectOptions(screen.getByLabelText("来源"), "openclaw");
  await user.click(screen.getByRole("button", { name: "创建Agent任务" }));

  await waitFor(() => expect(apiMock.api.createAgentTask).toHaveBeenCalledWith("帮我实盘买入 000001", "openclaw", expect.any(Object)));
  expect(await screen.findByText("LIVE_TRADING_BLOCKED")).toBeInTheDocument();
  expect(screen.getByText("检测到实盘或下单意图")).toBeInTheDocument();
});

test("polls Agent task status while the command center is open", async () => {
  vi.useFakeTimers();
  try {
    render(<AgentPage />);

    await act(async () => {
      await Promise.resolve();
    });

    expect(screen.getByText("agt_done")).toBeInTheDocument();
    expect(apiMock.api.agentTasks).toHaveBeenCalledTimes(1);

    await act(async () => {
      vi.advanceTimersByTime(3000);
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(apiMock.api.agentTasks).toHaveBeenCalledTimes(2);
  } finally {
    vi.useRealTimers();
  }
});

test("shows pending tool confirmation and submits approval", async () => {
  const user = userEvent.setup();
  apiMock.api.agentTasks.mockResolvedValue({ tasks: [waitingTask()] });
  apiMock.api.approveAgentTask.mockResolvedValue({
    task: {
      ...waitingTask(),
      status: "queued",
      confirmations: [{ ...waitingTask().confirmations[0], status: "approved", resolved_at: "2026-06-20T00:00:05Z" }]
    }
  });

  render(<AgentPage />);

  expect(await screen.findByText("等待确认")).toBeInTheDocument();
  expect(screen.getByText(/research.fundamental · 工具 research.fundamental/)).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "确认" }));

  expect(apiMock.api.approveAgentTask).toHaveBeenCalledWith("agt_waiting", "approved");
  expect(await screen.findByText("排队中")).toBeInTheDocument();
});

test("loads and renders append-only trace events for a task", async () => {
  const user = userEvent.setup();
  render(<AgentPage />);

  expect(await screen.findByText("agt_done")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "执行日志" }));

  expect(apiMock.api.agentTaskTrace).toHaveBeenCalledWith("agt_done");
  expect(await screen.findByText("tool_finished")).toBeInTheDocument();
  expect(screen.getAllByText("OpenClaw 未配置").length).toBeGreaterThan(0);
  expect(screen.getByText(/\"duration_ms\": 12/)).toBeInTheDocument();
});
