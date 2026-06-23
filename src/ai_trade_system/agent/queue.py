from __future__ import annotations

from threading import Lock, Thread
from time import monotonic, sleep
from typing import Any

from .models import AgentTask
from .orchestrator import AgentOrchestrator


TERMINAL_STATUSES = {"completed", "failed", "blocked", "waiting_confirmation"}


class AgentTaskQueue:
    def __init__(self, orchestrator: Any | None = None):
        self.orchestrator = orchestrator or AgentOrchestrator()
        self._lock = Lock()
        self._threads: dict[str, Thread] = {}

    def submit(self, prompt: str, *, source: str = "frontend", context: dict[str, Any] | None = None) -> AgentTask:
        self.cleanup_stale_tasks()
        task = self.orchestrator.create_task(prompt, source=source, context=context or {}, auto_run=False)
        if task.status not in TERMINAL_STATUSES:
            task.status = "queued"
            self._save_task(task)
            self._start(task.task_id)
        return task

    def approve(self, task_id: str, approval: str = "approved") -> AgentTask:
        task = self.orchestrator.approve_task(task_id, approval)
        if task.status not in TERMINAL_STATUSES:
            task.status = "queued"
            self._save_task(task)
            self._start(task.task_id)
        return task

    def wait_for_idle(self, timeout: float = 5.0) -> bool:
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            with self._lock:
                self._threads = {task_id: thread for task_id, thread in self._threads.items() if thread.is_alive()}
                threads = list(self._threads.values())
            if not threads:
                return True
            for thread in threads:
                thread.join(timeout=0.05)
            sleep(0.01)
        return False

    def cleanup_stale_tasks(self, *, max_age_seconds: int = 1800, now: str | None = None) -> list[AgentTask]:
        store = getattr(self.orchestrator, "store", None)
        if store is None or not hasattr(store, "mark_stale_incomplete_tasks"):
            return []
        with self._lock:
            self._threads = {task_id: thread for task_id, thread in self._threads.items() if thread.is_alive()}
            active_task_ids = set(self._threads)
        return store.mark_stale_incomplete_tasks(
            max_age_seconds=max_age_seconds,
            now=now,
            exclude_task_ids=active_task_ids,
        )

    def _start(self, task_id: str) -> None:
        with self._lock:
            existing = self._threads.get(task_id)
            if existing and existing.is_alive():
                return
            thread = Thread(target=self._run, args=(task_id,), daemon=True)
            self._threads[task_id] = thread
            thread.start()

    def _run(self, task_id: str) -> None:
        task = self.orchestrator.run_task(task_id)
        self._notify_task_update(task)

    def _notify_task_update(self, task: AgentTask) -> None:
        notifier = getattr(self.orchestrator, "notify_task_update", None)
        if not callable(notifier):
            return
        try:
            notifier(task)
        except Exception:
            return

    def _save_task(self, task: AgentTask) -> None:
        store = getattr(self.orchestrator, "store", None)
        if store is not None:
            store.save_task(task)
