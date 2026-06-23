from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ai_trade_system.agent.system_tools import AgentSystemToolExecutor
from ai_trade_system.automation.models import (
    RadarCandidateScore,
    WeeklyAnalysisItem,
    WeeklyAnalysisResult,
    WeeklyAnalysisSection,
    WeeklyRadarResult,
)
from ai_trade_system.automation.store import AutomationStore
from ai_trade_system.data import write_bars_csv
from ai_trade_system.market import Bar


def _bar(day: date, close: float) -> Bar:
    return Bar(
        symbol="000001",
        exchange="SZSE",
        trading_day=day,
        open_price=close - 0.1,
        high_price=close + 0.3,
        low_price=close - 0.3,
        close_price=close,
        volume=1000,
        turnover=close * 1000,
    )


def _write_sample_csv(path: Path) -> None:
    start = date(2024, 1, 1)
    closes = [10 + index * 0.05 for index in range(80)]
    write_bars_csv([_bar(start + timedelta(days=index), close) for index, close in enumerate(closes)], path)


def _context(csv_path: Path) -> dict:
    return {
        "symbol": "000001",
        "exchange": "SZSE",
        "settings": {
            "symbol": "000001",
            "exchange": "SZSE",
            "start_date": "20240101",
            "end_date": "20240320",
            "csv_path": csv_path.as_posix(),
            "log_path": "logs/agent-paper-events.jsonl",
        },
    }


def _weekly_candidate(code: str, name: str, exchange: str, board: str, rank: int) -> RadarCandidateScore:
    return RadarCandidateScore(
        code=code,
        name=name,
        exchange=exchange,
        board=board,
        rank=rank,
        composite_score=95.0 - rank,
        chan_score=88.0 - rank,
        volume_score=20.0 + rank,
        latest_day="2026-06-18",
        latest_close=30.0 + rank,
        chan_signal_title="缠论多级别日线锚定买入",
        chan_signal_action="buy",
        volume_entry_ready=True,
        reason="日线买点已触发；30m 高确定性反转；15m 风险级别同步转强",
    )


