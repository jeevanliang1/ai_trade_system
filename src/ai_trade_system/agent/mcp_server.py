from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from ai_trade_system.agent.orchestrator import AgentOrchestrator
from ai_trade_system.agent.queue import AgentTaskQueue
from ai_trade_system.agent.store import AgentStore

WEEKLY_SCAN_DEFAULT_LIMIT = 10
WEEKLY_SCAN_DEFAULT_RESEARCH_LIMIT = 30


class AgentMcpServer:
    def __init__(
        self,
        store: AgentStore | None = None,
        orchestrator: AgentOrchestrator | None = None,
        queue: AgentTaskQueue | None = None,
    ):
        self.orchestrator = orchestrator or AgentOrchestrator(store=store)
        self.queue = queue or AgentTaskQueue(orchestrator=self.orchestrator)

    def handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        if method and method.startswith("notifications/"):
            return None
        request_id = message.get("id")
        try:
            if method == "initialize":
                return self._response(request_id, self._initialize_result())
            if method == "tools/list":
                return self._response(request_id, {"tools": self._tools()})
            if method == "tools/call":
                return self._response(request_id, self._call_tool(message.get("params", {})))
            return self._error(request_id, -32601, f"Unknown MCP method: {method}")
        except UnknownMcpTool as exc:
            return self._error(request_id, -32601, str(exc))
        except KeyError as exc:
            return self._error(request_id, -32004, str(exc))
        except Exception as exc:
            return self._error(request_id, -32000, str(exc))

    def serve_stdio(self) -> None:
        for line in sys.stdin:
            if not line.strip():
                continue
            response = self.handle_message(json.loads(line))
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)

    def _initialize_result(self) -> dict[str, Any]:
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "ai-trade-system-agent", "version": "0.1.0"},
        }

    def _tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "create_agent_task",
                "description": "Create and execute an audited ai_trade_system Agent task. Use this for Chinese natural-language trading-system requests, including 本周/这周股票扫描、股票分析结论、基本面研究、回测、风控、纸面交易和微信结果输出。For long OpenClaw/Weixin requests, set context.notify_on_completion=true and context.notification_channel='openclaw' so ai_trade_system returns a task id immediately and notifies OpenClaw after completion.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string"},
                        "source": {"type": "string", "default": "mcp"},
                        "context": {"type": "object"},
                    },
                    "required": ["prompt"],
                },
            },
            {
                "name": "get_weekly_scan_report",
                "description": "当用户说“这周/本周的股票扫描结果、股票扫描分析结论、周榜优质股票、输出给我、完成分享”等自然语言请求时调用。该工具会创建 ai_trade_system Agent 任务：读取或自动触发本周扫描，默认按科创板Top10、创业板Top10、综合非ST Top10继续做候选股票分析和微信可返回结论。",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {"type": "string", "default": "这周的股票扫描分析结论输出给我"},
                        "source": {"type": "string", "default": "weixin"},
                        "limit": {"type": "integer", "default": WEEKLY_SCAN_DEFAULT_LIMIT},
                        "research_limit": {"type": "integer", "default": WEEKLY_SCAN_DEFAULT_RESEARCH_LIMIT},
                        "auto_run_weekly_scan": {"type": "boolean", "default": True},
                        "notify_on_completion": {"type": "boolean", "default": True},
                        "reply_channel": {"type": "string"},
                        "reply_to": {"type": "string"},
                        "reply_account": {"type": "string"},
                        "session_id": {"type": "string"},
                        "session_key": {"type": "string"},
                    },
                },
            },
            {
                "name": "get_agent_task_status",
                "description": "Read a single Agent task by id.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
            },
            {
                "name": "get_agent_trace",
                "description": "Read append-only trace events for a single Agent task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
            },
            {
                "name": "list_agent_tasks",
                "description": "List recent Agent tasks.",
                "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
            },
            {
                "name": "approve_agent_action",
                "description": "Resolve a pending Agent confirmation.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}, "approval": {"type": "string", "default": "approved"}},
                    "required": ["task_id"],
                },
            },
            {
                "name": "list_agent_tools",
                "description": "List internal Agent tool registry entries and permission levels.",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

    def _call_tool(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if name == "create_agent_task":
            prompt = arguments["prompt"]
            source = arguments.get("source", "mcp")
            task, deduplicated, idempotency_key = self._submit_idempotent(
                prompt,
                source=source,
                context=arguments.get("context", {}),
            )
            return self._tool_result(
                {
                    "task": task.as_dict(),
                    "routing": {"delivery": {"deduplicated": deduplicated, "idempotency_key": idempotency_key}},
                }
            )
        if name == "get_weekly_scan_report":
            prompt = arguments.get("prompt") or "这周的股票扫描分析结论输出给我"
            context = {
                "week": "current",
                "limit": int(arguments.get("limit", WEEKLY_SCAN_DEFAULT_LIMIT)),
                "research_limit": int(arguments.get("research_limit", WEEKLY_SCAN_DEFAULT_RESEARCH_LIMIT)),
                "auto_run_weekly_scan": arguments.get("auto_run_weekly_scan", True) is not False,
                "notify_on_completion": arguments.get("notify_on_completion", True) is not False,
                "notification_channel": "openclaw",
                "source_workflow": "weekly_scan_report",
            }
            for key in ("reply_channel", "reply_to", "reply_account", "session_id", "session_key"):
                if arguments.get(key):
                    context[key] = arguments[key]
            task, deduplicated, idempotency_key = self._submit_idempotent(
                prompt,
                source=arguments.get("source", "weixin"),
                context=context,
            )
            return self._tool_result(
                {
                    "task": task.as_dict(),
                    "routing": {
                        "intent": "weekly_scan_report",
                        "delivery": {
                            "mode": "async_notify",
                            "notify_on_completion": context["notify_on_completion"],
                            "task_id": task.task_id,
                            "deduplicated": deduplicated,
                            "idempotency_key": idempotency_key,
                        },
                        "next": "poll get_agent_task_status; approve pending confirmations if required; inspect get_agent_trace on failure",
                    },
                }
            )
        if name == "get_agent_task_status":
            return self._tool_result({"task": self.orchestrator.get_task(arguments["task_id"]).as_dict()})
        if name == "get_agent_trace":
            task_id = arguments["task_id"]
            return self._tool_result({"task_id": task_id, "events": self.orchestrator.trace_task(task_id)})
        if name == "list_agent_tasks":
            limit = int(arguments.get("limit", 20))
            return self._tool_result({"tasks": [task.as_dict() for task in self.orchestrator.list_tasks(limit)]})
        if name == "approve_agent_action":
            task = self.queue.approve(arguments["task_id"], arguments.get("approval", "approved"))
            return self._tool_result({"task": task.as_dict()})
        if name == "list_agent_tools":
            return self._tool_result({"tools": self.orchestrator.list_tools()})
        raise UnknownMcpTool(name)

    def _submit_idempotent(self, prompt: str, *, source: str, context: dict[str, Any]) -> tuple[Any, bool, str]:
        task_context = dict(context or {})
        idempotency_key = str(task_context.get("idempotency_key") or self._derive_idempotency_key(prompt, source, task_context))
        task_context["idempotency_key"] = idempotency_key
        self.queue.cleanup_stale_tasks()
        existing = self._find_idempotent_task(idempotency_key)
        if existing is not None:
            return existing, True, idempotency_key
        return self.queue.submit(prompt, source=source, context=task_context), False, idempotency_key

    def _find_idempotent_task(self, idempotency_key: str) -> Any | None:
        store = getattr(self.orchestrator, "store", None)
        finder = getattr(store, "find_recent_task_by_idempotency_key", None)
        if not callable(finder):
            return None
        return finder(idempotency_key)

    def _derive_idempotency_key(self, prompt: str, source: str, context: dict[str, Any]) -> str:
        stable_context_keys = (
            "symbol",
            "exchange",
            "week",
            "limit",
            "research_limit",
            "source_workflow",
            "reply_channel",
            "reply_to",
            "reply_account",
            "session_id",
            "session_key",
            "tools",
        )
        stable_context = {key: context[key] for key in stable_context_keys if key in context}
        payload = {
            "source": source,
            "prompt": " ".join(str(prompt).split()),
            "context": stable_context,
        }
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        return f"agent:{digest[:24]}"

    def _tool_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
            "structuredContent": payload,
        }

    def _response(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def wait_for_idle(self, timeout: float = 5.0) -> bool:
        return self.queue.wait_for_idle(timeout)

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class UnknownMcpTool(Exception):
    def __init__(self, name: str | None):
        super().__init__(f"Unknown MCP tool: {name}")
