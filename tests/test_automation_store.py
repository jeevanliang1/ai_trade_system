from __future__ import annotations

from ai_trade_system.automation.models import (
    AutomationConfig,
    AutomationRunRecord,
    DailyJudgment,
    RadarCandidateScore,
    WeeklyRadarResult,
)
from ai_trade_system.automation.store import AutomationStore


def test_automation_store_returns_defaults_when_files_are_missing(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")

    config = store.load_config()
    status = store.load_state()

    assert config.enabled is True
    assert config.weekly_weekday == 5
    assert config.top_n == 10
    assert config.volume_weight == 0.35
    assert status["last_weekly_run"] is None
    assert status["last_daily_run"] is None


def test_automation_store_round_trips_config_top10_judgments_and_runs(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    config = AutomationConfig(enabled=False, top_n=5, volume_weight=0.5)
    candidate = RadarCandidateScore(
        code="688001",
        name="华兴源创",
        exchange="SSE",
        rank=1,
        composite_score=70.1,
        chan_score=44.0,
        volume_score=74.7,
        latest_day="2026-06-18",
        latest_close=81.09,
        chan_signal_title="缠论三买",
        chan_signal_action="buy",
        volume_entry_ready=False,
        reason="三买结构，量能不足",
    )
    weekly = WeeklyRadarResult(
        run_id="weekly-1",
        generated_at="2026-06-20T09:30:00+08:00",
        status="success",
        total_candidates=1,
        scanned=1,
        missing=0,
        top=[candidate],
    )
    judgment = DailyJudgment(
        code="688001",
        name="华兴源创",
        exchange="SSE",
        judgment="watch_only",
        reason="三买结构仍在，量能未确认",
        current_score=70.1,
        baseline_score=70.1,
        latest_day="2026-06-23",
        latest_close=82.0,
        chan_signal_title="缠论三买",
        volume_entry_ready=False,
    )
    run = AutomationRunRecord(
        run_id="run-1",
        task="weekly",
        status="success",
        started_at="2026-06-20T09:30:00+08:00",
        finished_at="2026-06-20T09:31:00+08:00",
        message="ok",
    )

    store.save_config(config)
    store.save_weekly_result(weekly)
    store.save_daily_judgments("2026-06-23", [judgment])
    store.append_run(run)

    assert store.load_config().top_n == 5
    assert store.load_config().enabled is False
    assert store.load_weekly_result().top[0].code == "688001"
    assert store.load_daily_judgments("2026-06-23")[0].judgment == "watch_only"
    assert store.load_runs()[-1].task == "weekly"
