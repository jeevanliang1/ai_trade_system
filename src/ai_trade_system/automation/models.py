from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
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
    weekly_analysis_enabled: bool = True
    weekly_analysis_top_n: int = 10
    weekly_delivery_enabled: bool = True
    weekly_delivery_channel: str = "weixin"

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
    board: str | None = None

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
    board_top: dict[str, list[RadarCandidateScore]] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["top"] = [item.as_dict() for item in self.top]
        payload["board_top"] = {
            key: [item.as_dict() for item in items]
            for key, items in self.board_top.items()
        }
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WeeklyRadarResult":
        data = dict(payload or {})
        data["top"] = [RadarCandidateScore.from_dict(item) for item in data.get("top", [])]
        board_top = data.get("board_top") if isinstance(data.get("board_top"), dict) else {}
        data["board_top"] = {
            key: [RadarCandidateScore.from_dict(item) for item in items]
            for key, items in board_top.items()
            if isinstance(items, list)
        }
        return _from_dict(cls, data)


@dataclass
class WeeklyAnalysisItem:
    rank: int | None
    code: str
    name: str | None
    exchange: str | None
    board: str
    scan_score: float | None
    latest_day: str | None
    scan_signal_title: str | None
    scan_reason: str | None
    analysis_status: str
    summary: str
    confidence: str = "medium"
    evidence_status: str = "unknown"
    sources: list[dict[str, Any]] = field(default_factory=list)
    chan_multilevel_basis: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WeeklyAnalysisItem":
        data = dict(payload or {})
        sources = data.get("sources")
        data["sources"] = [dict(item) for item in sources if isinstance(item, dict)] if isinstance(sources, list) else []
        return _from_dict(cls, data)


@dataclass
class WeeklyAnalysisSection:
    key: str
    label: str
    status: str
    summary: str
    items: list[WeeklyAnalysisItem] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["items"] = [item.as_dict() for item in self.items]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WeeklyAnalysisSection":
        data = dict(payload or {})
        data["items"] = [WeeklyAnalysisItem.from_dict(item) for item in data.get("items", [])]
        return _from_dict(cls, data)


@dataclass
class WeeklyAnalysisResult:
    run_id: str
    weekly_run_id: str
    generated_at: str
    status: str
    delivery_channel: str
    sections: list[WeeklyAnalysisSection] = field(default_factory=list)
    delivery_status: str | None = None
    delivery_summary: str | None = None
    message: str = ""
    report_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sections"] = [section.as_dict() for section in self.sections]
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WeeklyAnalysisResult":
        data = dict(payload or {})
        data["sections"] = [WeeklyAnalysisSection.from_dict(item) for item in data.get("sections", [])]
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
    weekly_analysis_status: str | None = None
    weekly_analysis_run_id: str | None = None
    weekly_delivery_status: str | None = None
    next_weekly_run: str | None = None
    next_daily_run: str | None = None
    recent_runs: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["config"] = self.config.as_dict()
        return payload


def _from_dict(cls, payload: dict[str, Any] | None):
    data = payload or {}
    names = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in names})