def test_backtest_risk_and_paper_tools_reuse_local_services(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = Path("data/000001_daily.csv")
    _write_sample_csv(csv_path)
    executor = AgentSystemToolExecutor()
    context = _context(csv_path)

    backtest = executor.run("backtest.run", "回测 000001", "weixin", context, {})
    risk = executor.run("risk.evaluate", "风控评估 000001", "weixin", context, {"backtest.run": backtest})
    paper = executor.run("paper.run", "纸面交易 000001", "weixin", context, {"backtest.run": backtest, "risk.evaluate": risk})

    assert backtest["status"] == "ok"
    assert backtest["metrics"]["final_equity"] is not None
    assert risk["status"] == "ok"
    assert "status=passed" in risk["summary"]
    assert "risk_status" in risk
    assert paper["status"] == "ok"
    assert paper["event_count"] > 0


def test_default_strategy_selection_uses_chan_daily_anchor_preset(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    csv_path = Path("data/000001_daily.csv")
    _write_sample_csv(csv_path)
    executor = AgentSystemToolExecutor()
    settings = executor._settings(_context(csv_path))

    selection = executor._strategy({}, settings)

    assert selection.id == "builtin:popular:ChanMultiLevelReversalStrategy"
    assert selection.params["symbol"] == "000001"
    assert selection.params["exchange"] == "SZSE"
    assert selection.params["entry_mode"] == "daily_anchor"
    assert selection.params["confirm_timeframe"] == "60m"
    assert selection.params["risk_timeframe"] == "30m"
    assert selection.params["lower_level_policy"] == "confirm_only"
    assert selection.params["minute_missing_policy"] == "daily_only"
    assert selection.params["max_holding_bars"] == 30


def test_radar_scan_tool_defaults_to_chan_multilevel_daily_anchor(monkeypatch):
    captured: list[str] = []

    def fake_batch_research_signals(request):
        captured.append(request.score_mode)
        return {
            "query": "",
            "universe": "current",
            "score_mode": request.score_mode,
            "scanned": 1,
            "available": 0,
            "missing": 1,
            "data_update": None,
            "rows": [],
        }

    monkeypatch.setattr("ai_trade_system.api.service.batch_research_signals", fake_batch_research_signals)

    result = AgentSystemToolExecutor().run(
        "radar.scan",
        "扫描当前股票",
        "openclaw",
        {"symbol": "000001", "exchange": "SZSE"},
        {},
    )

    assert captured == ["chan_multilevel_daily_anchor"]
    assert result["score_mode"] == "chan_multilevel_daily_anchor"


def test_data_update_tool_summarizes_managed_stock_update(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    class FakeUpdateResult:
        def as_dict(self) -> dict:
            return {
                "code": "000001",
                "name": "000001",
                "exchange": "SZSE",
                "adjust": "qfq",
                "status": "skipped",
                "requested_start": "20240101",
                "requested_end": "20240320",
                "fetched_start": None,
                "fetched_end": None,
                "fetched_rows": 0,
                "latest_rows": 80,
                "latest_start": "2024-01-01",
                "latest_end": "2024-03-20",
                "latest_path": "data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv",
                "increment_path": None,
                "message": "already fresh",
            }

    def fake_update_stock_data(*args, **kwargs):
        return FakeUpdateResult()

    monkeypatch.setattr("ai_trade_system.data_manager.update_stock_data", fake_update_stock_data)
    executor = AgentSystemToolExecutor()

    result = executor.run(
        "data.update",
        "更新 000001 行情",
        "openclaw",
        {"symbol": "000001", "exchange": "SZSE", "settings": {"start_date": "20240101", "end_date": "20240320"}},
        {},
    )

    assert result["status"] == "skipped"
    assert result["file"]["latest_rows"] == 80
    assert "000001" in result["summary"]


def test_weekly_result_tool_reads_current_week_automation_top(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = AutomationStore()
    store.save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-2026-06-18T09:30:00",
            generated_at="2026-06-18T09:30:00",
            status="success",
            total_candidates=3,
            scanned=3,
            missing=0,
            top=[
                RadarCandidateScore(
                    code="688981",
                    name="中芯国际",
                    exchange="SSE",
                    rank=1,
                    composite_score=91.2,
                    chan_score=82.0,
                    volume_score=26.3,
                    latest_day="2026-06-18",
                    latest_close=53.2,
                    chan_signal_title="三买确认",
                    chan_signal_action="buy",
                    volume_entry_ready=True,
                    reason="结构与量能同步改善",
                ),
                RadarCandidateScore(
                    code="688012",
                    name="中微公司",
                    exchange="SSE",
                    rank=2,
                    composite_score=88.4,
                    chan_score=79.1,
                    volume_score=25.2,
                    latest_day="2026-06-18",
                    latest_close=177.6,
                    chan_signal_title="二买修复",
                    chan_signal_action="buy",
                    volume_entry_ready=False,
                    reason="结构偏多但量能未完全确认",
                ),
            ],
        )
    )

    result = AgentSystemToolExecutor().run(
        "automation.weekly_result",
        "给我这周股票扫描结果",
        "weixin",
        {"limit": 1, "now": "2026-06-20T12:00:00"},
        {},
    )

    assert result["status"] == "ok"
    assert result["is_current_week"] is True
    assert result["run_id"] == "weekly-2026-06-18T09:30:00"
    assert result["top_candidates"] == [
        {
            "rank": 1,
            "code": "688981",
            "name": "中芯国际",
            "exchange": "SSE",
            "composite_score": 91.2,
            "chan_score": 82.0,
            "volume_score": 26.3,
            "latest_day": "2026-06-18",
            "latest_close": 53.2,
            "chan_signal_title": "三买确认",
            "chan_signal_action": "buy",
            "volume_entry_ready": True,
            "reason": "结构与量能同步改善",
        }
    ]


def test_weekly_result_tool_auto_runs_scan_when_current_week_result_is_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls: list[str] = []

    def fake_run_automation_weekly() -> dict:
        calls.append("weekly")
        return WeeklyRadarResult(
            run_id="weekly-2026-06-20T10:00:00",
            generated_at="2026-06-20T10:00:00",
            status="success",
            total_candidates=1,
            scanned=1,
            missing=0,
            top=[
                RadarCandidateScore(
                    code="688981",
                    name="中芯国际",
                    exchange="SSE",
                    rank=1,
                    composite_score=91.2,
                    chan_score=82.0,
                    volume_score=26.3,
                    latest_day="2026-06-20",
                    latest_close=53.2,
                    chan_signal_title="三买确认",
                    chan_signal_action="buy",
                    volume_entry_ready=True,
                    reason="结构与量能同步改善",
                )
            ],
        ).as_dict()

    monkeypatch.setattr("ai_trade_system.api.service.run_automation_weekly", fake_run_automation_weekly)

    result = AgentSystemToolExecutor().run(
        "automation.weekly_result",
        "这周的股票扫描分析结论输出给我",
        "weixin",
        {"limit": 1, "now": "2026-06-20T12:00:00"},
        {},
    )

    assert calls == ["weekly"]
    assert result["status"] == "ok"
    assert result["auto_ran_scan"] is True
    assert result["missing_reason"] == "never_scanned"
    assert result["run_id"] == "weekly-2026-06-20T10:00:00"
    assert result["top_candidates"][0]["code"] == "688981"


def test_weekly_result_tool_auto_runs_when_current_week_result_lacks_board_top(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = AutomationStore()
    store.save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-legacy",
            generated_at="2026-06-20T09:30:00",
            status="success",
            total_candidates=20,
            scanned=20,
            missing=0,
            top=[_weekly_candidate("688001", "科创1", "SSE", "star", 1)],
        )
    )
    calls: list[str] = []

    def fake_run_automation_weekly() -> dict:
        calls.append("weekly")
        star = [_weekly_candidate(f"688{index:03d}", f"科创{index}", "SSE", "star", index) for index in range(1, 11)]
        chinext = [
            _weekly_candidate(f"300{index:03d}", f"创业{index}", "SZSE", "chinext", index)
            for index in range(1, 11)
        ]
        return WeeklyRadarResult(
            run_id="weekly-2026-06-20T10:00:00",
            generated_at="2026-06-20T10:00:00",
            status="success",
            total_candidates=20,
            scanned=20,
            missing=0,
            top=star[:10],
            board_top={"star": star, "chinext": chinext},
        ).as_dict()

    monkeypatch.setattr("ai_trade_system.api.service.run_automation_weekly", fake_run_automation_weekly)

    result = AgentSystemToolExecutor().run(
        "automation.weekly_result",
        "这周的股票扫描分析结论输出给我",
        "weixin",
        {"limit": 5, "research_limit": 5, "now": "2026-06-20T12:00:00"},
        {},
    )

    assert calls == ["weekly"]
    assert result["auto_ran_scan"] is True
    assert result["missing_reason"] == "legacy_result_missing_board_top"
    assert result["run_id"] == "weekly-2026-06-20T10:00:00"
    assert result["board_top_counts"] == {"star": 10, "chinext": 10}
    assert len(result["top_candidates"]) == 5
    assert "分板块 科创板 Top10=10 创业板 Top10=10" in result["summary"]


def test_weekly_scan_share_reuses_cached_deep_analysis_before_external_research(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    store = AutomationStore()
    store.save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-2026-06-20T09:30:00",
            generated_at="2026-06-20T09:30:00",
            status="success",
            total_candidates=2,
            scanned=2,
            missing=0,
            top=[
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
                    latest_close=81.09,
                    chan_signal_title="缠论多级别日线锚定买入",
                    chan_signal_action="buy",
                    volume_entry_ready=True,
                    reason="结构买点",
                )
            ],
        )
    )
    store.save_weekly_analysis(
        WeeklyAnalysisResult(
            run_id="analysis-2026-W25",
            weekly_run_id="weekly-2026-06-20T09:30:00",
            generated_at="2026-06-20T09:45:00",
            status="success",
            delivery_channel="weixin",
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
                            scan_reason="日线买点已触发；30m 高确定性反转；15m 风险级别同步转强",
                            analysis_status="ok",
                            summary="缓存中的深度分析结论。",
                            confidence="high",
                            evidence_status="verified",
                            sources=[{"url": "https://example.com/688001"}],
                        )
                    ],
                ),
                WeeklyAnalysisSection(
                    key="chinext",
                    label="创业板 Top10",
                    status="success",
                    summary="创业板 Top10 已完成深度分析。",
                    items=[
                        WeeklyAnalysisItem(
                            rank=1,
                            code="300001",
                            name="特锐德",
                            exchange="SZSE",
                            board="chinext",
                            scan_score=88,
                            latest_day="2026-06-18",
                            scan_signal_title="缠论多级别日线锚定买入",
                            scan_reason="日线买点已触发；30m 高确定性反转；15m 风险级别同步转强",
                            analysis_status="ok",
                            summary="创业板缓存中的深度分析结论。",
                            confidence="high",
                            evidence_status="verified",
                            sources=[{"url": "https://example.com/300001"}],
                        )
                    ],
                ),
            ],
        )
    )

    class FailingOpenClaw:
        def research(self, prompt, context):
            raise AssertionError("should not call external research when weekly analysis cache exists")

    executor = AgentSystemToolExecutor(openclaw=FailingOpenClaw())
    weekly = executor.run(
        "automation.weekly_result",
        "给我这周股票扫描分析结论",
        "weixin",
        {"limit": 10, "now": "2026-06-20T12:00:00"},
        {},
    )
    research = executor.run(
        "research.batch_fundamental",
        "给我这周股票扫描分析结论",
        "weixin",
        {"research_limit": 10},
        {"automation.weekly_result": weekly},
    )
    share = executor.run(
        "share.weixin",
        "给我这周股票扫描分析结论",
        "weixin",
        {},
        {"automation.weekly_result": weekly, "research.batch_fundamental": research},
    )

    assert weekly["analysis_cache"]["run_id"] == "analysis-2026-W25"
    assert research["status"] == "cached"
    assert research["items"][0]["summary"] == "缓存中的深度分析结论。"
    assert "科创板 Top10" in share["message"]
    assert "缓存中的深度分析结论" in share["message"]
    assert "本地缠论：缠论多级别日线锚定买入" in share["message"]
    assert "30m 高确定性反转" in share["message"]


