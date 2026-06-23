from __future__ import annotations

from pathlib import Path

from ai_trade_system.agent.governance import (
    AgentGovernanceService,
    AgentGovernanceStore,
    AgentMemory,
    AgentPlannerPolicy,
    AgentSkill,
)


def test_governance_store_seeds_default_memory_skill_and_policy(tmp_path: Path):
    store = AgentGovernanceStore(tmp_path / "agent")

    memories = store.list_memories()
    skills = store.list_skills()
    policy = store.load_policy()

    assert any(memory.id == "mem_weekly_scan_reuse" for memory in memories)
    weekly_skill = next(skill for skill in skills if skill.id == "weekly_scan_share")
    assert weekly_skill.steps == ["automation.weekly_result", "research.batch_fundamental", "share.weixin"]
    assert "实盘" in policy.blocked_intents
    assert policy.tool_permissions["research.batch_fundamental"] == "confirm"


def test_governance_store_persists_memory_skill_and_policy_updates(tmp_path: Path):
    store = AgentGovernanceStore(tmp_path / "agent")
    memory = store.save_memory(
        AgentMemory(
            id="mem_user_focus",
            type="preference",
            scope="agent",
            title="偏好周榜前三",
            content="用户默认只想看周榜前三名。",
            tags=["weekly", "preference"],
            source="user",
            confidence="high",
        )
    )
    skill = store.save_skill(
        AgentSkill(
            id="single_stock_deep_research",
            title="单股深度研究",
            description="对单只股票做外部研究和风险复核。",
            trigger_terms=["深度研究", "单股"],
            steps=["research.fundamental", "risk.evaluate"],
            allowed_tools=["research.fundamental", "risk.evaluate"],
            required_confirmations=["research.fundamental"],
            output_format="research_report",
        )
    )
    store.save_policy(AgentPlannerPolicy(max_steps=5, blocked_intents=["实盘"], tool_permissions={"research.fundamental": "confirm"}))

    reloaded = AgentGovernanceStore(tmp_path / "agent")

    assert reloaded.get_memory(memory.id).title == "偏好周榜前三"
    assert reloaded.get_skill(skill.id).steps == ["research.fundamental", "risk.evaluate"]
    assert reloaded.load_policy().max_steps == 5


def test_plan_preview_selects_weekly_scan_skill_with_memory_and_confirm_step(tmp_path: Path):
    service = AgentGovernanceService(store=AgentGovernanceStore(tmp_path / "agent"))

    preview = service.preview_plan("这周的股票扫描分析结论输出给我", {"source": "weixin"})

    assert preview["intent"] == "weekly_scan_share"
    assert preview["selected_skill"]["id"] == "weekly_scan_share"
    assert [step["tool"] for step in preview["steps"]] == [
        "automation.weekly_result",
        "research.batch_fundamental",
        "share.weixin",
    ]
    assert preview["steps"][1]["permission"] == "confirm"
    assert any(memory["id"] == "mem_weekly_scan_reuse" for memory in preview["matched_memories"])
    assert "live_trading_blocked" in preview["stop_conditions"]


def test_plan_preview_blocks_live_trading_intent(tmp_path: Path):
    service = AgentGovernanceService(store=AgentGovernanceStore(tmp_path / "agent"))

    preview = service.preview_plan("帮我实盘买入 000001", {"source": "weixin"})

    assert preview["status"] == "blocked"
    assert preview["intent"] == "blocked_live_trading"
    assert preview["steps"] == []
    assert "实盘" in preview["blocked_reason"]
