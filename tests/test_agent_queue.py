from __future__ import annotations

from threading import Event

from ai_trade_system.agent.models import AgentTask
from ai_trade_system.agent.queue import AgentTaskQueue
from ai_trade_system.agent.store import AgentStore


class BlockingOrchestrator:
    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.notifications: list[dict] = []
        self.task = AgentTask(task_id="agt_background", source="api", prompt="总结系统", status="pending")

    def create_task(self, prompt: str, *, source: str = "frontend", context: dict | None = None, auto_run: bool = True) -> AgentTask:
        assert auto_run is False
        self.task.prompt = prompt
        self.task.source = source
        self.task.context = context or {}
        return self.task

    def run_task(self, task_id: str) -> AgentTask:
        assert task_id == self.task.task_id
        self.started.set()
        self.release.wait(timeout=2)
        self.task.status = "completed"
        return self.task

    def approve_task(self, task_id: str, approval: str = "approved") -> AgentTask:
        self.task.status = "pending"
        return self.task

    def notify_task_update(self, task: AgentTask) -> dict:
        self.notifications.append({"task_id": task.task_id, "status": task.status})
        return {"status": "ok", "summary": "notified"}


def test_agent_queue_returns_queued_task_before_background_run_finishes():
    orchestrator = BlockingOrchestrator()
    queue = AgentTaskQueue(orchestrator=orchestrator)

    task = queue.submit("总结系统", source="api", context={"symbol": "000001"})

    assert task.status == "queued"
    assert orchestrator.started.wait(timeout=1)
    assert orchestrator.task.status == "queued"
    assert orchestrator.notifications == []

    orchestrator.release.set()
    assert queue.wait_for_idle(timeout=2)
    assert orchestrator.task.status == "completed"
    assert orchestrator.notifications == [{"task_id": "agt_background", "status": "completed"}]


def test_agent_queue_marks_stale_queued_tasks_as_failed(tmp_path):
    store = AgentStore(tmp_path / "agent")
    store.save_task(
        AgentTask(
            task_id="agt_orphan",
            source="weixin",
            prompt="这周的股票扫描分析结论输出给我",
            status="queued",
            created_at="2026-06-20T00:00:00Z",
            updated_at="2026-06-20T00:00:00Z",
        )
    )

    class StoreBackedOrchestrator:
        def __init__(self, store: AgentStore) -> None:
            self.store = store

    queue = AgentTaskQueue(orchestrator=StoreBackedOrchestrator(store))

    marked = queue.cleanup_stale_tasks(max_age_seconds=60, now="2026-06-20T00:10:00Z")

    assert [task.task_id for task in marked] == ["agt_orphan"]
    task = store.get_task("agt_orphan")
    assert task.status == "failed"
    assert "orphan" in task.result_summary
    events = store.read_trace("agt_orphan")
    assert events[-1]["type"] == "orphan_task_marked"
    assert events[-1]["payload"]["previous_status"] == "queued"


def test_agent_queue_does_not_mark_recent_or_active_tasks_as_stale(tmp_path):
    store = AgentStore(tmp_path / "agent")
    for task_id, status in [("agt_recent", "queued"), ("agt_active", "running")]:
        store.save_task(
            AgentTask(
                task_id=task_id,
                source="weixin",
                prompt="这周的股票扫描分析结论输出给我",
                status=status,
                created_at="2026-06-20T00:00:00Z",
                updated_at="2026-06-20T00:09:30Z",
            )
        )

    class StoreBackedOrchestrator:
        def __init__(self, store: AgentStore) -> None:
            self.store = store

    queue = AgentTaskQueue(orchestrator=StoreBackedOrchestrator(store))
    queue._threads["agt_active"] = type("ActiveThread", (), {"is_alive": lambda self: True})()

    marked = queue.cleanup_stale_tasks(max_age_seconds=60, now="2026-06-20T00:10:00Z")

    assert marked == []
    assert store.get_task("agt_recent").status == "queued"
    assert store.get_task("agt_active").status == "running"