def test_weekly_share_researches_board_top10_when_analysis_cache_is_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    star = [_weekly_candidate(f"688{index:03d}", f"科创{index}", "SSE", "star", index) for index in range(1, 11)]
    chinext = [
        _weekly_candidate(f"300{index:03d}", f"创业{index}", "SZSE", "chinext", index)
        for index in range(1, 11)
    ]
    AutomationStore().save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-2026-06-20T09:30:00",
            generated_at="2026-06-20T09:30:00",
            status="success",
            total_candidates=20,
            scanned=20,
            missing=0,
            top=star[:5],
            board_top={"star": star, "chinext": chinext},
        )
    )

    class FakeOpenClaw:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def research(self, prompt: str, context: dict) -> dict:
            self.calls.append((prompt, dict(context)))
            return {
                "status": "ok",
                "summary": f"{context['name']} 外部资料已核验。",
                "sources": [{"url": f"https://example.com/{context['code']}"}],
                "confidence": "medium",
            }

    openclaw = FakeOpenClaw()
    executor = AgentSystemToolExecutor(openclaw=openclaw)
    weekly = executor.run(
        "automation.weekly_result",
        "这周的股票扫描分析结论输出给我",
        "weixin",
        {"limit": 5, "research_limit": 5, "now": "2026-06-20T12:00:00"},
        {},
    )

    assert len(weekly["top_candidates"]) == 5
    assert len(weekly["board_top"]["star"]) == 10
    assert len(weekly["board_top"]["chinext"]) == 10

    research = executor.run(
        "research.batch_fundamental",
        "这周的股票扫描分析结论输出给我",
        "weixin",
        {"research_limit": 5},
        {"automation.weekly_result": weekly},
    )
    share = executor.run(
        "share.weixin",
        "这周的股票扫描分析结论输出给我",
        "weixin",
        {},
        {"automation.weekly_result": weekly, "research.batch_fundamental": research},
    )

    assert research["requested"] == 20
    assert research["researched"] == 20
    assert [section["label"] for section in research["sections"]] == ["科创板 Top10", "创业板 Top10"]
    assert [context["code"] for _prompt, context in openclaw.calls[:2]] == ["688001", "688002"]
    assert all("缠论多级联动" in prompt for prompt, _context in openclaw.calls)
    assert "30m 高确定性反转" in openclaw.calls[0][0]
    assert "30m 高确定性反转" in research["sections"][0]["items"][0]["chan_multilevel_basis"]
    assert share["item_count"] == 20
    assert "科创板 Top10" in share["message"]
    assert "创业板 Top10" in share["message"]
    assert "本地缠论：缠论多级别日线锚定买入" in share["message"]
    assert "30m 高确定性反转" in share["message"]


