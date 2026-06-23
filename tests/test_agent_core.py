from __future__ import annotations

import json
from pathlib import Path

from ai_trade_system.agent.governance import AgentGovernanceService, AgentGovernanceStore, AgentPlannerPolicy, AgentSkill
from ai_trade_system.agent.orchestrator import AgentOrchestrator
from ai_trade_system.agent.store import AgentStore


class FakeSystemTools:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def run(self, tool_name: str, prompt: str, source: str, context: dict, previous_outputs: dict | None = None) -> dict:
        self.calls.append((tool_name, dict(context)))
        return {
            "status": "ok",
            "summary": f"{tool_name} completed for {context.get('symbol', 'unknown')}",
            "tool": tool_name,
            "previous": sorted((previous_outputs or {}).keys()),
        }


class FakePlanner:
    def __init__(self, tools: list[str]):
        self.tools = tools

    def plan(self, prompt: str, context: dict) -> list[str]:
        return self.tools


def test_research_task_records_internal_and_openclaw_steps(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_TRADE_OPENCLAW_RESEARCH_COMMAND", "")
    store = AgentStore(tmp_path / "agent")
    orchestrator = AgentOrchestrator(store=store)

    task = orchestrator.create_task(
        "帮我研究 000001 最近是否值得关注",
        source="weixin",
        context={"symbol": "000001", "exchange": "SZSE"},
    )

    assert task.status == "waiting_confirmation"
    assert task.source == "weixin"
    assert task.context["symbol"] == "000001"
    assert [step.tool_name for step in task.steps] == ["system.snapshot"]
    assert task.confirmations[0].tool_name == "research.fundamental"

    orchestrator.approve_task(task.task_id, "approved")
    resumed = orchestrator.run_task(task.task_id)

    assert resumed.status == "completed"
    assert [step.tool_name for step in resumed.steps] == ["system.snapshot", "research.fundamental", "agent.report"]
    openclaw_evidence = next(item for item in resumed.evidence if item["tool"] == "research.fundamental")
    assert "OpenClaw" in openclaw_evidence["summary"]
    assert resumed.report_path is not None
    report = json.loads((tmp_path / "agent" / resumed.report_path).read_text(encoding="utf-8"))
    assert report["task_id"] == task.task_id
    assert report["source"] == "weixin"
    assert report["symbol"] == "000001"
    assert report["tool_outputs"]["research.fundamental"]["status"] == "not_configured"


def test_live_trading_prompt_is_blocked_before_tools_run(tmp_path: Path):
    store = AgentStore(tmp_path / "agent")
    orchestrator = AgentOrchestrator(store=store)

    task = orchestrator.create_task("帮我实盘买入 000001 一万块", source="openclaw")

    assert task.status == "blocked"
    assert task.steps == []
    assert task.confirmations
    assert task.confirmations[0].code == "LIVE_TRADING_BLOCKED"
    assert "实盘" in task.confirmations[0].message
    assert "不能绕过" in task.result_summary


def test_agent_tools_are_listed_with_permission_levels(tmp_path: Path):
    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"))

    tools = orchestrator.list_tools()
    tools_by_name = {tool["name"]: tool for tool in tools}

    assert tools_by_name["system.snapshot"]["permission"] == "auto"
    assert tools_by_name["research.fundamental"]["permission"] == "confirm"
    assert tools_by_name["data.update"]["permission"] == "auto"
    assert tools_by_name["radar.scan"]["permission"] == "auto"
    assert tools_by_name["backtest.run"]["permission"] == "auto"
    assert tools_by_name["risk.evaluate"]["permission"] == "auto"
    assert tools_by_name["paper.run"]["permission"] == "auto"
    assert tools_by_name["automation.weekly_result"]["permission"] == "auto"
    assert tools_by_name["research.batch_fundamental"]["permission"] == "confirm"
    assert tools_by_name["share.weixin"]["permission"] == "auto"
    assert tools_by_name["agent.report"]["permission"] == "auto"


def test_context_requested_system_tools_execute_between_snapshot_and_report(tmp_path: Path):
    store = AgentStore(tmp_path / "agent")
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(store=store, system_tools=fake_tools)

    task = orchestrator.create_task(
        "请按指定工具执行 000001",
        source="openclaw",
        context={
            "symbol": "000001",
            "exchange": "SZSE",
            "tools": ["data.update", "radar.scan", "backtest.run", "risk.evaluate", "paper.run"],
        },
    )

    assert task.status == "completed"
    assert [step.tool_name for step in task.steps] == [
        "system.snapshot",
        "data.update",
        "radar.scan",
        "backtest.run",
        "risk.evaluate",
        "paper.run",
        "agent.report",
    ]
    assert [name for name, _ in fake_tools.calls] == ["data.update", "radar.scan", "backtest.run", "risk.evaluate", "paper.run"]
    assert task.evidence[-2]["tool"] == "paper.run"
    report = json.loads((tmp_path / "agent" / task.report_path).read_text(encoding="utf-8"))
    assert report["tool_outputs"]["data.update"]["summary"] == "data.update completed for 000001"
    assert report["tool_outputs"]["paper.run"]["previous"] == [
        "backtest.run",
        "data.update",
        "radar.scan",
        "risk.evaluate",
        "system.snapshot",
    ]


def test_agent_task_writes_append_only_trace_events(tmp_path: Path):
    store = AgentStore(tmp_path / "agent")
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(store=store, system_tools=fake_tools)

    task = orchestrator.create_task(
        "请按指定工具执行 000001",
        source="weixin",
        context={"symbol": "000001", "tools": ["risk.evaluate"]},
    )

    events = store.read_trace(task.task_id)
    event_types = [event["type"] for event in events]

    assert task.status == "completed"
    assert event_types == [
        "request_received",
        "plan_selected",
        "tool_started",
        "tool_finished",
        "tool_started",
        "tool_finished",
        "tool_started",
        "tool_finished",
        "task_completed",
    ]
    assert events[0]["event_id"] == "000001"
    assert events[0]["payload"]["source"] == "weixin"
    assert events[1]["payload"]["plan"] == ["system.snapshot", "risk.evaluate", "agent.report"]
    risk_finished = next(event for event in events if event["type"] == "tool_finished" and event["tool_name"] == "risk.evaluate")
    assert risk_finished["payload"]["output"]["summary"] == "risk.evaluate completed for 000001"
    assert risk_finished["payload"]["duration_ms"] >= 0
    assert (tmp_path / "agent" / "runs" / task.task_id / "events.jsonl").exists()


def test_agent_trace_records_confirmation_and_approval(tmp_path: Path):
    store = AgentStore(tmp_path / "agent")
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(store=store, system_tools=fake_tools)

    task = orchestrator.create_task(
        "请做外部研究 000001",
        source="weixin",
        context={"symbol": "000001", "tools": ["research.fundamental"]},
    )
    orchestrator.approve_task(task.task_id, "approved")
    resumed = orchestrator.run_task(task.task_id)

    events = store.read_trace(resumed.task_id)
    event_types = [event["type"] for event in events]

    assert "confirmation_requested" in event_types
    assert "approval_recorded" in event_types
    assert event_types[-1] == "task_completed"
    confirmation = next(event for event in events if event["type"] == "confirmation_requested")
    approval = next(event for event in events if event["type"] == "approval_recorded")
    assert confirmation["tool_name"] == "research.fundamental"
    assert approval["payload"]["approval"] == "approved"


def test_confirm_level_tool_pauses_and_rejected_approval_blocks_task(tmp_path: Path):
    store = AgentStore(tmp_path / "agent")
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(store=store, system_tools=fake_tools)

    task = orchestrator.create_task(
        "请做外部研究并扫描 000001",
        source="weixin",
        context={"symbol": "000001", "tools": ["research.fundamental", "radar.scan"]},
    )

    assert task.status == "waiting_confirmation"
    assert [step.tool_name for step in task.steps] == ["system.snapshot"]
    assert fake_tools.calls == []

    rejected = orchestrator.approve_task(task.task_id, "rejected")

    assert rejected.status == "blocked"
    assert rejected.confirmations[0].status == "rejected"
    assert store.get_task(task.task_id).status == "blocked"


def test_prompt_keywords_plan_system_tools(tmp_path: Path):
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"), system_tools=fake_tools)

    task = orchestrator.create_task(
        "更新 688981 行情后做信号雷达扫描、回测、风控评估和纸面模拟交易",
        source="weixin",
        context={"symbol": "688981", "exchange": "SSE"},
    )

    assert [step.tool_name for step in task.steps] == [
        "system.snapshot",
        "data.update",
        "radar.scan",
        "backtest.run",
        "risk.evaluate",
        "paper.run",
        "agent.report",
    ]


def test_prompt_keywords_plan_weekly_scan_research_and_share(tmp_path: Path):
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(store=AgentStore(tmp_path / "agent"), system_tools=fake_tools)

    task = orchestrator.create_task(
        "给我这周股票扫描结果并完成分享的最终结果",
        source="weixin",
        context={"limit": 3},
    )

    assert task.status == "waiting_confirmation"
    assert [step.tool_name for step in task.steps] == ["system.snapshot", "automation.weekly_result"]
    assert task.confirmations[0].tool_name == "research.batch_fundamental"

    orchestrator.approve_task(task.task_id, "approved")
    resumed = orchestrator.run_task(task.task_id)

    assert resumed.status == "completed"
    assert [step.tool_name for step in resumed.steps] == [
        "system.snapshot",
        "automation.weekly_result",
        "research.batch_fundamental",
        "share.weixin",
        "agent.report",
    ]
    assert [name for name, _ in fake_tools.calls] == ["automation.weekly_result", "research.batch_fundamental", "share.weixin"]


def test_agent_report_backfills_report_path_into_share_output(tmp_path: Path):
    class FakeShareTools:
        def run(self, tool_name: str, prompt: str, source: str, context: dict, previous_outputs: dict | None = None) -> dict:
            if tool_name == "share.weixin":
                return {
                    "status": "prepared",
                    "summary": "微信分享文本已准备：items=1。",
                    "delivery": "agent_response",
                    "target": "weixin",
                    "message": "微信摘要",
                    "item_count": 1,
                }
            return {"status": "ok", "summary": f"{tool_name} ok"}

    store = AgentStore(tmp_path / "agent")
    orchestrator = AgentOrchestrator(store=store, system_tools=FakeShareTools())

    task = orchestrator.create_task("请准备微信分享", source="weixin", context={"tools": ["share.weixin"]})

    assert task.status == "completed"
    assert task.report_path == f"reports/{task.task_id}.json"
    share_step = next(step for step in task.steps if step.tool_name == "share.weixin")
    assert f"完整报告：{task.report_path}" in share_step.output["message"]
    assert share_step.output["full_report_hint"] == task.report_path
    report = json.loads((tmp_path / "agent" / task.report_path).read_text(encoding="utf-8"))
    assert report["share_output"]["full_report_hint"] == task.report_path


def test_deepseek_planner_tools_are_normalized_before_execution(tmp_path: Path):
    fake_tools = FakeSystemTools()
    orchestrator = AgentOrchestrator(
        store=AgentStore(tmp_path / "agent"),
        system_tools=fake_tools,
        planner=FakePlanner(["made.up", "data.update", "radar.scan", "backtest.run", "risk.evaluate", "paper.run"]),
    )

    task = orchestrator.create_task("帮我完整分析 688981", source="weixin", context={"symbol": "688981", "exchange": "SSE"})

    assert task.status == "completed"
    assert [step.tool_name for step in task.steps] == [
        "system.snapshot",
        "data.update",
        "radar.scan",
        "backtest.run",
        "risk.evaluate",
        "paper.run",
        "agent.report",
    ]
    assert [name for name, _ in fake_tools.calls] == ["data.update", "radar.scan", "backtest.run", "risk.evaluate", "paper.run"]


def test_governance_skill_can_drive_real_agent_task_plan(tmp_path: Path):
    fake_tools = FakeSystemTools()
    governance_store = AgentGovernanceStore(tmp_path / "governance")
    governance_store.save_skill(
        AgentSkill(
            id="risk_first_review",
            title="先风控复核",
            description="按用户要求先做风险检查。",
            trigger_terms=["先风控", "风险复核"],
            steps=["risk.evaluate"],
            allowed_tools=["risk.evaluate"],
            required_confirmations=[],
            output_format="risk_report",
        )
    )
    orchestrator = AgentOrchestrator(
        store=AgentStore(tmp_path / "agent"),
        system_tools=fake_tools,
        governance=AgentGovernanceService(store=governance_store),
    )

    task = orchestrator.create_task("请先风控复核 000001", source="weixin", context={"symbol": "000001"})

    assert task.status == "completed"
    assert [step.tool_name for step in task.steps] == ["system.snapshot", "risk.evaluate", "agent.report"]
    assert [name for name, _ in fake_tools.calls] == ["risk.evaluate"]
    planner_evidence = next(item for item in task.evidence if item["tool"] == "agent.planner")
    assert planner_evidence["selected_skill"] == "risk_first_review"


def test_governance_policy_permissions_apply_to_real_agent_task(tmp_path: Path):
    fake_tools = FakeSystemTools()
    governance_store = AgentGovernanceStore(tmp_path / "governance")
    governance_store.save_skill(
        AgentSkill(
            id="share_review",
            title="分享复核",
            description="按治理策略先确认再准备分享。",
            trigger_terms=["分享复核", "确认分享"],
            steps=["share.weixin"],
            allowed_tools=["share.weixin"],
            required_confirmations=["share.weixin"],
            output_format="weixin_ready_report",
        )
    )
    governance_store.save_policy(AgentPlannerPolicy(tool_permissions={"share.weixin": "confirm"}))
    orchestrator = AgentOrchestrator(
        store=AgentStore(tmp_path / "agent"),
        system_tools=fake_tools,
        governance=AgentGovernanceService(store=governance_store),
    )

    task = orchestrator.create_task("请分享复核并确认分享 000001", source="weixin", context={"symbol": "000001"})

    assert task.status == "waiting_confirmation"
    assert [step.tool_name for step in task.steps] == ["system.snapshot"]
    assert task.confirmations[0].tool_name == "share.weixin"
    assert task.context["planner_tool_permissions"]["share.weixin"] == "confirm"

    orchestrator.approve_task(task.task_id, "approved")
    resumed = orchestrator.run_task(task.task_id)

    assert resumed.status == "completed"
    assert [name for name, _ in fake_tools.calls] == ["share.weixin"]


def test_store_lists_newest_task_first(tmp_path: Path):
    store = AgentStore(tmp_path / "agent")
    orchestrator = AgentOrchestrator(store=store)

    first = orchestrator.create_task("总结系统状态", source="frontend")
    second = orchestrator.create_task("研究 600000", source="cli", context={"symbol": "600000", "exchange": "SSE"})

    listed = store.list_tasks()

    assert [task.task_id for task in listed] == [second.task_id, first.task_id]
    assert store.get_task(first.task_id).prompt == "总结系统状态"
