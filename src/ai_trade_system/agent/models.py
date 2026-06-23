from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


AgentTaskStatus = Literal["pending", "queued", "running", "completed", "waiting_confirmation", "blocked", "failed"]
AgentPermission = Literal["auto", "confirm", "blocked"]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass
class AgentConfirmation:
    code: str
    message: str
    risk_level: str = "high"
    status: str = "pending"
    tool_name: str | None = None
    created_at: str = field(default_factory=utc_now)
    resolved_at: str | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentConfirmation":
        return cls(**payload)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentStep:
    tool_name: str
    title: str
    status: str = "pending"
    started_at: str | None = None
    finished_at: str | None = None
    summary: str = ""
    output: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentStep":
        return cls(**payload)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentTask:
    task_id: str
    source: str
    prompt: str
    status: AgentTaskStatus
    context: dict[str, Any] = field(default_factory=dict)
    plan: list[str] = field(default_factory=list)
    steps: list[AgentStep] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    result_summary: str = ""
    confirmations: list[AgentConfirmation] = field(default_factory=list)
    report_path: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentTask":
        data = dict(payload)
        data["steps"] = [AgentStep.from_dict(step) for step in data.get("steps", [])]
        data["confirmations"] = [AgentConfirmation.from_dict(item) for item in data.get("confirmations", [])]
        return cls(**data)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def as_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "steps": [step.as_dict() for step in self.steps],
            "confirmations": [confirmation.as_dict() for confirmation in self.confirmations],
        }


@dataclass(frozen=True)
class AgentToolSpec:
    name: str
    description: str
    permission: AgentPermission
    category: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
