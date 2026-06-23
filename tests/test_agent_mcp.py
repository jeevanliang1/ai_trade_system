from __future__ import annotations

from pathlib import Path
from time import monotonic, sleep

import pytest

from ai_trade_system.agent.mcp_server import AgentMcpServer
from ai_trade_system.agent.store import AgentStore


@pytest.fixture(autouse=True)
def _disable_local_openclaw_commands(monkeypatch):
    monkeypatch.setenv("AI_TRADE_OPENCLAW_RESEARCH_COMMAND", "")
    monkeypatch.setenv("AI_TRADE_OPENCLAW_NOTIFY_COMMAND", "")


def test_mcp_initialize_and_list_tools(tmp_path: Path):
    server = AgentMcpServer(store=AgentStore(tmp_path / "agent"))

    initialized = server.handle_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert initialized["id"] == 1
    assert initialized["result"]["serverInfo"]["name"] == "ai-trade-system-agent"

    tools = server.handle_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    tool_names = {tool["name"] for tool in tools["result"]["tools"]}

    assert {
        "create_agent_task",
        "get_weekly_scan_report",
        "get_agent_task_status",
        "get_agent_trace",
        "list_agent_tasks",
        "approve_agent_action",
        "list_agent_tools",
    } <= tool_names

    weekly_tool = next(tool for tool in tools["result"]["tools"] if tool["name"] == "get_weekly_scan_report")
    assert "这周" in weekly_tool["description"]
    assert "股票扫描" in weekly_tool["description"]
    properties = weekly_tool["inputSchema"]["properties"]
    assert properties["limit"]["default"] == 10
    assert properties["research_limit"]["default"] == 30


def test_mcp_create_and_read_agent_task(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_TRADE_OPENCLAW_RESEARCH_COMMAND", "")
    server = AgentMcpServer(store=AgentStore(tmp_path / "agent"))

    created = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "create_agent_task",
                "arguments": {
                    "prompt": "帮我研究 000001",
                    "source": "openclaw",
                    "context": {"symbol": "000001", "exchange": "SZSE"},
                },
            },
        }
    )
    task_payload = created["result"]["structuredContent"]["task"]
    assert task_payload["status"] in {"queued", "running", "waiting_confirmation"}
    assert task_payload["source"] == "openclaw"

    task_payload = _wait_for_mcp_status(server, task_payload["task_id"], {"waiting_confirmation"})
    assert task_payload["confirmations"][0]["tool_name"] == "research.fundamental"

    approved = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "approve_agent_action", "arguments": {"task_id": task_payload["task_id"]}},
        }
    )
    assert approved["result"]["structuredContent"]["task"]["status"] in {"queued", "running", "completed"}
    task_payload = _wait_for_mcp_status(server, task_payload["task_id"], {"completed"})

    fetched = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "get_agent_task_status", "arguments": {"task_id": task_payload["task_id"]}},
        }
    )

    assert fetched["result"]["structuredContent"]["task"]["task_id"] == task_payload["task_id"]

    trace = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {"name": "get_agent_trace", "arguments": {"task_id": task_payload["task_id"]}},
        }
    )

    assert trace["result"]["structuredContent"]["task_id"] == task_payload["task_id"]
    assert "approval_recorded" in [event["type"] for event in trace["result"]["structuredContent"]["events"]]


def test_mcp_create_agent_task_runs_requested_system_tools(tmp_path: Path):
    class FakeSystemTools:
        def run(self, tool_name: str, prompt: str, source: str, context: dict, previous_outputs: dict | None = None) -> dict:
            return {"status": "ok", "summary": f"{tool_name} ok"}

    from ai_trade_system.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"), system_tools=FakeSystemTools())
    server = AgentMcpServer(orchestrator=orchestrator)

    created = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "create_agent_task",
                "arguments": {
                    "prompt": "给 000001 跑一次雷达扫描",
                    "source": "openclaw",
                    "context": {"symbol": "000001", "exchange": "SZSE", "tools": ["radar.scan"]},
                },
            },
        }
    )

    task_payload = created["result"]["structuredContent"]["task"]
    task_payload = _wait_for_mcp_status(server, task_payload["task_id"], {"completed"})
    assert [step["tool_name"] for step in task_payload["steps"]] == ["system.snapshot", "radar.scan", "agent.report"]
    assert task_payload["evidence"][1]["tool"] == "radar.scan"


