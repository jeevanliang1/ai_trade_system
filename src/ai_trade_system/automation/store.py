from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from ai_trade_system.automation.models import (
    AutomationConfig,
    AutomationRunRecord,
    DailyJudgment,
    WeeklyAnalysisResult,
    WeeklyRadarResult,
)


DEFAULT_AUTOMATION_ROOT = Path("data/automation")
DEFAULT_AUTOMATION_LOG_ROOT = Path("logs/automation")


class AutomationStore:
    def __init__(self, root: str | Path = DEFAULT_AUTOMATION_ROOT, log_root: str | Path = DEFAULT_AUTOMATION_LOG_ROOT):
        self.root = Path(root)
        self.log_root = Path(log_root)

    @property
    def config_path(self) -> Path:
        return self.root / "config.json"

    @property
    def state_path(self) -> Path:
        return self.root / "state.json"

    @property
    def weekly_path(self) -> Path:
        return self.root / "star_radar_top10.json"

    @property
    def daily_dir(self) -> Path:
        return self.root / "daily_judgments"

    @property
    def weekly_analysis_dir(self) -> Path:
        return self.root / "weekly_analysis"

    @property
    def latest_weekly_analysis_path(self) -> Path:
        return self.root / "weekly_analysis_latest.json"

    @property
    def runs_path(self) -> Path:
        return self.log_root / "runs.jsonl"

    def load_config(self) -> AutomationConfig:
        return AutomationConfig.from_dict(_read_json(self.config_path))

    def save_config(self, config: AutomationConfig) -> None:
        _write_json(self.config_path, config.as_dict())

    def load_state(self) -> dict[str, Any]:
        return {
            **_default_state(),
            **(_read_json(self.state_path) or {}),
        }

    def save_state(self, state: dict[str, Any]) -> None:
        _write_json(self.state_path, {**_default_state(), **state})

    def load_weekly_result(self) -> WeeklyRadarResult | None:
        payload = _read_json(self.weekly_path)
        if not payload:
            return None
        return WeeklyRadarResult.from_dict(payload)

    def save_weekly_result(self, result: WeeklyRadarResult) -> None:
        _write_json(self.weekly_path, result.as_dict())

    def weekly_analysis_path(self, week_key: str) -> Path:
        return self.weekly_analysis_dir / f"{week_key}.json"

    def load_weekly_analysis(self, week_key: str | None = None) -> WeeklyAnalysisResult | None:
        path = self.weekly_analysis_path(week_key) if week_key else self.latest_weekly_analysis_path
        payload = _read_json(path)
        if not payload:
            return None
        return WeeklyAnalysisResult.from_dict(payload)

    def load_latest_weekly_analysis(self) -> WeeklyAnalysisResult | None:
        return self.load_weekly_analysis()

    def save_weekly_analysis(self, result: WeeklyAnalysisResult) -> None:
        payload = result.as_dict()
        week_key = week_key_for_datetime(result.generated_at)
        _write_json(self.weekly_analysis_path(week_key), payload)
        _write_json(self.latest_weekly_analysis_path, payload)

    def load_daily_judgments(self, day: str) -> list[DailyJudgment]:
        payload = _read_json(self.daily_dir / f"{day}.json")
        rows = payload.get("judgments", []) if isinstance(payload, dict) else []
        return [DailyJudgment.from_dict(item) for item in rows]

    def save_daily_judgments(self, day: str, judgments: list[DailyJudgment]) -> None:
        _write_json(
            self.daily_dir / f"{day}.json",
            {"date": day, "judgments": [judgment.as_dict() for judgment in judgments]},
        )

    def append_run(self, run: AutomationRunRecord) -> None:
        self.runs_path.parent.mkdir(parents=True, exist_ok=True)
        with self.runs_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(run.as_dict(), ensure_ascii=False) + "\n")

    def load_runs(self) -> list[AutomationRunRecord]:
        if not self.runs_path.exists():
            return []
        records: list[AutomationRunRecord] = []
        for line in self.runs_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(AutomationRunRecord.from_dict(json.loads(line)))
        return records


def week_key_for_datetime(value: str) -> str:
    day = value[:10]
    year, week, _weekday = date.fromisoformat(day).isocalendar()
    return f"{year}-W{week:02d}"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_state() -> dict[str, Any]:
    return {
        "last_weekly_run": None,
        "last_daily_run": None,
        "last_watchlist_data_run": None,
        "last_weekly_success_date": None,
        "last_daily_success_date": None,
        "last_watchlist_data_success_date": None,
    }
