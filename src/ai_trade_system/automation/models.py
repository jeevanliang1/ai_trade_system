from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass
class AutomationConfig:
    enabled: bool = True
    timezone: str = "Asia/Shanghai"
    weekly_weekday: int = 5
    weekly_time: str = "09:30"
    daily_time: str = "09:45"
    top_n: int = 10
    adjust: str = "qfq"
    min_bars: int = 60
    lookback: int = 120
    chan_weight: float = 1.0
    volume_weight: float = 0.35

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AutomationConfig":
        return _from_dict(cls, payload)


@dataclass
class AutomationRunRecord:
    run_id: str
    task: str
    status: str
    started_at: str
    finished_at: str | None = None
    message: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AutomationRunRecord":
        return _from_dict(cls, payload)


@dataclass
class RadarCandidateScore:
    code: str
    name: str
    exchange: str
    rank: int
    composite_score: float
    chan_score: float
    volume_score: float
    latest_day: str | None
    latest_close: float | None
    chan_signal_title: str | None
    chan_signal_action: str | None
    volume_entry_ready: bool
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "RadarCandidateScore":
        return _from_dict(cls, payload)


@dataclass
class WeeklyRadarResult:
    run_id: str
    generated_at: str
    status: str
    total_candidates: int
    scanned: int
    missing: int
    top: list[RadarCandidateScore]

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["top"] = [item.as_dict() for item in self.top]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WeeklyRadarResult":
        data = dict(payload or {})
        data["top"] = [RadarCandidateScore.from_dict(item) for item in data.get("top", [])]
        return _from_dict(cls, data)


@dataclass
class DailyJudgment:
    code: str
    name: str
    exchange: str
    judgment: str
    reason: str
    current_score: float
    baseline_score: float
    latest_day: str | None
    latest_close: float | None
    chan_signal_title: str | None
    volume_entry_ready: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "DailyJudgment":
        return _from_dict(cls, payload)


@dataclass
class AutomationStatus:
    config: AutomationConfig
    running: bool = False
    last_weekly_run: dict[str, Any] | None = None
    last_daily_run: dict[str, Any] | None = None
    weekly_top10_count: int = 0
    latest_daily_judgment_count: int = 0
    next_weekly_run: str | None = None
    next_daily_run: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["config"] = self.config.as_dict()
        return payload


def _from_dict(cls, payload: dict[str, Any] | None):
    data = payload or {}
    names = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in names})
