from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta

from ai_trade_system.automation.models import AutomationConfig
from ai_trade_system.automation.service import AutomationService
from ai_trade_system.automation.store import AutomationStore


class AutomationScheduler:
    def __init__(
        self,
        *,
        service: AutomationService,
        store: AutomationStore | None = None,
        config: AutomationConfig | None = None,
        check_interval_seconds: float = 60.0,
    ):
        self.service = service
        self.store = store or service.store
        self.config = config or self.store.load_config()
        self.check_interval_seconds = check_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        if not self.store.load_config().enabled:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name="automation-scheduler", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def run_due_tasks(self, now: datetime | None = None) -> None:
        current = now or datetime.now()
        config = self.config
        if not config.enabled:
            return
        if self._watchlist_data_due(current, config):
            self.service.run_watchlist_data_maintenance(now=current)
        if self._weekly_due(current, config):
            self.service.run_weekly_full_maintenance(now=current)
            return
        if self._daily_due(current):
            self.service.run_daily_top10_judgment(now=current)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_due_tasks()
            except Exception:
                pass
            self._stop_event.wait(self.check_interval_seconds)

    def _weekly_due(self, now: datetime, config: AutomationConfig) -> bool:
        state = self.store.load_state()
        last_success = state.get("last_weekly_success_date")
        current_period = _weekly_period_start(now.date(), config.weekly_weekday)
        if last_success and date.fromisoformat(last_success) >= current_period:
            return False
        return now.date() >= current_period

    def _daily_due(self, now: datetime) -> bool:
        state = self.store.load_state()
        weekly = self.store.load_weekly_result()
        if (weekly is None or not weekly.top) and not state.get("last_weekly_success_date"):
            return False
        last_daily = state.get("last_daily_success_date")
        return last_daily != now.date().isoformat()

    def _watchlist_data_due(self, now: datetime, config: AutomationConfig) -> bool:
        if not getattr(config, "watchlist_data_enabled", True):
            return False
        state = self.store.load_state()
        return state.get("last_watchlist_data_success_date") != now.date().isoformat()


def _weekly_period_start(day: date, weekday: int) -> date:
    delta = (day.weekday() - weekday) % 7
    return day - timedelta(days=delta)
