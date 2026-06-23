from __future__ import annotations

from datetime import datetime

from ai_trade_system.automation.analysis import analyze_weekly_radar_result
from ai_trade_system.automation.models import (
    AutomationConfig,
    AutomationRunRecord,
    RadarCandidateScore,
    WeeklyAnalysisItem,
    WeeklyAnalysisResult,
    WeeklyAnalysisSection,
    WeeklyRadarResult,
)
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


def test_weekly_analysis_prompt_and_message_include_chan_multilevel_basis():
    captured: list[tuple[str, dict]] = []

    def analyzer(prompt: str, context: dict) -> dict:
        captured.append((prompt, dict(context)))
        return {
            "status": "ok",
            "summary": "外部资料已核验，技术结构以本地缠论多级联动为准。",
            "sources": [{"url": "https://example.com/688001"}],
            "confidence": "high",
        }

    weekly = WeeklyRadarResult(
        run_id="weekly-2026-W25",
        generated_at="2026-06-20T09:30:00",
        status="success",
        total_candidates=1,
        scanned=1,
        missing=0,
        top=[],
        board_top={
            "star": [
                RadarCandidateScore(
                    code="688001",
                    name="华兴源创",
                    exchange="SSE",
                    board="star",
                    rank=1,
                    composite_score=94,
                    chan_score=91,
                    volume_score=28,
                    latest_day="2026-06-18",
                    latest_close=81.09,
                    chan_signal_title="缠论多级别日线锚定买入",
                    chan_signal_action="buy",
                    volume_entry_ready=True,
                    reason="日线买点已触发；30m 高确定性反转；15m 风险级别同步转强",
                )
            ]
        },
    )

    result = analyze_weekly_radar_result(
        weekly,
        config=AutomationConfig(),
        generated_at="2026-06-20T09:40:00",
        analyzer=analyzer,
    )

    assert captured
    assert "缠论多级联动" in captured[0][0]
    assert "30m 高确定性反转" in captured[0][0]
    assert "15m 风险级别同步转强" in captured[0][0]
    assert result.sections[0].items[0].chan_multilevel_basis.startswith("缠论多级联动")
    assert "本地缠论：" in result.message
    assert "30m 高确定性反转" in result.message


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


def test_weekly_full_maintenance_generates_analysis_cache_and_notification(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    analyzed: list[str] = []
    notified: list[str] = []

    def scan(stocks_by_board, config, generated_at=None):
        assert set(stocks_by_board) == {"star", "chinext"}
        star = list(stocks_by_board["star"])
        chinext = list(stocks_by_board["chinext"])
        return WeeklyRadarResult(
            run_id="weekly-2026-W25",
            generated_at=generated_at or "2026-06-20T09:30:00",
            status="success",
            total_candidates=len(star) + len(chinext),
            scanned=2,
            missing=0,
            top=[],
            board_top={
                "star": [
                    RadarCandidateScore(
                        code="688001",
                        name="华兴源创",
                        exchange="SSE",
                        board="star",
                        rank=1,
                        composite_score=94,
                        chan_score=94,
                        volume_score=0,
                        latest_day="2026-06-18",
                        latest_close=81,
                        chan_signal_title="缠论多级别日线锚定买入",
                        chan_signal_action="buy",
                        volume_entry_ready=True,
                        reason="科创板结构买点",
                    )
                ],
                "chinext": [
                    RadarCandidateScore(
                        code="300432",
                        name="富临精工",
                        exchange="SZSE",
                        board="chinext",
                        rank=1,
                        composite_score=94,
                        chan_score=94,
                        volume_score=0,
                        latest_day="2026-06-18",
                        latest_close=22.86,
                        chan_signal_title="缠论多级别日线锚定买入",
                        chan_signal_action="buy",
                        volume_entry_ready=True,
                        reason="创业板结构买点",
                    )
                ],
            },
        )

    def analyze(weekly, *, config, generated_at=None):
        analyzed.append(weekly.run_id)
        return WeeklyAnalysisResult(
            run_id="analysis-2026-W25",
            weekly_run_id=weekly.run_id,
            generated_at=generated_at or "2026-06-20T09:40:00",
            status="success",
            delivery_channel=config.weekly_delivery_channel,
            sections=[
                WeeklyAnalysisSection(
                    key="star",
                    label="科创板 Top10",
                    status="success",
                    summary="科创板 Top10 已完成深度分析。",
                    items=[
                        WeeklyAnalysisItem(
                            rank=1,
                            code="688001",
                            name="华兴源创",
                            exchange="SSE",
                            board="star",
                            scan_score=94,
                            latest_day="2026-06-18",
                            scan_signal_title="缠论多级别日线锚定买入",
                            scan_reason="科创板结构买点",
                            analysis_status="ok",
                            summary="深度分析摘要",
                            confidence="high",
                            evidence_status="verified",
                            sources=[{"url": "https://example.com/688001"}],
                        )
                    ],
                )
            ],
        )

    def notify(analysis, *, config):
        notified.append(config.weekly_delivery_channel)
        return {"status": "ok", "summary": "sent"}

    service = AutomationService(
        store=store,
        load_catalog=lambda: [
            StockInfo("688001", "华兴源创", "SSE"),
            StockInfo("300432", "富临精工", "SZSE"),
        ],
        load_watchlist=lambda: [],
        update_stock_data=lambda *args, **kwargs: {"status": "skipped"},
        scan_weekly_radar=scan,
        analyze_weekly_result=analyze,
        notify_weekly_analysis=notify,
    )

    result = service.run_weekly_full_maintenance(now=datetime(2026, 6, 20, 9, 30))

    assert result.run_id == "weekly-2026-W25"
    assert analyzed == ["weekly-2026-W25"]
    assert notified == ["weixin"]
    analysis = store.load_weekly_analysis("2026-W25")
    assert analysis.weekly_run_id == "weekly-2026-W25"
    assert analysis.delivery_status == "ok"
    assert store.load_state()["last_weekly_analysis_run"] == "analysis-2026-W25"


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


def test_status_includes_recent_runs_and_failure_diagnostics(tmp_path):
    store = AutomationStore(root=tmp_path / "data" / "automation", log_root=tmp_path / "logs" / "automation")
    store.append_run(
        AutomationRunRecord(
            run_id="weekly-old",
            task="weekly",
            status="success",
            started_at="2026-06-13T09:30:00",
            finished_at="2026-06-13T09:31:00",
            message="success",
        )
    )
    store.append_run(
        AutomationRunRecord(
            run_id="daily-failed",
            task="daily",
            status="failed",
            started_at="2026-06-20T09:45:00",
            finished_at="2026-06-20T09:46:00",
            message="AKShare timeout",
        )
    )
    store.save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-partial",
            generated_at="2026-06-20T09:30:00",
            status="partial",
            total_candidates=12,
            scanned=8,
            missing=4,
            top=[],
        )
    )
    service = AutomationService(
        store=store,
        load_catalog=lambda: [],
        load_watchlist=lambda: [],
        update_stock_data=lambda *args, **kwargs: {"status": "skipped"},
        scan_star_radar=lambda stocks, config, generated_at=None: None,
    )

    status = service.status()
    payload = status.as_dict()

    assert [run["run_id"] for run in payload["recent_runs"]] == ["daily-failed", "weekly-old"]
    diagnostics = payload["diagnostics"]
    assert diagnostics[0]["code"] == "RUN_FAILED"
    assert "AKShare timeout" in diagnostics[0]["message"]
    assert any(item["code"] == "MISSING_DATA" and "4" in item["message"] for item in diagnostics)
