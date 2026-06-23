from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from ai_trade_system.agent.tools import agent_tool_spec, prompt_planned_tools, requested_agent_tools


DEFAULT_AGENT_ROOT = Path("data/agent")


@dataclass
class AgentMemory:
    id: str
    type: str
    scope: str
    title: str
    content: str
    tags: list[str] = field(default_factory=list)
    source: str = "system"
    confidence: str = "medium"
    enabled: bool = True
    expires_at: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AgentMemory":
        return _from_dict(cls, payload)


@dataclass
class AgentSkill:
    id: str
    title: str
    description: str
    trigger_terms: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    required_confirmations: list[str] = field(default_factory=list)
    output_format: str = "agent_report"
    enabled: bool = True

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AgentSkill":
        return _from_dict(cls, payload)


@dataclass
class AgentPlannerPolicy:
    max_steps: int = 8
    blocked_intents: list[str] = field(default_factory=lambda: ["实盘", "下单", "真实交易", "券商委托", "委托买入", "委托卖出"])
    tool_permissions: dict[str, str] = field(
        default_factory=lambda: {
            "research.fundamental": "confirm",
            "research.batch_fundamental": "confirm",
            "share.weixin": "auto",
        }
    )
    default_output_format: str = "agent_report"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AgentPlannerPolicy":
        if not payload:
            return cls()
        policy = _from_dict(cls, payload)
        defaults = cls()
        policy.blocked_intents = list(dict.fromkeys([*defaults.blocked_intents, *policy.blocked_intents]))
        policy.tool_permissions = {**defaults.tool_permissions, **policy.tool_permissions}
        return policy


class AgentGovernanceStore:
    def __init__(self, root: str | Path = DEFAULT_AGENT_ROOT):
        self.root = Path(root)

    @property
    def memory_path(self) -> Path:
        return self.root / "memory.json"

    @property
    def skills_path(self) -> Path:
        return self.root / "skills.json"

    @property
    def policy_path(self) -> Path:
        return self.root / "policy.json"

    def list_memories(self) -> list[AgentMemory]:
        payload = _read_json(self.memory_path)
        if not payload:
            memories = _default_memories()
            self._write_memories(memories)
            return memories
        return [AgentMemory.from_dict(item) for item in payload.get("memories", [])]

    def get_memory(self, memory_id: str) -> AgentMemory:
        for memory in self.list_memories():
            if memory.id == memory_id:
                return memory
        raise ValueError(f"unknown memory: {memory_id}")

    def save_memory(self, memory: AgentMemory) -> AgentMemory:
        memories = [item for item in self.list_memories() if item.id != memory.id]
        memories.append(memory)
        self._write_memories(memories)
        return memory

    def delete_memory(self, memory_id: str) -> None:
        memories = [item for item in self.list_memories() if item.id != memory_id]
        self._write_memories(memories)

    def list_skills(self) -> list[AgentSkill]:
        payload = _read_json(self.skills_path)
        if not payload:
            skills = _default_skills()
            self._write_skills(skills)
            return skills
        return [AgentSkill.from_dict(item) for item in payload.get("skills", [])]

    def get_skill(self, skill_id: str) -> AgentSkill:
        for skill in self.list_skills():
            if skill.id == skill_id:
                return skill
        raise ValueError(f"unknown skill: {skill_id}")

    def save_skill(self, skill: AgentSkill) -> AgentSkill:
        skills = [item for item in self.list_skills() if item.id != skill.id]
        skills.append(skill)
        self._write_skills(skills)
        return skill

    def delete_skill(self, skill_id: str) -> None:
        skills = [item for item in self.list_skills() if item.id != skill_id]
        self._write_skills(skills)

    def load_policy(self) -> AgentPlannerPolicy:
        payload = _read_json(self.policy_path)
        if not payload:
            policy = AgentPlannerPolicy()
            self.save_policy(policy)
            return policy
        return AgentPlannerPolicy.from_dict(payload)

    def save_policy(self, policy: AgentPlannerPolicy) -> AgentPlannerPolicy:
        _write_json(self.policy_path, policy.as_dict())
        return policy

    def _write_memories(self, memories: list[AgentMemory]) -> None:
        _write_json(self.memory_path, {"memories": [memory.as_dict() for memory in memories]})

    def _write_skills(self, skills: list[AgentSkill]) -> None:
        _write_json(self.skills_path, {"skills": [skill.as_dict() for skill in skills]})


