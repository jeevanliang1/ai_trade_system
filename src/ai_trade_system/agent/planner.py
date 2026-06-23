from __future__ import annotations

from typing import Any

from ai_trade_system.config import env_value
from ai_trade_system.deepseek import DeepSeekClient

from .tools import SYSTEM_TOOL_NAMES, canonical_tool_name


class AgentPlanner:
    def __init__(self, client: Any | None = None):
        self.client = client or DeepSeekClient()

    def plan(self, prompt: str, context: dict[str, Any]) -> list[str]:
        if (env_value("AI_TRADE_LLM_PROVIDER", "mock") or "mock").lower() != "deepseek":
            return []
        response = self.client.chat_json(
            system_prompt=(
                "你是 ai_trade_system 的任务规划器。只输出 JSON 对象，字段 tools 是数组。"
                "tools 只能从 data.update, automation.weekly_result, research.fundamental, "
                "research.batch_fundamental, radar.scan, backtest.run, risk.evaluate, "
                "paper.run, share.weixin 中选择。"
                "读取本周定时扫描结果时用 automation.weekly_result；"
                "对周榜候选批量做基本面和信息面研究时用 research.batch_fundamental；"
                "需要给微信/用户返回最终可分享文本时用 share.weixin。不要输出实盘下单工具。"
            ),
            user_prompt=f"任务：{prompt}\n上下文：{context}",
            max_tokens=512,
        )
        if response.get("status") != "ok":
            return []
        return normalize_agent_tools((response.get("data") or {}).get("tools", []))


def normalize_agent_tools(raw_tools: object) -> list[str]:
    if isinstance(raw_tools, str):
        raw_tools = [item.strip() for item in raw_tools.split(",")]
    if not isinstance(raw_tools, list):
        return []

    tools: list[str] = []
    for raw_name in raw_tools:
        name = canonical_tool_name(raw_name)
        if name in SYSTEM_TOOL_NAMES and name not in tools:
            tools.append(name)
    return tools
