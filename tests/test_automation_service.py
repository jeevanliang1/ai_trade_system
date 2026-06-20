from __future__ import annotations

from datetime import datetime

from ai_trade_system.automation.models import RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.automation.service import AutomationService, BusyAutomationError
from ai_trade_system.automation.store import AutomationStore
from ai_trade_system.stock_catalog import StockInfo


class FakeCatalog:
    def __call__(self):
        return [
            StockInfo("688001", "华兴源创", "SSE"),
            StockInfo("688002", "睿创微纳", "SSE"),
            StockInfo("000858", "五粮液", "SZSE"),
        ]


class FakeWatchlist:
    def __call__(self):
        return [StockInfo("601318", "中国平安", "SSE")]


class FakeUpdater:
    def __init__(self):
        self.calls = []

    def __call__(self, stock, *, start_date, end_date, adjust, if_stale=True):
        self.calls.append((stock.code, start_date, end_date, adjust, if_stale))
        return {"status": "updated", "code": stock.code, "latest_rows": 80, "message": "ok"}


def test_weekly_full_maintenance_updates_star_and_watchlist_then_persists_top10(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    updater = FakeUpdater()

    def scan(stocks, config, generated_at=None):
        return WeeklyRadarResult(
            run_id="weekly-1",
            generated_at=generated_at or "2026-06-20T09:30:00+08:00",
            status="success",
            total_candidates=len(list(stocks)),
            scanned=2,
            missing=0,
            top=[
                RadarCandidateScore(
                    code="688001",
                    name="华兴源创",
                    exchange="SSE",
                    rank=1,
                    composite_score=70.1,
                    chan_score=44,
                    volume_score=74.7,
                    latest_day="2026-06-18",
                    latest_close=81.09,
                    chan_signal_title="缠论三买",
                    chan_signal_action="buy",
                    volume_entry_ready=False,
                    reason="三买结构，量能不足",
                )
            ],
        )

    service = AutomationService(
        store=store,
        load_catalog=FakeCatalog(),
        load_watchlist=FakeWatchlist(),
        update_stock_data=updater,
        scan_star_radar=scan,
    )

    result = service.run_weekly_full_maintenance(now=datetime(2026, 6, 20, 9, 30))

    assert result.status == "success"
    assert store.load_weekly_result().top[0].code == "688001"
    assert {call[0] for call in updater.calls} == {"688001", "688002", "601318"}


def test_daily_top10_judgment_marks_strong_follow_and_persists(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    store.save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-1",
            generated_at="2026-06-20T09:30:00+08:00",
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

    def score_top(stocks, config, generated_at=None):
        return WeeklyRadarResult(
            run_id="daily-1",
            generated_at="2026-06-23T09:45:00+08:00",
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
                    composite_score=90,
                    chan_score=44,
                    volume_score=100,
                    latest_day="2026-06-23",
                    latest_close=84,
                    chan_signal_title="缠论三买",
                    chan_signal_action="buy",
                    volume_entry_ready=True,
                    reason="三买叠加量价确认",
                )
            ],
        )

    service = AutomationService(
        store=store,
        load_catalog=lambda: [],
        load_watchlist=lambda: [],
        update_stock_data=lambda *args, **kwargs: {"status": "skipped"},
        scan_star_radar=score_top,
    )

    judgments = service.run_daily_top10_judgment(now=datetime(2026, 6, 23, 9, 45))

    assert judgments[0].judgment == "strong_follow"
    assert "量价确认" in judgments[0].reason
    assert store.load_daily_judgments("2026-06-23")[0].code == "688001"


def test_manual_trigger_returns_busy_when_lock_is_held(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    service = AutomationService(
        store=store,
        load_catalog=lambda: [],
        load_watchlist=lambda: [],
        update_stock_data=lambda *args, **kwargs: {"status": "skipped"},
        scan_star_radar=lambda stocks, config, generated_at=None: None,
    )
    assert service._lock.acquire(blocking=False)
    try:
        try:
            service.run_weekly_full_maintenance(now=datetime(2026, 6, 20, 9, 30))
        except BusyAutomationError as exc:
            assert "automation task is already running" in str(exc)
        else:
            raise AssertionError("expected BusyAutomationError")
    finally:
        service._lock.release()