class AgentGovernanceService:
    def __init__(self, store: AgentGovernanceStore | None = None):
        self.store = store or AgentGovernanceStore()

    def preview_plan(self, prompt: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_prompt = prompt.strip()
        policy = self.store.load_policy()
        blocked_term = next((term for term in policy.blocked_intents if term and term in clean_prompt), None)
        if blocked_term:
            return {
                "status": "blocked",
                "intent": "blocked_live_trading",
                "selected_skill": None,
                "matched_memories": [],
                "steps": [],
                "stop_conditions": ["live_trading_blocked"],
                "final_output": "blocked_notice",
                "blocked_reason": f"检测到被阻断意图：{blocked_term}",
                "ignored_tools": [],
            }

        normalized_context = dict(context or {})
        requested_tools, ignored = requested_agent_tools(normalized_context)
        skill = self._select_skill(clean_prompt)
        if skill:
            tool_names = skill.steps
            intent = skill.id
            final_output = skill.output_format
        elif requested_tools:
            tool_names = requested_tools
            intent = "explicit_tools"
            final_output = policy.default_output_format
        else:
            tool_names = prompt_planned_tools(clean_prompt)
            intent = "keyword_plan" if tool_names else "general_agent_report"
            final_output = policy.default_output_format
        tool_names = tool_names[: policy.max_steps]
        steps = [self._step_payload(tool_name, index, policy, skill) for index, tool_name in enumerate(tool_names, start=1) if agent_tool_spec(tool_name)]
        return {
            "status": "ok",
            "intent": intent,
            "selected_skill": skill.as_dict() if skill else None,
            "matched_memories": [memory.as_dict() for memory in self._match_memories(clean_prompt, skill)],
            "steps": steps,
            "stop_conditions": ["live_trading_blocked", "missing_required_data", "requires_confirmation"],
            "final_output": final_output,
            "blocked_reason": None,
            "ignored_tools": ignored + [tool_name for tool_name in tool_names if agent_tool_spec(tool_name) is None],
        }

    def _select_skill(self, prompt: str) -> AgentSkill | None:
        enabled = [skill for skill in self.store.list_skills() if skill.enabled]
        scored: list[tuple[int, AgentSkill]] = []
        for skill in enabled:
            score = sum(1 for term in skill.trigger_terms if term and term in prompt)
            if score:
                scored.append((score, skill))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def _match_memories(self, prompt: str, skill: AgentSkill | None) -> list[AgentMemory]:
        terms = set(skill.trigger_terms if skill else [])
        terms.update(prompt.split())
        matched: list[AgentMemory] = []
        for memory in self.store.list_memories():
            if not memory.enabled:
                continue
            if any(tag in prompt for tag in memory.tags) or any(term and term in memory.content for term in terms):
                matched.append(memory)
        return matched[:5]

    def _step_payload(self, tool_name: str, index: int, policy: AgentPlannerPolicy, skill: AgentSkill | None) -> dict[str, Any]:
        spec = agent_tool_spec(tool_name)
        permission = policy.tool_permissions.get(tool_name, spec.permission if spec else "auto")
        return {
            "index": index,
            "tool": tool_name,
            "title": spec.description if spec else tool_name,
            "permission": permission,
            "reason": _step_reason(tool_name, skill),
        }


def _default_memories() -> list[AgentMemory]:
    return [
        AgentMemory(
            id="mem_weekly_scan_reuse",
            type="workflow_rule",
            scope="agent",
            title="本周扫描结果优先复用",
            content="用户询问这周或本周股票扫描分析结果时，优先读取 automation.weekly_result 附带的周度 AI 深度分析缓存；缓存存在时不重复外部研究或重跑扫描。",
            tags=["weekly", "scan", "automation", "weixin"],
            source="system_default",
            confidence="high",
        )
    ]


def _default_skills() -> list[AgentSkill]:
    return [
        AgentSkill(
            id="weekly_scan_share",
            title="周度扫描研究分享",
            description="复用本周周扫描和分区 Top10 AI 深度分析缓存，并准备微信或飞书可返回的最终分享文本。",
            trigger_terms=["这周", "本周", "周扫描", "股票扫描", "定时扫描结果", "扫描结果", "分析结论", "结论", "输出给我", "分享", "最终结果"],
            steps=["automation.weekly_result", "research.batch_fundamental", "share.weixin"],
            allowed_tools=["automation.weekly_result", "research.batch_fundamental", "share.weixin"],
            required_confirmations=["research.batch_fundamental"],
            output_format="weixin_ready_report",
        )
    ]


def _step_reason(tool_name: str, skill: AgentSkill | None) -> str:
    reasons = {
        "automation.weekly_result": "读取已持久化周扫描和 AI 深度分析缓存，避免把定时任务结果和临时重扫混在一起。",
        "research.batch_fundamental": "优先复用周度 AI 深度分析缓存；没有缓存时才对候选股票做外部基本面和信息面研究。",
        "share.weixin": "把周榜和 AI 深度分析整理成可由 OpenClaw/微信/飞书返回的最终文本。",
    }
    if tool_name in reasons:
        return reasons[tool_name]
    if skill:
        return f"技能 {skill.id} 需要调用 {tool_name} 完成任务。"
    return f"根据用户输入选择 {tool_name}。"


def _from_dict(cls, payload: dict[str, Any] | None):
    data = payload or {}
    names = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in names})


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