def test_batch_fundamental_tool_researches_weekly_candidates_with_openclaw():
    class FakeOpenClaw:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def research(self, prompt: str, context: dict) -> dict:
            self.calls.append((prompt, dict(context)))
            return {
                "status": "ok",
                "summary": f"{context['name']} 外部研究摘要",
                "sources": [{"type": "web_search", "title": context["code"], "url": f"https://example.com/{context['code']}"}],
                "confidence": "medium",
            }

    weekly_output = {
        "status": "ok",
        "top_candidates": [
            {"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE", "composite_score": 91.2},
            {"rank": 2, "code": "688012", "name": "中微公司", "exchange": "SSE", "composite_score": 88.4},
        ],
    }
    openclaw = FakeOpenClaw()
    result = AgentSystemToolExecutor(openclaw=openclaw).run(
        "research.batch_fundamental",
        "分析这周优质股票的基本面和信息面",
        "weixin",
        {"research_limit": 2},
        {"automation.weekly_result": weekly_output},
    )

    assert result["status"] == "ok"
    assert result["researched"] == 2
    assert [call[1]["symbol"] for call in openclaw.calls] == ["688981", "688012"]
    assert result["items"][0]["summary"] == "中芯国际 外部研究摘要"
    assert result["items"][0]["sources"] == [{"type": "web_search", "title": "688981", "url": "https://example.com/688981"}]


