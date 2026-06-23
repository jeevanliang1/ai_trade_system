from __future__ import annotations

from typing import Any

from ai_trade_system.agent.models import AgentToolSpec

AGENT_REPORT_TOOL = "agent.report"
SYSTEM_SNAPSHOT_TOOL = "system.snapshot"
TOOL_ALIASES = {"openclaw.external_research": "research.fundamental"}
SYSTEM_TOOL_NAMES = {
    "data.update",
    "automation.weekly_result",
    "research.fundamental",
    "research.batch_fundamental",
    "radar.scan",
    "backtest.run",
    "risk.evaluate",
    "paper.run",
    "share.weixin",
}
ALL_TOOL_NAMES = {SYSTEM_SNAPSHOT_TOOL, AGENT_REPORT_TOOL, *SYSTEM_TOOL_NAMES}


def list_agent_tools() -> list[AgentToolSpec]:
    return [
        AgentToolSpec(
            name=SYSTEM_SNAPSHOT_TOOL,
            description="Summarize local trading-system state, limits, source, prompt, and target context.",
            permission="auto",
            category="system",
        ),
        AgentToolSpec(
            name="data.update",
            description="Maintain local managed A-share market data for the requested symbol or watchlist.",
            permission="auto",
            category="market_data",
        ),
        AgentToolSpec(
            name="automation.weekly_result",
            description="Read the latest persisted weekly automation radar result and return ranked candidates.",
            permission="auto",
            category="automation",
        ),
        AgentToolSpec(
            name="research.fundamental",
            description="Ask OpenClaw to collect external fundamental, announcement, news, and user-local information.",
            permission="confirm",
            category="external_research",
        ),
        AgentToolSpec(
            name="research.batch_fundamental",
            description="Ask OpenClaw to research fundamentals and information-side context for a ranked candidate batch.",
            permission="confirm",
            category="external_research",
        ),
        AgentToolSpec(
            name="radar.scan",
            description="Run the existing local signal-radar batch scanner and summarize ranked candidates.",
            permission="auto",
            category="research",
        ),
        AgentToolSpec(
            name="backtest.run",
            description="Run the existing local backtest engine with the selected or default strategy.",
            permission="auto",
            category="backtest",
        ),
        AgentToolSpec(
            name="risk.evaluate",
            description="Evaluate deterministic risk guardrails from metrics and current limits.",
            permission="auto",
            category="risk",
        ),
        AgentToolSpec(
            name="paper.run",
            description="Replay local bars through the existing paper-trading service.",
            permission="auto",
            category="paper",
        ),
        AgentToolSpec(
            name="share.weixin",
            description="Prepare a Weixin-ready final response from Agent outputs without sending an independent outbound message.",
            permission="auto",
            category="sharing",
        ),
        AgentToolSpec(
            name=AGENT_REPORT_TOOL,
            description="Persist a structured research or operations report under data/agent/reports.",
            permission="auto",
            category="reporting",
        ),
    ]


def agent_tool_spec(name: str) -> AgentToolSpec | None:
    return next((tool for tool in list_agent_tools() if tool.name == name), None)


def canonical_tool_name(name: object) -> str | None:
    if not isinstance(name, str):
        return None
    clean = name.strip()
    if not clean:
        return None
    return TOOL_ALIASES.get(clean, clean)


def requested_agent_tools(context: dict[str, Any]) -> tuple[list[str], list[str]]:
    requested = context.get("tools", [])
    if isinstance(requested, str):
        requested = [item.strip() for item in requested.split(",")]
    if not isinstance(requested, list):
        return [], [str(requested)]

    tools: list[str] = []
    ignored: list[str] = []
    for raw_name in requested:
        name = canonical_tool_name(raw_name)
        if name in SYSTEM_TOOL_NAMES and name not in tools:
            tools.append(name)
        elif name and name not in ALL_TOOL_NAMES:
            ignored.append(name)
    return tools, ignored


def prompt_planned_tools(prompt: str) -> list[str]:
    lowered = prompt.lower()
    weekly_terms = ("这周", "本周", "周扫描", "周榜", "股票扫描", "定时扫描结果", "weekly")
    share_terms = ("分享", "发给我", "发送", "输出给我", "输出", "结论", "分析结论", "最终结果", "返回结果", "share")
    weekly_requested = any(term in prompt or term in lowered for term in weekly_terms)
    share_requested = any(term in prompt or term in lowered for term in share_terms)
    planned: list[str] = []
    if weekly_requested:
        planned.append("automation.weekly_result")
        if any(term in prompt or term in lowered for term in ("股票", "优质", "分析", "结果", "基本面", "信息面")) or share_requested:
            planned.append("research.batch_fundamental")
    if share_requested:
        planned.append("share.weixin")

    checks: list[tuple[str, tuple[str, ...]]] = [
        ("data.update", ("更新数据", "维护数据", "行情更新", "行情维护", "更新", "行情", "data.update")),
        ("research.fundamental", ("研究", "基本面", "信息面", "新闻", "公告", "关注", "openclaw", "外部", "research.fundamental")),
        ("radar.scan", ("扫描", "信号雷达", "雷达", "选股", "radar.scan")),
        ("backtest.run", ("回测", "backtest", "backtest.run")),
        ("risk.evaluate", ("风控", "风险", "risk", "risk.evaluate")),
        ("paper.run", ("纸面", "模拟交易", "paper", "paper.run")),
    ]
    for tool_name, terms in checks:
        if tool_name == "radar.scan" and weekly_requested and not any(term in prompt for term in ("重新扫描", "跑扫描", "运行扫描")):
            continue
        if tool_name == "research.fundamental" and "research.batch_fundamental" in planned:
            continue
        if any(term in prompt or term in lowered for term in terms):
            planned.append(tool_name)
    return list(dict.fromkeys(planned))


def system_snapshot(prompt: str, source: str, context: dict[str, Any]) -> dict[str, Any]:
    symbol = context.get("symbol") or _symbol_from_prompt(prompt) or "未指定"
    return {
        "status": "ok",
        "summary": f"系统已接收来自 {source} 的 Agent 任务，目标标的 {symbol}。",
        "symbol": symbol,
        "exchange": context.get("exchange"),
        "live_trading": False,
        "risk_boundary": "AI Agent 只能触发研究、回测、纸面交易和风控复核；不能绕过实盘前置规则。",
    }


def _symbol_from_prompt(prompt: str) -> str | None:
    for token in prompt.replace("，", " ").replace(",", " ").split():
        digits = "".join(char for char in token if char.isdigit())
        if len(digits) == 6:
            return digits
    return None
