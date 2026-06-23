from __future__ import annotations

from time import perf_counter
from typing import Any
from uuid import uuid4

from ai_trade_system.agent.governance import AgentGovernanceService
from ai_trade_system.agent.models import AgentConfirmation, AgentStep, AgentTask, utc_now
from ai_trade_system.agent.openclaw import OpenClawConnector
from ai_trade_system.agent.planner import AgentPlanner, normalize_agent_tools
from ai_trade_system.agent.store import AgentStore
from ai_trade_system.agent.system_tools import AgentSystemToolExecutor
from ai_trade_system.agent.tools import (
    AGENT_REPORT_TOOL,
    SYSTEM_SNAPSHOT_TOOL,
    agent_tool_spec,
    prompt_planned_tools,
    requested_agent_tools,
    list_agent_tools,
    system_snapshot,
)


class AgentOrchestrator:
    def __init__(
        self,
        store: AgentStore | None = None,
        openclaw: OpenClawConnector | None = None,
        system_tools: Any | None = None,
        planner: Any | None = None,
        governance: AgentGovernanceService | None = None,
    ):
        self.store = store or AgentStore()
        self.openclaw = openclaw or OpenClawConnector()
        self.system_tools = system_tools or AgentSystemToolExecutor(openclaw=self.openclaw)
        self.planner = planner if planner is not None else AgentPlanner()
        self.governance = governance or AgentGovernanceService()

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.as_dict() for tool in list_agent_tools()]

    def create_task(
        self,
        prompt: str,
        *,
        source: str = "frontend",
        context: dict[str, Any] | None = None,
        auto_run: bool = True,
    ) -> AgentTask:
        task = AgentTask(
            task_id=self._new_task_id(),
            source=source,
            prompt=prompt,
            status="pending",
            context=self._normalize_context(prompt, context or {}),
        )
        self._trace(
            task,
            "request_received",
            status=task.status,
            summary=f"收到来自 {source} 的 Agent 请求。",
            payload={"source": source, "prompt": prompt, "context": task.context},
        )
        if self._is_live_trading_request(prompt):
            task.status = "blocked"
            task.confirmations.append(
                AgentConfirmation(
                    code="LIVE_TRADING_BLOCKED",
                    message="检测到实盘或下单意图；当前系统不能绕过风控、纸面交易和未来实盘前置规则。",
                    risk_level="blocked",
                    status="blocked",
                    tool_name=None,
                )
            )
            task.result_summary = "任务已阻断：AI Agent 不能绕过实盘前置规则或直接发出实盘交易指令。"
            self._trace(task, "task_blocked", status=task.status, summary=task.result_summary, payload={"reason": "live_trading_blocked"})
            task.touch()
            return self.store.save_task(task)

        plan_preview = self._governance_preview(prompt, task.context)
        if plan_preview.get("status") == "blocked":
            task.status = "blocked"
            reason = plan_preview.get("blocked_reason") or "Planner policy blocked this task."
            task.confirmations.append(
                AgentConfirmation(
                    code="PLANNER_POLICY_BLOCKED",
                    message=str(reason),
                    risk_level="blocked",
                    status="blocked",
                    tool_name=None,
                )
            )
            task.result_summary = f"任务已阻断：{reason}"
            self._trace(task, "task_blocked", status=task.status, summary=task.result_summary, payload={"reason": reason, "preview": plan_preview})
            task.touch()
            return self.store.save_task(task)

        self._store_planner_permissions(task.context, plan_preview)
        task.plan = self._plan(prompt, task.context, plan_preview)
        self._record_planner_evidence(task, plan_preview)
        self._trace(
            task,
            "plan_selected",
            status=task.status,
            summary=f"已生成 Agent 执行计划：{', '.join(task.plan)}",
            payload={
                "plan": task.plan,
                "preview": plan_preview,
                "planner_tool_permissions": task.context.get("planner_tool_permissions", {}),
                "ignored_tools": task.context.get("ignored_tools", []),
            },
        )
        self.store.save_task(task)
        if not auto_run:
            return task
        return self.run_task(task.task_id)

    def run_task(self, task_id: str) -> AgentTask:
        task = self.store.get_task(task_id)
        if task.status in {"completed", "failed", "blocked"}:
            return task
        if self._has_pending_confirmation(task):
            task.status = "waiting_confirmation"
            task.touch()
            return self.store.save_task(task)
        task.status = "running"
        self.store.save_task(task)
        try:
            outputs: dict[str, dict[str, Any]] = self._completed_outputs(task)
            ignored_tools = task.context.get("ignored_tools", [])
            if ignored_tools and not any(item.get("tool") == "agent.planner" for item in task.evidence):
                task.evidence.append(
                    {
                        "tool": "agent.planner",
                        "status": "ignored",
                        "summary": f"已忽略未知 Agent 工具：{', '.join(ignored_tools)}",
                    }
                )
                self.store.save_task(task)
            for tool_name in task.plan:
                if tool_name in outputs:
                    continue
                if self._tool_permission(task, tool_name) == "blocked":
                    self._add_tool_block(task, tool_name)
                    task.status = "blocked"
                    task.result_summary = f"任务已阻断：Planner policy 禁止执行 {tool_name}。"
                    self._trace(task, "task_blocked", tool_name=tool_name, status=task.status, summary=task.result_summary)
                    task.touch()
                    return self.store.save_task(task)
                if self._confirmation_required(task, tool_name):
                    self._add_tool_confirmation(task, tool_name)
                    task.status = "waiting_confirmation"
                    task.result_summary = f"等待确认后继续执行 {tool_name}。"
                    task.touch()
                    return self.store.save_task(task)
                if tool_name == SYSTEM_SNAPSHOT_TOOL:
                    outputs[tool_name] = self._run_step(
                        task,
                        tool_name,
                        "读取系统边界和当前上下文",
                        lambda: system_snapshot(task.prompt, task.source, task.context),
                    )
                elif tool_name == AGENT_REPORT_TOOL:
                    outputs[tool_name] = self._run_step(
                        task,
                        tool_name,
                        "生成并持久化 Agent 报告",
                        lambda: self._write_report(task, outputs),
                    )
                else:
                    outputs[tool_name] = self._run_step(
                        task,
                        tool_name,
                        self._tool_title(tool_name),
                        lambda tool_name=tool_name: self.system_tools.run(tool_name, task.prompt, task.source, task.context, outputs),
                    )
            task.status = "failed" if self._has_failed_tool(outputs) else "completed"
            task.result_summary = self._summary(task, outputs)
        except Exception as exc:
            task.status = "failed"
            task.result_summary = str(exc)
            self._trace(task, "task_failed", status=task.status, summary=task.result_summary, payload={"error": str(exc)})
        else:
            event_type = "task_failed" if task.status == "failed" else "task_completed"
            self._trace(
                task,
                event_type,
                status=task.status,
                summary=task.result_summary,
                payload={"report_path": task.report_path, "plan": task.plan},
            )
        task.touch()
        return self.store.save_task(task)

    def get_task(self, task_id: str) -> AgentTask:
        return self.store.get_task(task_id)

    def list_tasks(self, limit: int = 50) -> list[AgentTask]:
        return self.store.list_tasks(limit)

    def trace_task(self, task_id: str) -> list[dict[str, Any]]:
        self.store.get_task(task_id)
        return self.store.read_trace(task_id)

    def approve_task(self, task_id: str, approval: str = "approved") -> AgentTask:
        task = self.store.get_task(task_id)
        for confirmation in task.confirmations:
            if confirmation.status == "pending":
                confirmation.status = approval
                confirmation.resolved_at = utc_now()
        if approval == "approved" and task.status == "waiting_confirmation":
            task.status = "pending"
            task.result_summary = "确认已通过，等待继续执行。"
        elif approval != "approved":
            task.status = "blocked"
            task.result_summary = "任务已阻断：用户未批准需要确认的 Agent 动作。"
        self._trace(
            task,
            "approval_recorded",
            status=task.status,
            summary=task.result_summary,
            payload={"approval": approval, "confirmations": [confirmation.as_dict() for confirmation in task.confirmations]},
        )
        if task.status == "blocked":
            self._trace(task, "task_blocked", status=task.status, summary=task.result_summary, payload={"approval": approval})
        task.touch()
        return self.store.save_task(task)

    def notify_task_update(self, task: AgentTask) -> dict[str, Any]:
        if not self._should_notify_task(task):
            return {"status": "skipped", "summary": "任务未配置 OpenClaw 完成通知。"}
        result = self.openclaw.notify_task(task)
        if result.get("status") == "ok":
            event_type = "task_notification_sent"
        elif result.get("status") == "not_configured":
            event_type = "task_notification_skipped"
        else:
            event_type = "task_notification_failed"
        self._trace(
            task,
            event_type,
            status=result.get("status"),
            summary=str(result.get("summary", "")),
            payload={"notification": result},
        )
        return result

    def _run_step(self, task: AgentTask, tool_name: str, title: str, runner) -> dict[str, Any]:
        started = perf_counter()
        self._trace(task, "tool_started", tool_name=tool_name, status="running", summary=title, payload={"title": title})
        step = AgentStep(tool_name=tool_name, title=title, status="running", started_at=utc_now())
        task.steps.append(step)
        self.store.save_task(task)
        try:
            output = runner()
        except Exception as exc:
            duration_ms = int((perf_counter() - started) * 1000)
            self._trace(
                task,
                "tool_failed",
                tool_name=tool_name,
                status="failed",
                summary=str(exc),
                payload={"title": title, "error": str(exc), "duration_ms": duration_ms},
            )
            raise
        step.output = output
        step.summary = str(output.get("summary", output.get("status", "")))
        step.status = "failed" if output.get("status") == "failed" else "completed"
        step.finished_at = utc_now()
        task.evidence.append({"tool": tool_name, "summary": step.summary, "status": output.get("status", "ok")})
        duration_ms = int((perf_counter() - started) * 1000)
        self._trace(
            task,
            "tool_failed" if step.status == "failed" else "tool_finished",
            tool_name=tool_name,
            status=step.status,
            summary=step.summary,
            payload={"title": title, "output": output, "duration_ms": duration_ms},
        )
        task.touch()
        self.store.save_task(task)
        return output

    def _write_report(self, task: AgentTask, tool_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        snapshot = tool_outputs.get(SYSTEM_SNAPSHOT_TOOL, {})
        fundamental = tool_outputs.get("research.fundamental") or {"status": "not_requested", "summary": "本任务未请求外部研究。", "sources": []}
        weekly_result = tool_outputs.get("automation.weekly_result") or {"status": "not_requested", "summary": "本任务未读取周扫描结果。"}
        batch_research = tool_outputs.get("research.batch_fundamental") or {"status": "not_requested", "summary": "本任务未请求批量外部研究。", "items": []}
        share_output = tool_outputs.get("share.weixin") or {"status": "not_requested", "summary": "本任务未准备微信分享文本。"}
        predicted_report_path = f"reports/{task.task_id}.json"
        self._backfill_share_report_hint(share_output, predicted_report_path)
        payload = {
            "task_id": task.task_id,
            "source": task.source,
            "prompt": task.prompt,
            "symbol": task.context.get("symbol"),
            "exchange": task.context.get("exchange"),
            "system_snapshot": snapshot,
            "external_research": fundamental,
            "weekly_result": weekly_result,
            "batch_research": batch_research,
            "share_output": share_output,
            "tool_outputs": tool_outputs,
            "risk_boundary": snapshot.get("risk_boundary", "AI Agent 不能绕过风控、纸面交易和未来实盘前置规则。"),
            "next_steps": ["在前端 AI指挥台复核证据链", "需要外部资料时确认 OpenClaw connector 状态后重跑任务"],
            "created_at": utc_now(),
        }
        task.report_path = self.store.write_report(task, payload)
        return {"status": "ok", "summary": f"Agent 报告已保存：{task.report_path}", "report_path": task.report_path}

    def _backfill_share_report_hint(self, share_output: dict[str, Any], report_path: str) -> None:
        if share_output.get("status") == "not_requested":
            return
        message = str(share_output.get("message") or "").strip()
        if not message:
            return
        share_output["full_report_hint"] = share_output.get("full_report_hint") or report_path
        if report_path not in message:
            message = f"{message}\n\n完整报告：{report_path}"
            share_output["message"] = message
        share_output["message_chars"] = len(str(share_output.get("message") or ""))

    def _summary(self, task: AgentTask, tool_outputs: dict[str, dict[str, Any]]) -> str:
        snapshot = tool_outputs.get(SYSTEM_SNAPSHOT_TOOL, {})
        symbol = task.context.get("symbol") or snapshot.get("symbol") or "未指定"
        failed = [name for name, output in tool_outputs.items() if output.get("status") == "failed"]
        if failed:
            return f"{symbol} Agent 任务完成但存在失败工具：{', '.join(failed)}。"
        if "share.weixin" in tool_outputs:
            item_count = tool_outputs["share.weixin"].get("item_count", 0)
            return f"{symbol} Agent 任务完成；已准备微信分享结果，包含 {item_count} 个候选。"
        executed = [name for name in task.plan if name not in {SYSTEM_SNAPSHOT_TOOL, AGENT_REPORT_TOOL}]
        return f"{symbol} Agent 任务完成；已执行 {len(executed)} 个系统工具并生成可审计报告。"

    def _plan(self, prompt: str, context: dict[str, Any], preview: dict[str, Any] | None = None) -> list[str]:
        requested, ignored = requested_agent_tools(context)
        if ignored:
            context["ignored_tools"] = ignored
        if requested:
            system_tools = requested
        else:
            governance_tools = self._preview_tools(preview)
            if governance_tools:
                system_tools = governance_tools
            else:
                planned = normalize_agent_tools(self.planner.plan(prompt, context)) if self.planner else []
                system_tools = planned or prompt_planned_tools(prompt)
        return [SYSTEM_SNAPSHOT_TOOL, *system_tools, AGENT_REPORT_TOOL]

    def _governance_preview(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        try:
            return self.governance.preview_plan(prompt, context) if self.governance else {}
        except Exception as exc:
            return {
                "status": "failed",
                "intent": "planner_policy_unavailable",
                "selected_skill": None,
                "matched_memories": [],
                "steps": [],
                "stop_conditions": [],
                "final_output": "agent_report",
                "blocked_reason": None,
                "ignored_tools": [],
                "error": str(exc),
            }

    def _preview_tools(self, preview: dict[str, Any] | None) -> list[str]:
        if not preview or preview.get("status") != "ok":
            return []
        return normalize_agent_tools([step.get("tool") for step in preview.get("steps", [])])

    def _store_planner_permissions(self, context: dict[str, Any], preview: dict[str, Any]) -> None:
        permissions = {
            str(step.get("tool")): str(step.get("permission"))
            for step in preview.get("steps", [])
            if step.get("tool") and step.get("permission")
        }
        if permissions:
            context["planner_tool_permissions"] = permissions

    def _record_planner_evidence(self, task: AgentTask, preview: dict[str, Any]) -> None:
        selected_skill = preview.get("selected_skill") or {}
        matched_memories = preview.get("matched_memories") or []
        ignored = preview.get("ignored_tools") or []
        if not (selected_skill or matched_memories or ignored or preview.get("error")):
            return
        selected_skill_id = selected_skill.get("id") if isinstance(selected_skill, dict) else None
        matched_memory_ids = [memory.get("id") for memory in matched_memories if isinstance(memory, dict) and memory.get("id")]
        step_tools = [step.get("tool") for step in preview.get("steps", []) if step.get("tool")]
        if preview.get("error"):
            summary = f"Planner policy 暂不可用，已回退到默认规划：{preview['error']}"
        elif selected_skill_id:
            summary = f"Planner policy 已选择技能 {selected_skill_id}，计划执行 {len(step_tools)} 个工具。"
        else:
            summary = f"Planner policy 已匹配 {len(matched_memory_ids)} 条记忆，计划执行 {len(step_tools)} 个工具。"
        task.evidence.append(
            {
                "tool": "agent.planner",
                "status": preview.get("status", "ok"),
                "summary": summary,
                "intent": preview.get("intent"),
                "selected_skill": selected_skill_id,
                "matched_memories": matched_memory_ids,
                "planned_tools": step_tools,
                "ignored_tools": ignored,
            }
        )

    def _tool_title(self, tool_name: str) -> str:
        return {
            "data.update": "维护本地行情数据",
            "research.fundamental": "请求 OpenClaw 基本面和信息面研究",
            "automation.weekly_result": "读取周度自动扫描结果",
            "research.batch_fundamental": "批量请求 OpenClaw 基本面和信息面研究",
            "radar.scan": "运行信号雷达扫描",
            "backtest.run": "运行本地回测",
            "risk.evaluate": "执行风控评估",
            "paper.run": "运行纸面交易回放",
            "share.weixin": "准备微信分享结果",
        }.get(tool_name, f"执行 {tool_name}")

    def _has_failed_tool(self, outputs: dict[str, dict[str, Any]]) -> bool:
        return any(name != AGENT_REPORT_TOOL and output.get("status") == "failed" for name, output in outputs.items())

    def _completed_outputs(self, task: AgentTask) -> dict[str, dict[str, Any]]:
        return {step.tool_name: step.output for step in task.steps if step.status == "completed"}

    def _confirmation_required(self, task: AgentTask, tool_name: str) -> bool:
        permission = self._tool_permission(task, tool_name)
        if permission != "confirm":
            return False
        return not any(item.tool_name == tool_name and item.status == "approved" for item in task.confirmations)

    def _tool_permission(self, task: AgentTask, tool_name: str) -> str:
        policy_permissions = task.context.get("planner_tool_permissions", {})
        if isinstance(policy_permissions, dict) and isinstance(policy_permissions.get(tool_name), str):
            return policy_permissions[tool_name]
        spec = agent_tool_spec(tool_name)
        return spec.permission if spec else "auto"

    def _has_pending_confirmation(self, task: AgentTask) -> bool:
        return any(item.status == "pending" for item in task.confirmations)

    def _add_tool_confirmation(self, task: AgentTask, tool_name: str) -> None:
        if any(item.tool_name == tool_name and item.status == "pending" for item in task.confirmations):
            return
        confirmation = AgentConfirmation(
            code="TOOL_CONFIRMATION_REQUIRED",
            message=f"工具 {tool_name} 需要确认后才能继续执行。",
            risk_level="high",
            status="pending",
            tool_name=tool_name,
        )
        task.confirmations.append(confirmation)
        self._trace(
            task,
            "confirmation_requested",
            tool_name=tool_name,
            status="pending",
            summary=confirmation.message,
            payload={"confirmation": confirmation.as_dict()},
        )

    def _add_tool_block(self, task: AgentTask, tool_name: str) -> None:
        if any(item.tool_name == tool_name and item.status == "blocked" for item in task.confirmations):
            return
        task.confirmations.append(
            AgentConfirmation(
                code="TOOL_BLOCKED_BY_PLANNER_POLICY",
                message=f"Planner policy 禁止执行工具 {tool_name}。",
                risk_level="blocked",
                status="blocked",
                tool_name=tool_name,
            )
        )

    def _trace(
        self,
        task: AgentTask,
        event_type: str,
        *,
        tool_name: str | None = None,
        status: str | None = None,
        summary: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.store.append_trace_event(
                task.task_id,
                event_type,
                tool_name=tool_name,
                status=status,
                summary=summary,
                payload=payload or {},
            )
        except Exception:
            return

    def _should_notify_task(self, task: AgentTask) -> bool:
        if task.status not in {"completed", "failed", "blocked", "waiting_confirmation"}:
            return False
        if task.context.get("notify_on_completion") is False:
            return False
        return (
            task.context.get("notify_on_completion") is True
            or task.context.get("notification_channel") == "openclaw"
        )

    def _normalize_context(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(context)
        normalized.setdefault("symbol", self._symbol_from_prompt(prompt))
        return {key: value for key, value in normalized.items() if value is not None}

    def _symbol_from_prompt(self, prompt: str) -> str | None:
        digits = "".join(char if char.isdigit() else " " for char in prompt).split()
        return next((token for token in digits if len(token) == 6), None)

    def _is_live_trading_request(self, prompt: str) -> bool:
        return any(term in prompt for term in ("实盘", "下单", "真实交易", "券商委托", "委托买入", "委托卖出"))

    def _new_task_id(self) -> str:
        return f"agt_{uuid4().hex[:12]}"
