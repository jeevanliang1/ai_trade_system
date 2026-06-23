import { useEffect, useState } from "react";
import { Bot, CheckCircle2, RefreshCcw, ScrollText, Send, ShieldAlert } from "lucide-react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { ToolbarButton } from "../components/ToolbarButton";
import type { AgentTask, AgentTool, AgentTraceEvent } from "../types";

export function AgentPage() {
  const [prompt, setPrompt] = useState("帮我研究 000001 最近是否值得关注");
  const [source, setSource] = useState("frontend");
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [tools, setTools] = useState<AgentTool[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("等待Agent任务");
  const [traceByTask, setTraceByTask] = useState<Record<string, AgentTraceEvent[]>>({});
  const [traceErrors, setTraceErrors] = useState<Record<string, string>>({});
  const [expandedTraceTaskId, setExpandedTraceTaskId] = useState<string | null>(null);
  const [traceBusyTaskId, setTraceBusyTaskId] = useState<string | null>(null);

  async function loadAgentState() {
    const [toolPayload, taskPayload] = await Promise.all([api.agentTools(), api.agentTasks()]);
    return { tools: toolPayload.tools, tasks: taskPayload.tasks };
  }

  async function refresh() {
    const payload = await loadAgentState();
    setTools(payload.tools);
    setTasks(payload.tasks);
  }

  useEffect(() => {
    let mounted = true;
    async function refreshSafely() {
      try {
        const payload = await loadAgentState();
        if (!mounted) return;
        setTools(payload.tools);
        setTasks(payload.tasks);
      } catch (error) {
        if (mounted) setMessage(formatRequestError(error));
      }
    }
    void refreshSafely();
    const timer = window.setInterval(() => void refreshSafely(), 3000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  async function createTask() {
    const cleanPrompt = prompt.trim();
    if (!cleanPrompt) return;
    setBusy(true);
    setMessage("Agent任务执行中...");
    try {
      const response = await api.createAgentTask(cleanPrompt, source, inferredContext(cleanPrompt));
      setTasks((current) => [response.task, ...current.filter((task) => task.task_id !== response.task.task_id)]);
      setMessage(response.task.result_summary || `Agent任务已记录：${statusLabel(response.task.status)}`);
    } catch (error) {
      setMessage(formatRequestError(error));
    } finally {
      setBusy(false);
    }
  }

  async function approve(taskId: string, approval: string) {
    setBusy(true);
    try {
      const response = await api.approveAgentTask(taskId, approval);
      setTasks((current) => current.map((task) => (task.task_id === taskId ? response.task : task)));
      setMessage(`确认已记录：${approval}`);
    } catch (error) {
      setMessage(formatRequestError(error));
    } finally {
      setBusy(false);
    }
  }

  async function toggleTrace(taskId: string) {
    if (expandedTraceTaskId === taskId) {
      setExpandedTraceTaskId(null);
      return;
    }
    setExpandedTraceTaskId(taskId);
    if (traceByTask[taskId]) return;
    setTraceBusyTaskId(taskId);
    try {
      const payload = await api.agentTaskTrace(taskId);
      setTraceByTask((current) => ({ ...current, [taskId]: payload.events }));
      setTraceErrors((current) => {
        const next = { ...current };
        delete next[taskId];
        return next;
      });
    } catch (error) {
      setTraceErrors((current) => ({ ...current, [taskId]: formatRequestError(error) }));
    } finally {
      setTraceBusyTaskId(null);
    }
  }

  return (
    <div className="agent-page">
      <section className="panel agent-command-panel">
        <div className="panel-title">AI指挥台</div>
        <label className="field">
          <span>任务指令</span>
          <textarea value={prompt} onChange={(event) => setPrompt(event.currentTarget.value)} rows={5} />
        </label>
        <label className="field">
          <span>来源</span>
          <select value={source} onChange={(event) => setSource(event.currentTarget.value)}>
            <option value="frontend">frontend</option>
            <option value="cli">cli</option>
            <option value="mcp">mcp</option>
            <option value="openclaw">openclaw</option>
            <option value="weixin">weixin</option>
          </select>
        </label>
        <div className="toolbar-row">
          <ToolbarButton variant="primary" icon={<Send size={15} />} onClick={createTask} disabled={busy}>
            创建Agent任务
          </ToolbarButton>
          <ToolbarButton icon={<RefreshCcw size={15} />} onClick={() => void refresh()} disabled={busy}>
            刷新状态
          </ToolbarButton>
        </div>
        <p className="muted-copy">{message}</p>
        <div className="tool-list">
          {tools.map((tool) => (
            <span className={`tool-pill permission-${tool.permission}`} key={tool.name}>
              {tool.name} · {tool.permission}
            </span>
          ))}
        </div>
      </section>

      <section className="agent-task-column">
        {tasks.length ? (
          tasks.map((task) => (
            <AgentTaskCard
              key={task.task_id}
              task={task}
              onApprove={approve}
              busy={busy}
              traceEvents={traceByTask[task.task_id] ?? []}
              traceError={traceErrors[task.task_id]}
              traceOpen={expandedTraceTaskId === task.task_id}
              traceBusy={traceBusyTaskId === task.task_id}
              onToggleTrace={toggleTrace}
            />
          ))
        ) : (
          <EmptyTasks />
        )}
      </section>
    </div>
  );
}

function AgentTaskCard({
  task,
  onApprove,
  busy,
  traceEvents,
  traceError,
  traceOpen,
  traceBusy,
  onToggleTrace
}: {
  task: AgentTask;
  onApprove: (taskId: string, approval: string) => void;
  busy: boolean;
  traceEvents: AgentTraceEvent[];
  traceError?: string;
  traceOpen: boolean;
  traceBusy: boolean;
  onToggleTrace: (taskId: string) => void;
}) {
  return (
    <article className={`panel agent-task-card status-${task.status}`}>
      <header>
        <div>
          <strong>{task.task_id}</strong>
          <span>{task.source}</span>
        </div>
        <span className="task-status">{statusLabel(task.status)}</span>
      </header>
      <p className="task-prompt">{task.prompt}</p>
      {task.result_summary ? <p className="task-summary">{task.result_summary}</p> : null}
      <div className="task-meta">
        {task.report_path ? <span>{task.report_path}</span> : null}
        <span>{task.updated_at}</span>
      </div>
      <div className="toolbar-row task-actions">
        <ToolbarButton icon={<ScrollText size={15} />} onClick={() => onToggleTrace(task.task_id)} disabled={traceBusy}>
          执行日志
        </ToolbarButton>
      </div>
      <div className="agent-timeline">
        {task.steps.map((step) => (
          <div className={`agent-step status-${step.status}`} key={`${task.task_id}-${step.tool_name}-${step.title}`}>
            {step.status === "failed" ? <ShieldAlert size={14} /> : <CheckCircle2 size={14} />}
            <div>
              <strong>{step.tool_name}</strong>
              <span>{step.status}{step.summary ? ` · ${step.summary}` : ""}</span>
            </div>
          </div>
        ))}
      </div>
      {task.confirmations.length ? (
        <div className="confirmation-list">
          {task.confirmations.map((confirmation) => (
            <div className="confirmation-item" key={confirmation.code}>
              <ShieldAlert size={15} />
              <div>
                <strong>{confirmation.code}</strong>
                <span>{confirmation.tool_name ? `${confirmation.tool_name} · ${confirmation.message}` : confirmation.message}</span>
              </div>
              {confirmation.status === "pending" ? (
                <>
                  <ToolbarButton onClick={() => onApprove(task.task_id, "approved")} disabled={busy}>
                    确认
                  </ToolbarButton>
                  <ToolbarButton onClick={() => onApprove(task.task_id, "rejected")} disabled={busy}>
                    拒绝
                  </ToolbarButton>
                </>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}
      {task.evidence.length ? (
        <div className="agent-evidence">
          {task.evidence.map((item, index) => (
            <span key={`${task.task_id}-evidence-${index}`}>{String(item.summary ?? item.tool ?? "-")}</span>
          ))}
        </div>
      ) : null}
      {traceOpen ? <AgentTracePanel taskId={task.task_id} events={traceEvents} error={traceError} busy={traceBusy} /> : null}
    </article>
  );
}

function AgentTracePanel({ taskId, events, error, busy }: { taskId: string; events: AgentTraceEvent[]; error?: string; busy: boolean }) {
  if (busy) {
    return <div className="agent-trace-panel">执行日志加载中...</div>;
  }
  if (error) {
    return <div className="agent-trace-panel trace-error">{error}</div>;
  }
  return (
    <div className="agent-trace-panel" aria-label={`${taskId} 执行日志`}>
      {events.length ? (
        events.map((event) => (
          <div className="trace-event" key={`${event.task_id}-${event.event_id}`}>
            <div className="trace-event-header">
              <strong>{event.type}</strong>
              <span>{event.tool_name ?? "task"} · {event.status ?? "-"}</span>
              <span>{event.created_at}</span>
            </div>
            {event.summary ? <p>{event.summary}</p> : null}
            <pre>{JSON.stringify(event.payload, null, 2)}</pre>
          </div>
        ))
      ) : (
        <p className="muted-copy">暂无执行日志。</p>
      )}
    </div>
  );
}

function EmptyTasks() {
  return (
    <section className="panel empty-agent-state">
      <Bot size={24} />
      <p>还没有Agent任务。来自前端、CLI、MCP、OpenClaw 或微信的任务都会进入这里。</p>
    </section>
  );
}

function inferredContext(prompt: string): Record<string, unknown> {
  const symbol = prompt.match(/\d{6}/)?.[0];
  return symbol ? { symbol } : {};
}

function statusLabel(status: string): string {
  return {
    pending: "待执行",
    queued: "排队中",
    running: "执行中",
    waiting_confirmation: "等待确认",
    completed: "已完成",
    blocked: "已阻断",
    failed: "失败"
  }[status] ?? status;
}