def test_mcp_weekly_scan_report_tool_creates_routed_agent_task(tmp_path: Path):
    class FakeSystemTools:
        def run(self, tool_name: str, prompt: str, source: str, context: dict, previous_outputs: dict | None = None) -> dict:
            if tool_name == "automation.weekly_result":
                return {
                    "status": "ok",
                    "summary": "周扫描结果读取完成",
                    "top_candidates": [{"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE"}],
                }
            return {"status": "ok", "summary": f"{tool_name} ok"}

    from ai_trade_system.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"), system_tools=FakeSystemTools())
    server = AgentMcpServer(orchestrator=orchestrator)

    created = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "get_weekly_scan_report",
                "arguments": {
                    "prompt": "这周的股票扫描分析结论输出给我",
                    "source": "weixin",
                    "limit": 3,
                },
            },
        }
    )

    task_payload = created["result"]["structuredContent"]["task"]
    task_payload = _wait_for_mcp_status(server, task_payload["task_id"], {"waiting_confirmation"})

    assert created["result"]["structuredContent"]["routing"]["intent"] == "weekly_scan_report"
    assert created["result"]["structuredContent"]["routing"]["delivery"]["mode"] == "async_notify"
    assert created["result"]["structuredContent"]["routing"]["delivery"]["notify_on_completion"] is True
    assert task_payload["source"] == "weixin"
    assert task_payload["context"]["week"] == "current"
    assert task_payload["context"]["auto_run_weekly_scan"] is True
    assert task_payload["context"]["notify_on_completion"] is True
    assert task_payload["context"]["limit"] == 3
    assert task_payload["confirmations"][0]["tool_name"] == "research.batch_fundamental"


def test_mcp_weekly_scan_report_uses_board_top10_defaults(tmp_path: Path):
    class FakeSystemTools:
        def run(self, tool_name: str, prompt: str, source: str, context: dict, previous_outputs: dict | None = None) -> dict:
            if tool_name == "automation.weekly_result":
                return {
                    "status": "ok",
                    "summary": "周扫描结果读取完成",
                    "top_candidates": [{"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE"}],
                    "board_top_counts": {"star": 10, "chinext": 10, "combined_non_st": 10},
                }
            return {"status": "ok", "summary": f"{tool_name} ok"}

    from ai_trade_system.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"), system_tools=FakeSystemTools())
    server = AgentMcpServer(orchestrator=orchestrator)

    created = server.handle_message(
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "get_weekly_scan_report",
                "arguments": {
                    "prompt": "把这周的最新扫描分析结果发给我",
                    "source": "weixin",
                },
            },
        }
    )

    task_payload = created["result"]["structuredContent"]["task"]
    task_payload = _wait_for_mcp_status(server, task_payload["task_id"], {"waiting_confirmation"})

    assert task_payload["context"]["limit"] == 10
    assert task_payload["context"]["research_limit"] == 30
    assert task_payload["context"]["source_workflow"] == "weekly_scan_report"
    assert task_payload["confirmations"][0]["tool_name"] == "research.batch_fundamental"


def test_mcp_weekly_scan_report_reuses_recent_duplicate_task(tmp_path: Path):
    class FakeSystemTools:
        def run(self, tool_name: str, prompt: str, source: str, context: dict, previous_outputs: dict | None = None) -> dict:
            if tool_name == "automation.weekly_result":
                return {
                    "status": "ok",
                    "summary": "周扫描结果读取完成",
                    "top_candidates": [{"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE"}],
                }
            return {"status": "ok", "summary": f"{tool_name} ok"}

    from ai_trade_system.agent.orchestrator import AgentOrchestrator

    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"), system_tools=FakeSystemTools())
    server = AgentMcpServer(orchestrator=orchestrator)
    message = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "get_weekly_scan_report",
            "arguments": {
                "prompt": "这周的股票扫描分析结论输出给我",
                "source": "weixin",
                "limit": 5,
                "reply_to": "wx_user",
            },
        },
    }

    first = server.handle_message(message)
    first_task = first["result"]["structuredContent"]["task"]
    duplicate = server.handle_message({**message, "id": 12})
    duplicate_payload = duplicate["result"]["structuredContent"]

    assert duplicate_payload["task"]["task_id"] == first_task["task_id"]
    assert duplicate_payload["routing"]["delivery"]["deduplicated"] is True
    assert duplicate_payload["routing"]["delivery"]["task_id"] == first_task["task_id"]
    assert "idempotency_key" in duplicate_payload["routing"]["delivery"]


def test_mcp_unknown_tool_returns_json_rpc_error(tmp_path: Path):
    server = AgentMcpServer(store=AgentStore(tmp_path / "agent"))

    response = server.handle_message(
        {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "missing_tool", "arguments": {}}}
    )

    assert response["id"] == 5
    assert response["error"]["code"] == -32601


def _wait_for_mcp_status(server: AgentMcpServer, task_id: str, statuses: set[str]) -> dict:
    deadline = monotonic() + 3
    latest: dict | None = None
    while monotonic() < deadline:
        server.wait_for_idle(timeout=0.2)
        response = server.handle_message(
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {"name": "get_agent_task_status", "arguments": {"task_id": task_id}},
            }
        )
        latest = response["result"]["structuredContent"]["task"]
        if latest["status"] in statuses:
            return latest
        sleep(0.05)
    raise AssertionError(f"Agent MCP task {task_id} did not reach {statuses}; latest={latest}")