def test_batch_fundamental_tool_requires_external_evidence_for_ok_research():
    class FakeOpenClaw:
        def research(self, prompt: str, context: dict) -> dict:
            return {
                "status": "ok",
                "summary": "看起来基本面很好，但没有任何外部来源。",
                "sources": [{"type": "openclaw_agent", "run_id": "run-1"}],
                "confidence": "medium",
            }

    weekly_output = {
        "status": "ok",
        "top_candidates": [
            {"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE", "composite_score": 91.2},
        ],
    }

    result = AgentSystemToolExecutor(openclaw=FakeOpenClaw()).run(
        "research.batch_fundamental",
        "分析这周优质股票的基本面和信息面",
        "weixin",
        {"research_limit": 1},
        {"automation.weekly_result": weekly_output},
    )

    assert result["status"] == "failed"
    assert result["items"][0]["status"] == "failed"
    assert result["items"][0]["confidence"] == "low"
    assert result["items"][0]["evidence_status"] == "missing_external_evidence"
    assert "外部证据不足" in result["items"][0]["summary"]


def test_weixin_share_tool_prepares_final_weekly_report_message():
    previous_outputs = {
        "automation.weekly_result": {
            "status": "ok",
            "run_id": "weekly-2026-06-18T09:30:00",
            "generated_at": "2026-06-18T09:30:00",
            "top_candidates": [
                {"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE", "composite_score": 91.2, "reason": "结构与量能同步改善"},
            ],
        },
        "research.batch_fundamental": {
            "status": "ok",
            "items": [
                {
                    "code": "688981",
                    "name": "中芯国际",
                    "exchange": "SSE",
                    "status": "ok",
                    "summary": "外部研究摘要",
                    "confidence": "medium",
                }
            ],
        },
    }

    result = AgentSystemToolExecutor().run("share.weixin", "完成分享", "weixin", {}, previous_outputs)

    assert result["status"] == "prepared"
    assert result["delivery"] == "agent_response"
    assert "weekly-2026-06-18T09:30:00" in result["message"]
    assert "1. 中芯国际(688981.SSE)" in result["message"]
    assert "外部研究摘要" in result["message"]


def test_weixin_share_tool_prepares_compact_weekly_report_message():
    long_body = "\n".join(
        [
            "**688981（中芯国际）— 基本面和信息面研究摘要**",
            "",
            "主营业务：这是一段应出现在摘要里的短句。",
            "财务质量：" + "长正文" * 300,
            "公告与新闻：" + "更多长正文" * 300,
            "研究结论：这段完整正文不应全部进入微信消息。",
        ]
    )
    previous_outputs = {
        "automation.weekly_result": {
            "status": "ok",
            "run_id": "weekly-2026-06-20T17:39:46",
            "generated_at": "2026-06-20T17:39:46",
            "source_path": "data/automation/star_radar_top10.json",
            "top_candidates": [
                {"rank": 1, "code": "688981", "name": "中芯国际", "exchange": "SSE", "composite_score": 91.2, "reason": "结构与量能同步改善"},
                {"rank": 2, "code": "688012", "name": "中微公司", "exchange": "SSE", "composite_score": 88.4, "reason": "趋势通过"},
            ],
        },
        "research.batch_fundamental": {
            "status": "ok",
            "items": [
                {
                    "rank": 1,
                    "code": "688981",
                    "name": "中芯国际",
                    "exchange": "SSE",
                    "status": "ok",
                    "summary": long_body,
                    "confidence": "medium",
                }
            ],
        },
    }

    result = AgentSystemToolExecutor().run(
        "share.weixin",
        "这周的股票扫描分析结论输出给我",
        "weixin",
        {"report_path": "reports/agt_demo.json"},
        previous_outputs,
    )

    assert result["status"] == "prepared"
    assert result["researched_item_count"] == 1
    assert result["scan_only_item_count"] == 1
    assert result["message_chars"] <= 1800
    assert result["full_report_hint"] == "reports/agt_demo.json"
    assert "深度研究候选" in result["message"]
    assert "仅扫描候选" in result["message"]
    assert "中微公司(688012.SSE)：综合分 88.40；趋势通过" in result["message"]
    assert "主营业务：这是一段应出现在摘要里的短句。" in result["message"]
    assert "更多长正文" not in result["message"]
    assert "完整报告：reports/agt_demo.json" in result["message"]
