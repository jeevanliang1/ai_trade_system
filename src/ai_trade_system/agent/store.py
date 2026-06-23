from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_trade_system.agent.models import AgentTask, utc_now


DEFAULT_AGENT_ROOT = Path("data/agent")


class AgentStore:
    def __init__(self, root: str | Path = DEFAULT_AGENT_ROOT):
        self.root = Path(root)
        self.tasks_dir = self.root / "tasks"
        self.reports_dir = self.root / "reports"
        self.runs_dir = self.root / "runs"

    def save_task(self, task: AgentTask) -> AgentTask:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        path = self._task_path(task.task_id)
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(task.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(path)
        return task

    def get_task(self, task_id: str) -> AgentTask:
        path = self._task_path(task_id)
        if not path.exists():
            raise KeyError(f"Agent task not found: {task_id}")
        return AgentTask.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_tasks(self, limit: int = 50) -> list[AgentTask]:
        if not self.tasks_dir.exists():
            return []
        task_entries = [
            (path.stat().st_mtime_ns, AgentTask.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            for path in self.tasks_dir.glob("*.json")
        ]
        task_entries.sort(key=lambda item: (item[0], item[1].created_at, item[1].task_id), reverse=True)
        return [task for _, task in task_entries[:limit]]

    def mark_stale_incomplete_tasks(
        self,
        *,
        max_age_seconds: int = 1800,
        now: str | datetime | None = None,
        statuses: set[str] | None = None,
        exclude_task_ids: set[str] | None = None,
    ) -> list[AgentTask]:
        now_dt = _parse_utc_datetime(now) if now is not None else datetime.now(UTC).replace(microsecond=0)
        stale_statuses = statuses or {"queued", "running"}
        excluded = exclude_task_ids or set()
        marked: list[AgentTask] = []
        for task in self.list_tasks(limit=1000):
            if task.task_id in excluded or task.status not in stale_statuses:
                continue
            updated_at = _parse_utc_datetime(task.updated_at)
            age_seconds = int((now_dt - updated_at).total_seconds())
            if age_seconds < max_age_seconds:
                continue
            previous_status = task.status
            task.status = "failed"
            task.result_summary = (
                f"任务已标记为失败：{previous_status} 状态超过 {max_age_seconds} 秒未继续执行，"
                "可能是 OpenClaw/本地进程中断留下的 orphan task。"
            )
            self.append_trace_event(
                task.task_id,
                "orphan_task_marked",
                status=task.status,
                summary=task.result_summary,
                payload={
                    "previous_status": previous_status,
                    "age_seconds": age_seconds,
                    "max_age_seconds": max_age_seconds,
                },
            )
            task.touch()
            self.save_task(task)
            marked.append(task)
        return marked

    def find_recent_task_by_idempotency_key(
        self,
        idempotency_key: str,
        *,
        max_age_seconds: int = 300,
        now: str | datetime | None = None,
        statuses: set[str] | None = None,
    ) -> AgentTask | None:
        now_dt = _parse_utc_datetime(now) if now is not None else datetime.now(UTC).replace(microsecond=0)
        reusable_statuses = statuses or {"pending", "queued", "running", "waiting_confirmation"}
        for task in self.list_tasks(limit=1000):
            if task.context.get("idempotency_key") != idempotency_key:
                continue
            if task.status not in reusable_statuses:
                continue
            age_seconds = int((now_dt - _parse_utc_datetime(task.created_at)).total_seconds())
            if age_seconds <= max_age_seconds:
                return task
        return None

    def write_report(self, task: AgentTask, payload: dict[str, Any]) -> str:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        relative = Path("reports") / f"{task.task_id}.json"
        path = self.root / relative
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return relative.as_posix()

    def append_trace_event(
        self,
        task_id: str,
        event_type: str,
        *,
        tool_name: str | None = None,
        status: str | None = None,
        summary: str = "",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = self._trace_path(task_id)
        existing = self.read_trace(task_id)
        event = {
            "event_id": f"{len(existing) + 1:06d}",
            "task_id": task_id,
            "type": event_type,
            "created_at": utc_now(),
            "tool_name": tool_name,
            "status": status,
            "summary": summary,
            "payload": payload or {},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        return event

    def read_trace(self, task_id: str) -> list[dict[str, Any]]:
        path = self._trace_path(task_id)
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        return events

    def _task_path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def _trace_path(self, task_id: str) -> Path:
        return self.runs_dir / task_id / "events.jsonl"


def _parse_utc_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
