from __future__ import annotations

from datetime import datetime

from ai_trade_system.automation.models import AutomationConfig, RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.automation.scheduler import AutomationScheduler
from ai_trade_system.automation.store import AutomationStore


class FakeService:
    def __init__(self, store):
        self.store = store
        self.weekly_calls = 0
        self.daily_calls = 0
        self.watchlist_data_calls = 0

    def run_watchlist_data_maintenance(self, now=None):
        self.watchlist_data_calls += 1
        state = self.store.load_state()
        state["last_watchlist_data_success_date"] = now.date().isoformat()
        self.store.save_state(state)

    def run_weekly_full_maintenance(self, now=None):
        self.weekly_calls += 1
        self.store.save_weekly_result(
            WeeklyRadarResult(
                run_id="weekly-1",
                generated_at=now.isoformat(),
                status="success",
                total_candidates=1,
                scanned=1,
                missing=0,
                top=[
                    RadarCandidateScore(
                        code="688001",
                        name="华兴源创",
                        exchange="SSE",
                        rank=1,
                        composite_score=70,
                        chan_score=44,
                        volume_score=74,
                        latest_day="2026-06-18",
                        latest_close=81,
                        chan_signal_title="缠论三买",
                        chan_signal_action="buy",
                        volume_entry_ready=False,
                        reason="baseline",
                    )
                ],
            )
        )
        self.store.save_state(
            {
                "last_weekly_success_date": now.date().isoformat(),
                "last_daily_success_date": None,
                "last_weekly_run": None,
                "last_daily_run": None,
            }
        )

    def run_daily_top10_judgment(self, now=None):
        self.daily_calls += 1
        self.store.save_state(
            {
                "last_weekly_success_date": "2026-06-20",
                "last_daily_success_date": now.date().isoformat(),
                "last_weekly_run": None,
                "last_daily_run": None,
            }
        )


def test_scheduler_runs_weekly_on_saturday_once(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 20, 10, 0))
    scheduler.run_due_tasks(now=datetime(2026, 6, 20, 10, 5))

    assert service.weekly_calls == 1


def test_scheduler_catches_up_missed_saturday_on_startup(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 22, 9, 0))

    assert service.weekly_calls == 1


def test_scheduler_runs_daily_when_weekly_top10_exists(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    store.save_state({"last_weekly_success_date": "2026-06-20", "last_daily_success_date": None, "last_weekly_run": None, "last_daily_run": None})
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 23, 10, 0))
    scheduler.run_due_tasks(now=datetime(2026, 6, 23, 10, 5))

    assert service.daily_calls == 1


def test_scheduler_runs_watchlist_data_maintenance_once_per_day(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    store.save_state({
        "last_weekly_success_date": "2026-06-20",
        "last_daily_success_date": "2026-06-23",
        "last_weekly_run": None,
        "last_daily_run": None,
    })
    service = FakeService(store)
    scheduler = AutomationScheduler(service=service, store=store, config=AutomationConfig(enabled=True))

    scheduler.run_due_tasks(now=datetime(2026, 6, 23, 9, 0))
    scheduler.run_due_tasks(now=datetime(2026, 6, 23, 9, 5))

    assert service.watchlist_data_calls == 1
    assert service.weekly_calls == 0
