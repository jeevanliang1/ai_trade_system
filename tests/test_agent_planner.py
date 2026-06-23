from __future__ import annotations

from ai_trade_system.agent.planner import AgentPlanner


class ExplodingClient:
    def chat_json(self, **kwargs):
        raise AssertionError("DeepSeek planner should be disabled when provider is not deepseek")


def test_agent_planner_respects_provider_switch(monkeypatch):
    monkeypatch.setenv("AI_TRADE_LLM_PROVIDER", "mock")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret")

    plan = AgentPlanner(client=ExplodingClient()).plan("更新数据并扫描 000001", {"symbol": "000001"})

    assert plan == []
