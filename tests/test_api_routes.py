from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient
from time import monotonic, sleep

from ai_trade_system import data_manager
from ai_trade_system.automation.models import RadarCandidateScore, WeeklyRadarResult
from ai_trade_system.api import service
from ai_trade_system.api.app import create_app
from ai_trade_system.data import write_bars_csv
from ai_trade_system.data_manager import DataUpdateResult, data_file_for_stock
from ai_trade_system.market import Bar
from ai_trade_system.stock_catalog import StockInfo, write_stock_catalog
from ai_trade_system.watchlist import save_watchlist


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AI_TRADE_OPENCLAW_RESEARCH_COMMAND", "")
    monkeypatch.setenv("AI_TRADE_OPENCLAW_NOTIFY_COMMAND", "")
    monkeypatch.setenv("AI_TRADE_LLM_PROVIDER", "mock")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    service._AUTOMATION_SERVICE = None
    service._AUTOMATION_SCHEDULER = None
    service._AGENT_ORCHESTRATOR = None
    service._AGENT_QUEUE = None
    service._AGENT_GOVERNANCE = None
    service._REALTIME_MONITOR = None
    return TestClient(create_app())


def test_app_lifespan_starts_and_stops_automation_scheduler(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    events: list[str] = []

    class FakeScheduler:
        def start(self) -> None:
            events.append("start")

        def stop(self) -> None:
            events.append("stop")

    monkeypatch.setattr(service, "get_automation_scheduler", lambda: FakeScheduler())

    with TestClient(create_app()) as client:
        assert events == ["start"]
        assert client.get("/api/automation/status").status_code == 200

    assert events == ["start", "stop"]


def _strategy_payload() -> dict:
    return {
        "id": "builtin:popular:ChanStructureStrategy",
        "params": {"symbol": "000001", "trade_size": 100},
    }


def _settings_payload() -> dict:
    return {
        "symbol": "000001",
        "exchange": "SZSE",
        "start_date": "20220101",
        "end_date": "20250516",
        "adjust": "qfq",
        "timeframe": "daily",
        "csv_path": "data/000001_daily.csv",
        "log_path": "logs/paper_events.jsonl",
        "initial_cash": 100000.0,
        "commission_rate": 0.0003,
        "slippage": 0.01,
        "max_order_cash": 50000.0,
        "max_drawdown_pct": 20.0,
        "min_cash_balance": 0.0,
        "max_position_shares": 50000,
    }


def test_realtime_routes_start_status_events_and_stop(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    class FakeRealtimeMonitor:
        def __init__(self):
            self.started = False
            self.started_payload = None

        def start(self, **kwargs):
            self.started = True
            self.started_payload = kwargs
            return self.status()

        def stop(self):
            self.started = False
            return self.status()

        def status(self):
            return {
                "running": self.started,
                "started_at": "2026-06-22T10:00:00" if self.started else None,
                "stopped_at": None if self.started else "2026-06-22T10:01:00",
                "strategy_id": "builtin:popular:ChanStructureStrategy" if self.started else None,
                "symbols": ["000001.SZSE", "AAPL.NASDAQ", "BTCUSDT.CRYPTO"] if self.started else [],
                "stock_markets": {"000001.SZSE": "a_share", "AAPL.NASDAQ": "us_stock", "BTCUSDT.CRYPTO": "crypto"} if self.started else {},
                "market_counts": {"a_share": 1, "us_stock": 1, "crypto": 1} if self.started else {},
                "timeframe": "1m" if self.started else None,
                "poll_interval_seconds": 1 if self.started else None,
                "event_count": 1 if self.started else 0,
                "last_event_at": "2026-06-22T10:00:00" if self.started else None,
                "last_bar_time": None,
                "last_error": None,
            }

        def events(self, limit=100):
            assert limit == 25
            return [
                {
                    "id": "evt-1",
                    "event": "monitor_started",
                    "created_at": "2026-06-22T10:00:00",
                    "symbols": ["000001.SZSE"],
                    "timeframe": "1m",
                }
            ]

    fake = FakeRealtimeMonitor()
    monkeypatch.setattr(service, "get_realtime_monitor_service", lambda: fake)

    start_response = client.post(
        "/api/realtime/start",
        json={
            "settings": {**_settings_payload(), "timeframe": "1m"},
            "strategy": _strategy_payload(),
            "poll_interval_seconds": 1,
            "market_sources": ["a_share", "us_stock", "crypto"],
        },
    )
    assert start_response.status_code == 200
    assert start_response.json()["running"] is True
    assert fake.started_payload["stocks"][0].code == "000001"
    assert [stock.code for stock in fake.started_payload["stocks"]] == ["000001", "AAPL", "BTCUSDT"]
    assert fake.started_payload["stock_markets"] == {
        "000001.SZSE": "a_share",
        "AAPL.NASDAQ": "us_stock",
        "BTCUSDT.CRYPTO": "crypto",
    }
    assert fake.started_payload["market_counts"] == {"a_share": 1, "us_stock": 1, "crypto": 1}

    status_response = client.get("/api/realtime/status")
    assert status_response.status_code == 200
    assert status_response.json()["symbols"] == ["000001.SZSE", "AAPL.NASDAQ", "BTCUSDT.CRYPTO"]
    assert status_response.json()["market_counts"] == {"a_share": 1, "us_stock": 1, "crypto": 1}

    events_response = client.get("/api/realtime/events?limit=25")
    assert events_response.status_code == 200
    assert events_response.json()["events"][0]["event"] == "monitor_started"

    stop_response = client.post("/api/realtime/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["running"] is False


def test_realtime_start_can_monitor_watchlist_and_weekly_quality_batches(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    save_watchlist(
        [
            StockInfo("000001", "平安银行", "SZSE"),
            StockInfo("600519", "贵州茅台", "SSE"),
        ]
    )
    service.get_automation_service().store.save_weekly_result(
        WeeklyRadarResult(
            run_id="weekly-1",
            generated_at="2026-06-22T09:30:00",
            status="success",
            total_candidates=2,
            scanned=2,
            missing=0,
            top=[
                _weekly_candidate("688981", "中芯国际", "SSE", rank=1),
                _weekly_candidate("600519", "贵州茅台", "SSE", rank=2),
            ],
        )
    )

    class FakeRealtimeMonitor:
        def __init__(self):
            self.started_payload = None

        def start(self, **kwargs):
            self.started_payload = kwargs
            return {
                "running": True,
                "started_at": "2026-06-22T10:00:00",
                "stopped_at": None,
                "strategy_id": kwargs["strategy_id"],
                "symbols": [f"{stock.code}.{stock.exchange}" for stock in kwargs["stocks"]],
                "source_counts": kwargs["source_counts"],
                "timeframe": kwargs["timeframe"],
                "poll_interval_seconds": kwargs["poll_interval_seconds"],
                "event_count": 1,
                "last_event_at": "2026-06-22T10:00:00",
                "last_bar_time": None,
                "last_error": None,
            }

    fake = FakeRealtimeMonitor()
    monkeypatch.setattr(service, "get_realtime_monitor_service", lambda: fake)

    response = client.post(
        "/api/realtime/start",
        json={
            "settings": {**_settings_payload(), "timeframe": "1m"},
            "strategy": _strategy_payload(),
            "poll_interval_seconds": 1,
            "monitor_sources": ["watchlist", "weekly_quality"],
        },
    )

    assert response.status_code == 200
    assert response.json()["symbols"] == ["000001.SZSE", "600519.SSE", "688981.SSE"]
    assert response.json()["source_counts"] == {"watchlist": 2, "weekly_quality": 2}
    assert fake.started_payload["stock_sources"] == {
        "000001.SZSE": ["watchlist"],
        "600519.SSE": ["watchlist", "weekly_quality"],
        "688981.SSE": ["weekly_quality"],
    }


def _weekly_candidate(code: str, name: str, exchange: str, rank: int) -> RadarCandidateScore:
    return RadarCandidateScore(
        code=code,
        name=name,
        exchange=exchange,
        rank=rank,
        composite_score=80.0 - rank,
        chan_score=60.0,
        volume_score=20.0,
        latest_day="2026-06-19",
        latest_close=10.0,
        chan_signal_title="观察",
        chan_signal_action="watch",
        volume_entry_ready=True,
        reason="weekly quality candidate",
    )


def _bar(symbol: str, exchange: str, day: date, close: float, volume: float = 1000) -> Bar:
    return Bar(
        symbol=symbol,
        exchange=exchange,
        trading_day=day,
        open_price=close - 0.2,
        high_price=close + 0.4,
        low_price=close - 0.5,
        close_price=close,
        volume=volume,
        turnover=close * volume,
    )


def _write_managed_bars(stock: StockInfo, closes: list[float], volumes: list[float] | None = None) -> Path:
    data_file = data_file_for_stock(stock, adjust="qfq")
    start = date(2026, 1, 1)
    bar_volumes = volumes or [1000.0] * len(closes)
    write_bars_csv(
        [
            _bar(stock.code, stock.exchange, start + timedelta(days=index), close, bar_volumes[index])
            for index, close in enumerate(closes)
        ],
        data_file.latest_path,
    )
    return data_file.latest_path


def _momentum_closes(start: float, end: float, count: int = 80) -> list[float]:
    step = (end - start) / (count - 1)
    return [round(start + step * index, 2) for index in range(count)]


def _chan_structure_closes() -> list[float]:
    return [
        10.0,
        9.0,
        10.0,
        11.0,
        12.0,
        13.0,
        14.0,
        15.0,
        14.0,
        13.0,
        12.0,
        11.0,
        10.0,
        9.0,
        10.0,
        11.0,
        12.0,
        13.0,
        14.0,
        15.0,
        14.0,
        13.0,
        12.0,
        11.0,
        10.0,
        9.5,
        10.5,
        11.5,
        12.5,
        13.5,
        14.5,
        16.0,
        15.0,
        14.0,
        13.0,
        12.0,
        11.0,
        10.5,
        11.0,
        12.0,
        13.0,
    ] * 2


def test_bootstrap_returns_defaults_and_strategy_metadata(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["symbol"] == ""
    assert payload["settings"]["exchange"] == ""
    assert payload["settings"]["csv_path"] == ""
    assert payload["watchlist"] == []
    assert payload["catalog_available"] is True
    assert payload["strategies"][0]["id"].startswith("builtin:")
    assert payload["strategies"][0]["display_name"]
    assert payload["strategies"][0]["description"]
    assert payload["strategies"][0]["parameters"]
    assert payload["strategies"][0]["name"] == "ChanRsiResearchStrategy"
    trade_size = next(parameter for parameter in payload["strategies"][0]["parameters"] if parameter["name"] == "trade_size")
    assert trade_size["display_name"] == "每次交易股数"
    assert "仓位" in trade_size["increase_effect"]


def test_agent_routes_create_list_show_and_approve_tasks(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    tools_response = client.get("/api/agent/tools")
    assert tools_response.status_code == 200
    assert {tool["name"] for tool in tools_response.json()["tools"]} >= {
        "system.snapshot",
        "research.fundamental",
        "data.update",
        "radar.scan",
        "backtest.run",
        "risk.evaluate",
        "paper.run",
        "agent.report",
    }

    create_response = client.post(
        "/api/agent/tasks",
        json={
            "prompt": "帮我研究 000001 最近是否值得关注",
            "source": "weixin",
            "context": {"symbol": "000001", "exchange": "SZSE"},
        },
    )
    assert create_response.status_code == 200
    task = create_response.json()["task"]
    assert task["status"] in {"queued", "running", "waiting_confirmation"}
    assert task["source"] == "weixin"
    task = _wait_for_agent_status(client, task["task_id"], {"waiting_confirmation"})
    assert task["confirmations"][0]["tool_name"] == "research.fundamental"

    approve_research = client.post(f"/api/agent/tasks/{task['task_id']}/approve", json={"approval": "approved"})
    assert approve_research.status_code == 200
    task = _wait_for_agent_status(client, task["task_id"], {"completed"})
    assert task["report_path"].startswith("reports/")

    list_response = client.get("/api/agent/tasks")
    assert list_response.status_code == 200
    assert list_response.json()["tasks"][0]["task_id"] == task["task_id"]

    detail_response = client.get(f"/api/agent/tasks/{task['task_id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["task"]["prompt"] == "帮我研究 000001 最近是否值得关注"

    trace_response = client.get(f"/api/agent/tasks/{task['task_id']}/trace")
    assert trace_response.status_code == 200
    trace_payload = trace_response.json()
    assert trace_payload["task_id"] == task["task_id"]
    assert "request_received" in [event["type"] for event in trace_payload["events"]]
    assert any(event["type"] == "tool_finished" and event["tool_name"] == "agent.report" for event in trace_payload["events"])

    blocked_response = client.post(
        "/api/agent/tasks",
        json={"prompt": "帮我实盘买入 000001 一万块", "source": "openclaw"},
    )
    blocked = blocked_response.json()["task"]
    assert blocked["status"] == "blocked"
    assert blocked["confirmations"][0]["code"] == "LIVE_TRADING_BLOCKED"

    approve_response = client.post(f"/api/agent/tasks/{blocked['task_id']}/approve", json={"approval": "rejected"})
    assert approve_response.status_code == 200
    assert approve_response.json()["task"]["confirmations"][0]["status"] == "blocked"


def test_agent_governance_routes_manage_memory_skill_policy_and_preview(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    memories_response = client.get("/api/agent/governance/memories")
    assert memories_response.status_code == 200
    assert any(memory["id"] == "mem_weekly_scan_reuse" for memory in memories_response.json()["memories"])

    create_memory = client.post(
        "/api/agent/governance/memories",
        json={
            "id": "mem_user_pref_top3",
            "type": "preference",
            "scope": "agent",
            "title": "默认看前三",
            "content": "用户默认关注周榜前三。",
            "tags": ["weekly", "preference"],
            "source": "user",
            "confidence": "high",
            "enabled": True,
        },
    )
    assert create_memory.status_code == 200
    assert create_memory.json()["memory"]["title"] == "默认看前三"

    update_memory = client.put(
        "/api/agent/governance/memories/mem_user_pref_top3",
        json={"title": "默认看前五", "enabled": False},
    )
    assert update_memory.status_code == 200
    assert update_memory.json()["memory"]["title"] == "默认看前五"
    assert update_memory.json()["memory"]["enabled"] is False

    skills_response = client.get("/api/agent/governance/skills")
    assert skills_response.status_code == 200
    assert any(skill["id"] == "weekly_scan_share" for skill in skills_response.json()["skills"])

    create_skill = client.post(
        "/api/agent/governance/skills",
        json={
            "id": "risk_first_review",
            "title": "先风控复核",
            "description": "对输入指标先做风险检查。",
            "trigger_terms": ["先风控", "风险复核"],
            "steps": ["risk.evaluate"],
            "allowed_tools": ["risk.evaluate"],
            "required_confirmations": [],
            "output_format": "risk_report",
            "enabled": True,
        },
    )
    assert create_skill.status_code == 200
    assert create_skill.json()["skill"]["steps"] == ["risk.evaluate"]

    policy_response = client.get("/api/agent/governance/policy")
    assert policy_response.status_code == 200
    assert policy_response.json()["policy"]["tool_permissions"]["research.batch_fundamental"] == "confirm"

    update_policy = client.put(
        "/api/agent/governance/policy",
        json={"max_steps": 6, "tool_permissions": {"share.weixin": "confirm"}},
    )
    assert update_policy.status_code == 200
    assert update_policy.json()["policy"]["max_steps"] == 6
    assert update_policy.json()["policy"]["tool_permissions"]["share.weixin"] == "confirm"

    preview_response = client.post(
        "/api/agent/governance/plan-preview",
        json={"prompt": "给我这周股票扫描结果并完成分享的最终结果", "context": {"source": "weixin"}},
    )
    assert preview_response.status_code == 200
    preview = preview_response.json()["preview"]
    assert preview["selected_skill"]["id"] == "weekly_scan_share"
    assert [step["tool"] for step in preview["steps"]] == ["automation.weekly_result", "research.batch_fundamental", "share.weixin"]
    assert preview["steps"][1]["permission"] == "confirm"

    delete_response = client.delete("/api/agent/governance/memories/mem_user_pref_top3")
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


def _wait_for_agent_status(client: TestClient, task_id: str, statuses: set[str]) -> dict:
    deadline = monotonic() + 3
    latest: dict | None = None
    while monotonic() < deadline:
        response = client.get(f"/api/agent/tasks/{task_id}")
        assert response.status_code == 200
        latest = response.json()["task"]
        if latest["status"] in statuses:
            return latest
        sleep(0.05)
    raise AssertionError(f"Agent task {task_id} did not reach {statuses}; latest={latest}")


def test_bootstrap_returns_portfolio_presets_for_strategy_combinations(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    presets = payload["portfolio_presets"]
    research = next(preset for preset in presets if preset["id"] == "chan_research_stack")

    assert research["name"] == "缠论研究组合"
    assert research["mode"] == "weighted_vote"
    assert "缠论结构" in research["description"]
    assert len(research["allocations"]) == 2
    strategy_ids = [allocation["strategy"]["id"] for allocation in research["allocations"]]
    assert "builtin:popular:ChanStructureStrategy" in strategy_ids
    assert "builtin:popular:ChanRsiResearchStrategy" in strategy_ids
    assert research["allocations"][0]["strategy"]["params"]["symbol"] == ""
    assert research["allocations"][0]["weight"] > 0
    assert research["allocations"][0]["enabled"] is True
    assert {preset["id"] for preset in presets} == {
        "chan_research_stack",
        "chan_offensive_fusion_stack",
        "chan_multilevel_execution_stack",
    }
    offensive = next(preset for preset in presets if preset["id"] == "chan_offensive_fusion_stack")

    assert offensive["name"] == "缠论进攻融合组合"
    assert offensive["mode"] == "primary_assist"
    assert "进攻" in offensive["description"]
    assert offensive["allocations"][0]["strategy"]["id"] == "builtin:popular:ChanVolumeFusionStrategy"
    assert offensive["allocations"][0]["weight"] > offensive["allocations"][1]["weight"]
    assert offensive["allocations"][0]["strategy"]["params"]["symbol"] == ""
    assert offensive["allocations"][0]["strategy"]["params"]["weak_volume_requires_trend_break"] is True
    assert offensive["allocations"][0]["strategy"]["params"]["high_confidence_units"] == 2
    assert offensive["allocations"][0]["strategy"]["params"]["max_units"] == 3
    assert offensive["allocations"][0]["strategy"]["params"]["severe_weak_momentum_pct"] == -0.04
    multilevel = next(preset for preset in presets if preset["id"] == "chan_multilevel_execution_stack")
    assert multilevel["allocations"][0]["strategy"]["id"] == "builtin:popular:ChanMultiLevelReversalStrategy"


def test_portfolio_preview_accepts_bootstrap_preset_allocations(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 120})
    assert demo_response.status_code == 200
    bootstrap = client.get("/api/bootstrap").json()
    preset = next(item for item in bootstrap["portfolio_presets"] if item["id"] == "chan_research_stack")

    preview_response = client.post(
        "/api/portfolio/preview",
        json={
            "settings": settings,
            "portfolio": {
                "allocations": [
                    {"strategy": allocation["strategy"], "weight": allocation["weight"], "enabled": allocation["enabled"]}
                    for allocation in preset["allocations"]
                ],
                "mode": preset["mode"],
                "ai_adjust": False,
                "ai_direction": None,
            },
        },
    )

    assert preview_response.status_code == 200
    payload = preview_response.json()
    assert payload["allocations"][0]["name"] == "缠论结构策略"
    assert len(payload["allocations"]) == len(preset["allocations"])
    assert payload["breakdown"]["mode"] == "weighted_vote"


def test_default_settings_use_five_year_range_from_current_date():
    settings = service.default_settings(today=date(2026, 6, 18))

    assert settings.start_date == "20210618"
    assert settings.end_date == "20260618"


def test_watchlist_routes_persist_local_stock_configuration(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    empty_response = client.get("/api/watchlist")
    assert empty_response.status_code == 200
    assert empty_response.json() == {"stocks": []}

    save_response = client.put(
        "/api/watchlist",
        json={
            "stocks": [
                {"code": "601318", "name": "中国平安", "exchange": "sse"},
                {"code": "601318", "name": "中国平安", "exchange": "SSE"},
                {"code": "000001", "name": "平安银行", "exchange": "SZSE"},
            ]
        },
    )

    assert save_response.status_code == 200
    assert save_response.json() == {
        "stocks": [
            {"code": "601318", "name": "中国平安", "exchange": "SSE"},
            {"code": "000001", "name": "平安银行", "exchange": "SZSE"},
        ]
    }
    assert (tmp_path / "config/watchlist.json").exists()
    assert client.get("/api/watchlist").json() == save_response.json()


def test_stocks_route_searches_a_share_us_stock_and_crypto_defaults(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    write_stock_catalog([StockInfo("601318", "中国平安", "SSE")], tmp_path / "data/a_share_stocks.csv")

    assert client.get("/api/stocks", params={"query": "平安"}).json()[0] == {"code": "601318", "name": "中国平安", "exchange": "SSE"}
    assert client.get("/api/stocks", params={"query": "aap"}).json()[0] == {"code": "AAPL", "name": "Apple", "exchange": "NASDAQ"}
    assert client.get("/api/stocks", params={"query": "bitcoin"}).json()[0] == {"code": "BTCUSDT", "name": "Bitcoin", "exchange": "CRYPTO"}


def test_managed_data_routes_report_and_update_watchlist_files(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    client.put(
        "/api/watchlist",
        json={"stocks": [{"code": "601318", "name": "中国平安", "exchange": "SSE"}]},
    )

    status_response = client.get("/api/data/managed")

    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["files"][0]["code"] == "601318"
    assert status_payload["files"][0]["exists"] is False
    assert status_payload["files"][0]["latest_path"].endswith("601318_SSE_daily_qfq_latest.csv")

    from ai_trade_system import data_manager

    def fake_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str):
        assert (symbol, start_date, end_date, exchange, adjust) == ("601318", "20260617", "20260618", "SSE", "qfq")
        return [_bar(symbol, exchange, date(2026, 6, 17), 51.0), _bar(symbol, exchange, date(2026, 6, 18), 52.0)]

    monkeypatch.setattr(data_manager, "fetch_akshare_daily_bars", fake_fetch)

    update_response = client.post(
        "/api/data/update-watchlist",
        json={"start_date": "20260617", "end_date": "20260618", "adjust": "qfq", "if_stale": True},
    )

    assert update_response.status_code == 200
    update_payload = update_response.json()
    assert update_payload["updated"] == 1
    assert update_payload["skipped"] == 0
    assert update_payload["failed"] == 0
    assert update_payload["files"][0]["status"] == "updated"
    assert update_payload["files"][0]["latest_rows"] == 2
    assert (tmp_path / "data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv").exists()
    assert (tmp_path / "data/market/a_share/SSE/601318/manifest.json").exists()


def test_strategy_template_create_and_source_save_routes(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    create_response = client.post(
        "/api/strategies/template",
        json={"filename": "my_signal.py", "class_name": "MySignalStrategy"},
    )

    assert create_response.status_code == 200
    create_payload = create_response.json()
    assert create_payload["path"] == "strategies/my_signal.py"
    assert any(strategy["id"] == "user:my_signal:MySignalStrategy" for strategy in create_payload["strategies"])

    source = """from ai_trade_system.market import Signal\nfrom ai_trade_system.strategy import Strategy\n\n\nclass SavedStrategy(Strategy):\n    def on_bar(self, bar):\n        return [Signal(\"buy\", bar.symbol, bar.close_price, 100, \"saved\")]\n"""
    save_response = client.put(
        "/api/strategies/source",
        json={"filename": "saved_strategy.py", "source": source},
    )

    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert save_payload["path"] == "strategies/saved_strategy.py"
    assert any(strategy["id"] == "user:saved_strategy:SavedStrategy" for strategy in save_payload["strategies"])
    read_response = client.get("/api/strategies/source", params={"path": "strategies/saved_strategy.py"})
    assert read_response.status_code == 200
    assert "class SavedStrategy" in read_response.json()["source"]


def test_demo_data_backtest_ai_and_risk_flow(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()

    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 80})
    assert demo_response.status_code == 200
    assert demo_response.json()["summary"]["rows"] == 80

    backtest_response = client.post(
        "/api/backtest",
        json={
            "settings": settings,
            "strategy": _strategy_payload(),
            "portfolio": None,
            "mode": "single",
        },
    )
    assert backtest_response.status_code == 200
    backtest_payload = backtest_response.json()
    assert backtest_payload["metrics"]["final_equity"] > 0
    assert "benchmark_return_pct" in backtest_payload["metrics"]
    assert "excess_return_pct" in backtest_payload["metrics"]
    assert "annual_volatility_pct" in backtest_payload["metrics"]
    assert "sharpe_ratio" in backtest_payload["metrics"]
    assert backtest_payload["bars"][0]["trading_day"] == "2024-01-02"
    assert "risk_status" in backtest_payload
    assert backtest_payload["trade_attributions"]
    assert {"signal_reason", "signal_family", "signal_label"} <= set(backtest_payload["trade_attributions"][0])
    assert backtest_payload["signal_attribution"]
    assert {"family", "label", "trade_count", "entry_realized_pnl", "exit_realized_pnl"} <= set(
        backtest_payload["signal_attribution"][0]
    )

    ai_response = client.post(
        "/api/ai/research",
        json={
            "settings": settings,
            "information_notes": ["政策支持流动性改善", "关注短线追高风险"],
            "prompt_mode": "balanced",
            "horizon": "5个交易日",
        },
    )
    assert ai_response.status_code == 200
    ai_payload = ai_response.json()
    assert ai_payload["insight"]["provider"] == "MockLLMProvider"
    assert ai_payload["prompt"].startswith("你是 A 股量化研究员")

    risk_response = client.post(
        "/api/risk/evaluate",
        json={
            "metrics": {"max_drawdown_pct": -25.0},
            "config": {
                "max_drawdown_pct": 20.0,
                "max_order_cash": 50000.0,
                "min_cash_balance": 0.0,
                "max_position_shares": 50000,
                "cooldown_days": 0,
                "enabled": True,
            },
        },
    )
    assert risk_response.status_code == 200
    assert risk_response.json()["ok"] is False


def test_strategies_route_exposes_enum_parameter_options(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/strategies")

    assert response.status_code == 200
    payload = response.json()
    chan = next(strategy for strategy in payload if strategy["class_name"] == "ChanStructureStrategy")
    params = {param["name"]: param for param in chan["parameters"]}

    assert params["signal_mode"]["options"] == ["all", "confirmation", "structure"]
    assert params["signal_mode"]["multiple"] is False
    assert params["allowed_point_types"]["options"] == [
        "all",
        "first-buy",
        "first-sell",
        "second-buy",
        "second-sell",
        "third-buy",
        "third-sell",
    ]
    assert params["allowed_point_types"]["multiple"] is True
    assert params["allowed_levels"]["options"] == ["all", "segment", "stroke", "fractal"]
    assert params["allowed_levels"]["multiple"] is True

    fusion = next(strategy for strategy in payload if strategy["class_name"] == "ChanVolumeFusionStrategy")
    fusion_params = {param["name"]: param for param in fusion["parameters"]}

    assert fusion["display_name"] == "缠论量价融合"
    assert fusion_params["weak_volume_exit_mode"]["options"] == ["reduce", "exit", "ignore"]
    assert fusion_params["low_confidence_requires_volume"]["display_name"] == "低确定性需量价确认"
    assert "放量" in fusion_params["volume_boost_units"]["description"]


def test_paper_run_and_events_routes_round_trip_log(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 80})
    assert demo_response.status_code == 200

    run_response = client.post(
        "/api/paper/run",
        json={
            "settings": settings,
            "strategy": _strategy_payload(),
            "portfolio": None,
            "mode": "single",
        },
    )

    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["events"]
    assert run_payload["summary"]["event"] == "service_stopped"
    assert (tmp_path / settings["log_path"]).exists()

    events_response = client.get("/api/paper/events", params={"path": settings["log_path"]})

    assert events_response.status_code == 200
    events_payload = events_response.json()
    assert len(events_payload["events"]) == len(run_payload["events"])
    assert events_payload["summary"]["event"] == "service_stopped"


def test_risk_evaluate_route_accepts_valid_payload(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/risk/evaluate",
        json={
            "metrics": {"max_drawdown_pct": -25.0},
            "config": {
                "max_drawdown_pct": 20.0,
                "max_order_cash": 50000.0,
                "min_cash_balance": 0.0,
                "max_position_shares": 50000,
                "cooldown_days": 0,
                "enabled": True,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is False
    assert payload["enabled"] is True
    assert payload["warnings"]


def test_risk_evaluate_route_rejects_invalid_payload(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/risk/evaluate", json={"metrics": {"max_drawdown_pct": -5.0}})

    assert response.status_code == 422


def test_portfolio_preview_returns_breakdown_contract(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 80})
    assert demo_response.status_code == 200
    strategies = client.get("/api/bootstrap").json()["strategies"]
    structure = next(strategy for strategy in strategies if strategy["name"] == "ChanStructureStrategy")
    chan_rsi = next(strategy for strategy in strategies if strategy["name"] == "ChanRsiResearchStrategy")

    response = client.post(
        "/api/portfolio/preview",
        json={
            "settings": settings,
            "portfolio": {
                "mode": "weighted_vote",
                "ai_adjust": False,
                "ai_direction": None,
                "allocations": [
                    {
                        "strategy": {"id": structure["id"], "params": {"symbol": "000001", "trade_size": 100}},
                        "weight": 2,
                        "enabled": True,
                    },
                    {
                        "strategy": {"id": chan_rsi["id"], "params": {"symbol": "000001", "trade_size": 100}},
                        "weight": 1,
                        "enabled": True,
                    },
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["breakdown"]["mode"] == "weighted_vote"
    assert "contributions" in payload["breakdown"]
    assert payload["allocations"][0]["index"] == 0
    assert payload["allocations"][0]["name"] == "缠论结构策略"
    assert payload["allocations"][1]["index"] == 1
    assert payload["allocations"][1]["name"] == "缠论RSI研究"


def test_portfolio_preview_returns_ai_adjustment_weight_preview(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 80})
    assert demo_response.status_code == 200
    strategies = client.get("/api/bootstrap").json()["strategies"]
    structure = next(strategy for strategy in strategies if strategy["name"] == "ChanStructureStrategy")
    chan_rsi = next(strategy for strategy in strategies if strategy["name"] == "ChanRsiResearchStrategy")

    response = client.post(
        "/api/portfolio/preview",
        json={
            "settings": settings,
            "portfolio": {
                "mode": "weighted_vote",
                "ai_adjust": True,
                "ai_direction": "bullish",
                "allocations": [
                    {
                        "strategy": {"id": structure["id"], "params": {"symbol": "000001", "trade_size": 100}},
                        "weight": 2,
                        "enabled": True,
                    },
                    {
                        "strategy": {"id": chan_rsi["id"], "params": {"symbol": "000001", "trade_size": 100}},
                        "weight": 1,
                        "enabled": True,
                    },
                ],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ai_adjustment"] == {
        "enabled": True,
        "direction": "bullish",
        "applied": True,
        "delta": 0.05,
    }
    assert payload["allocations"][0]["base_weight"] == 2
    assert payload["allocations"][0]["name"] == "缠论结构策略"
    assert payload["allocations"][0]["adjusted_weight"] == 2.05
    assert payload["allocations"][0]["ai_delta"] == 0.05
    assert payload["allocations"][0]["ai_adjusted"] is True
    assert payload["allocations"][0]["weight"] == 2.05
    assert payload["allocations"][1]["base_weight"] == 1
    assert payload["allocations"][1]["name"] == "缠论RSI研究"
    assert payload["allocations"][1]["adjusted_weight"] == 1.05


def test_demo_data_contains_mixed_rising_and_falling_candles(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.post("/api/data/demo", json={"settings": _settings_payload(), "count": 80})

    assert response.status_code == 200
    bars = response.json()["bars"]
    rising = [bar for bar in bars if bar["close_price"] > bar["open_price"]]
    falling = [bar for bar in bars if bar["close_price"] < bar["open_price"]]
    assert len(rising) >= 20
    assert len(falling) >= 20


def test_download_data_route_supports_minute_timeframe(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str, timeframe: str):
        assert (symbol, start_date, end_date, exchange, adjust, timeframe) == ("000001", "20240102", "20240102", "SZSE", "qfq", "5m")
        return [
            Bar(
                symbol=symbol,
                exchange=exchange,
                trading_day=date(2024, 1, 2),
                open_price=10,
                high_price=10.2,
                low_price=9.9,
                close_price=10.1,
                volume=1000,
                turnover=10100,
                timestamp=datetime(2024, 1, 2, 9, 31),
                timeframe="5m",
            )
        ]

    monkeypatch.setattr(service, "fetch_akshare_bars", fake_fetch)
    settings = {
        **_settings_payload(),
        "start_date": "20240102",
        "end_date": "20240102",
        "timeframe": "5m",
        "csv_path": "data/market/a_share/SZSE/000001/000001_SZSE_5m_qfq_latest.csv",
    }

    response = client.post("/api/data/download", json={"settings": settings})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["timeframe"] == "5m"
    assert payload["summary"]["start"] == "2024-01-02 09:31:00"
    assert payload["bars"][0]["timestamp"] == "2024-01-02T09:31:00"
    assert payload["bars"][0]["timeframe"] == "5m"
    assert payload["managed_file"]["timeframe"] == "5m"
    assert Path(settings["csv_path"]).exists()


def test_research_signals_preview_route_returns_blocker_for_short_demo_data(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 20})
    assert demo_response.status_code == 200

    response = client.post("/api/research/signals/preview", json={"settings": settings, "min_bars": 60, "lookback": 120})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "000001"
    assert payload["blockers"][0]["code"] == "INSUFFICIENT_BARS"
    assert payload["score"]["direction"] == "neutral"


def test_research_signals_batch_route_scans_local_csv_catalog(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    data_dir = tmp_path / "data"
    ping_an = StockInfo("000001", "平安银行", "SZSE")
    insurer = StockInfo("601318", "中国平安", "SSE")
    smic = StockInfo("688981", "中芯国际", "SSE")
    write_stock_catalog(
        [ping_an, insurer, smic],
        data_dir / "a_share_stocks.csv",
    )
    ping_an_path = _write_managed_bars(ping_an, _momentum_closes(10.0, 12.0))
    insurer_path = _write_managed_bars(insurer, _momentum_closes(20.0, 18.0))

    response = client.post(
        "/api/research/signals/batch",
        json={"settings": _settings_payload(), "query": "", "limit": 3, "min_bars": 40, "lookback": 60},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score_mode"] == "chan_multilevel_daily_anchor"
    assert payload["scanned"] == 3
    assert payload["available"] == 2
    assert payload["missing"] == 1
    assert {row["code"] for row in payload["rows"][:2]} == {"000001", "601318"}
    assert payload["rows"][0]["status"] == "scanned"
    assert payload["rows"][0]["csv_path"] in {ping_an_path.as_posix(), insurer_path.as_posix()}
    assert payload["rows"][0]["preview"]["symbol"] in {"000001", "601318"}
    assert payload["rows"][0]["score"]["direction"] in {"bullish", "bearish", "neutral"}
    assert payload["rows"][2]["status"] == "missing_data"
    assert payload["rows"][2]["csv_path"] == data_file_for_stock(smic, adjust="qfq").latest_path.as_posix()
    assert payload["rows"][2]["blockers"][0]["code"] == "MISSING_CSV"


def test_research_signals_batch_route_can_scan_only_local_csv_universe(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    data_dir = tmp_path / "data"
    ping_an = StockInfo("000001", "平安银行", "SZSE")
    insurer = StockInfo("601318", "中国平安", "SSE")
    smic = StockInfo("688981", "中芯国际", "SSE")
    write_stock_catalog(
        [ping_an, insurer, smic],
        data_dir / "a_share_stocks.csv",
    )
    ping_an_path = _write_managed_bars(ping_an, _momentum_closes(10.0, 12.0))
    insurer_path = _write_managed_bars(insurer, _momentum_closes(20.0, 18.0))

    response = client.post(
        "/api/research/signals/batch",
        json={"settings": _settings_payload(), "query": "", "limit": 3, "min_bars": 40, "lookback": 60, "universe": "local_csv"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"] == "local_csv"
    assert payload["scanned"] == 2
    assert payload["available"] == 2
    assert payload["missing"] == 0
    assert {row["code"] for row in payload["rows"]} == {"000001", "601318"}
    assert {row["csv_path"] for row in payload["rows"]} == {ping_an_path.as_posix(), insurer_path.as_posix()}


def test_research_signals_batch_star_universe_filters_star_candidates(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        service,
        "load_stock_catalog",
        lambda: [
            StockInfo("688001", "华兴源创", "SSE"),
            StockInfo("688981", "中芯国际", "SSE"),
            StockInfo("600000", "浦发银行", "SSE"),
            StockInfo("300750", "宁德时代", "SZSE"),
        ],
    )

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 100,
            "min_bars": 60,
            "lookback": 120,
            "universe": "star",
            "score_mode": "volume_momentum",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["universe"] == "star"
    assert [row["code"] for row in payload["rows"]] == ["688001", "688981"]
    assert payload["scanned"] == 2
    assert payload["available"] == 0
    assert payload["missing"] == 2


def test_research_signals_batch_star_universe_honors_query(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    monkeypatch.setattr(
        service,
        "load_stock_catalog",
        lambda: [
            StockInfo("688001", "华兴源创", "SSE"),
            StockInfo("688981", "中芯国际", "SSE"),
        ],
    )

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "68898",
            "limit": 100,
            "min_bars": 60,
            "lookback": 120,
            "universe": "star",
            "score_mode": "volume_momentum",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [row["code"] for row in payload["rows"]] == ["688981"]
    assert payload["scanned"] == 1


def test_research_signals_batch_auto_updates_star_data_before_scan(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    stock = StockInfo("688001", "华兴源创", "SSE")
    monkeypatch.setattr(service, "load_stock_catalog", lambda: [stock])

    def fake_update_stock_data(stock_arg, *, start_date, end_date, adjust, if_stale, **_kwargs):
        bars_path = _write_managed_bars(stock, _momentum_closes(10.0, 16.0), [1000.0] * 79 + [2600.0])
        return DataUpdateResult(
            code=stock_arg.code,
            name=stock_arg.name,
            exchange=stock_arg.exchange,
            adjust=adjust,
            status="updated",
            requested_start=start_date,
            requested_end=end_date,
            fetched_start=start_date,
            fetched_end=end_date,
            fetched_rows=80,
            latest_rows=80,
            latest_start="2026-01-01",
            latest_end="2026-03-21",
            latest_path=bars_path.as_posix(),
            increment_path=None,
            message="updated 80 bars",
        )

    monkeypatch.setattr(service, "update_stock_data", fake_update_stock_data, raising=False)

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 100,
            "min_bars": 20,
            "lookback": 60,
            "universe": "star",
            "score_mode": "volume_momentum",
            "auto_update_data": True,
            "if_stale": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_update"]["enabled"] is True
    assert payload["data_update"]["total"] == 1
    assert payload["data_update"]["updated"] == 1
    assert payload["data_update"]["skipped"] == 0
    assert payload["data_update"]["failed"] == 0
    assert payload["rows"][0]["status"] == "scanned"
    assert payload["rows"][0]["data_status"]["status"] == "updated"
    assert payload["rows"][0]["data_status"]["rows"] == 80
    assert payload["rows"][0]["momentum"]["entry_ready"] is True


def test_research_signals_batch_auto_update_skips_when_increment_fetch_fails_but_local_csv_exists(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    stock = StockInfo("688001", "华兴源创", "SSE")
    monkeypatch.setattr(service, "load_stock_catalog", lambda: [stock])
    _write_managed_bars(stock, _momentum_closes(10.0, 16.0), [1000.0] * 79 + [2600.0])

    def fail_fetch(symbol: str, start_date: str, end_date: str, exchange: str, adjust: str):
        assert (symbol, start_date, end_date, exchange, adjust) == ("688001", "20260322", "20260322", "SSE", "qfq")
        raise RuntimeError("provider has no data for requested end date")

    monkeypatch.setattr(data_manager, "fetch_akshare_daily_bars", fail_fetch)
    settings = {**_settings_payload(), "start_date": "20260101", "end_date": "20260322"}

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": settings,
            "query": "",
            "limit": 100,
            "min_bars": 20,
            "lookback": 60,
            "universe": "star",
            "score_mode": "volume_momentum",
            "auto_update_data": True,
            "if_stale": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_update"]["enabled"] is True
    assert payload["data_update"]["total"] == 1
    assert payload["data_update"]["updated"] == 0
    assert payload["data_update"]["skipped"] == 1
    assert payload["data_update"]["failed"] == 0
    assert payload["available"] == 1
    assert payload["missing"] == 0
    assert payload["rows"][0]["status"] == "scanned"
    assert payload["rows"][0]["data_status"]["status"] == "skipped"
    assert payload["rows"][0]["data_status"]["rows"] == 80
    assert payload["rows"][0]["data_status"]["end"] == "2026-03-21"
    assert "using existing local data" in payload["rows"][0]["data_status"]["message"]
    assert not any(blocker["code"] == "DATA_UPDATE_FAILED" for blocker in payload["rows"][0]["blockers"])


def test_research_signals_batch_auto_update_failure_returns_blocker(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    stock = StockInfo("688001", "华兴源创", "SSE")
    monkeypatch.setattr(service, "load_stock_catalog", lambda: [stock])

    def fail_update_stock_data(*_args, **_kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(service, "update_stock_data", fail_update_stock_data, raising=False)

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 100,
            "min_bars": 20,
            "lookback": 60,
            "universe": "star",
            "score_mode": "volume_momentum",
            "auto_update_data": True,
            "if_stale": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_update"]["enabled"] is True
    assert payload["data_update"]["failed"] == 1
    assert payload["rows"][0]["status"] == "missing_data"
    assert payload["rows"][0]["data_status"]["status"] == "failed"
    assert payload["rows"][0]["data_status"]["message"] == "network down"
    assert any(blocker["code"] == "DATA_UPDATE_FAILED" for blocker in payload["rows"][0]["blockers"])


def test_research_signals_batch_route_ranks_volume_momentum_from_managed_csv(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    data_dir = tmp_path / "data"
    strong = StockInfo("688981", "中芯国际", "SSE")
    weak = StockInfo("000858", "五粮液", "SZSE")
    write_stock_catalog([weak, strong], data_dir / "a_share_stocks.csv")
    strong_path = _write_managed_bars(strong, _momentum_closes(10.0, 16.0), [1000.0] * 79 + [2600.0])
    weak_path = _write_managed_bars(weak, _momentum_closes(20.0, 20.8), [1000.0] * 79 + [1050.0])

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 2,
            "min_bars": 60,
            "lookback": 80,
            "universe": "catalog",
            "score_mode": "volume_momentum",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score_mode"] == "volume_momentum"
    assert payload["available"] == 2
    assert [row["code"] for row in payload["rows"]] == ["688981", "000858"]
    assert payload["rows"][0]["csv_path"] == strong_path.as_posix()
    assert payload["rows"][1]["csv_path"] == weak_path.as_posix()
    assert payload["rows"][0]["score"]["direction"] == "bullish"
    assert payload["rows"][0]["score"]["total_score"] > payload["rows"][1]["score"]["total_score"]
    assert payload["rows"][0]["momentum"]["entry_ready"] is True
    assert payload["rows"][0]["momentum"]["latest_reason"] == "volume_confirmed_momentum_entry"
    assert payload["rows"][0]["latest_signal"]["title"] == "量价动量触发"
    assert payload["rows"][1]["momentum"]["entry_ready"] is False


def test_research_signals_batch_route_ranks_chan_structure_from_managed_csv(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    data_dir = tmp_path / "data"
    strong = StockInfo("688981", "中芯国际", "SSE")
    weak = StockInfo("000858", "五粮液", "SZSE")
    write_stock_catalog([weak, strong], data_dir / "a_share_stocks.csv")
    strong_path = _write_managed_bars(strong, _chan_structure_closes())
    weak_path = _write_managed_bars(weak, _momentum_closes(20.0, 20.8, 82))

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 2,
            "min_bars": 60,
            "lookback": 82,
            "universe": "catalog",
            "score_mode": "chan_structure",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score_mode"] == "chan_structure"
    assert payload["available"] == 2
    assert payload["rows"][0]["code"] == "688981"
    assert payload["rows"][0]["csv_path"] == strong_path.as_posix()
    assert payload["rows"][1]["csv_path"] == weak_path.as_posix()
    assert payload["rows"][0]["score"]["chan_structure"]["fractal_count"] > 0
    assert payload["rows"][0]["score"]["chan_structure"]["stroke_count"] > 0
    assert payload["rows"][0]["score"]["chan_structure"]["pivot_count"] > 0
    assert payload["rows"][0]["score"]["chan_structure"]["segment_count"] > 0
    assert payload["rows"][0]["score"]["chan_structure"]["recursive_pivot_count"] > 0
    assert payload["rows"][0]["score"]["chan_structure"]["divergence_count"] >= 0
    assert payload["rows"][0]["latest_signal"]["kind"].startswith("CHAN_STRUCT_")
    assert payload["rows"][0]["score"]["total_score"] > abs(payload["rows"][1]["score"]["total_score"])


def test_research_signals_batch_route_accepts_chan_multilevel_daily_anchor_mode(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    data_dir = tmp_path / "data"
    strong = StockInfo("688981", "中芯国际", "SSE")
    weak = StockInfo("000858", "五粮液", "SZSE")
    write_stock_catalog([weak, strong], data_dir / "a_share_stocks.csv")
    _write_managed_bars(strong, _chan_structure_closes())
    _write_managed_bars(weak, _momentum_closes(20.0, 20.8, 82))

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 2,
            "min_bars": 60,
            "lookback": 82,
            "universe": "catalog",
            "score_mode": "chan_multilevel_daily_anchor",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score_mode"] == "chan_multilevel_daily_anchor"
    assert payload["available"] == 2
    assert payload["rows"][0]["score"]["summary"]
    assert payload["rows"][0]["preview"]["strategy"]["entry_mode"] == "daily_anchor"


def test_research_signals_preview_route_returns_signals_for_demo_data(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 120})
    assert demo_response.status_code == 200

    response = client.post("/api/research/signals/preview", json={"settings": settings, "min_bars": 40, "lookback": 120})

    assert response.status_code == 200
    payload = response.json()
    assert payload["bars"] == 120
    assert "total_score" in payload["score"]
    assert isinstance(payload["signals"], list)


def test_strategy_source_and_data_paths_reject_traversal(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    source_response = client.get("/api/strategies/source", params={"path": "../outside.py"})
    assert source_response.status_code == 400

    data_response = client.post(
        "/api/data/load",
        json={"settings": {**_settings_payload(), "csv_path": "../outside.csv"}},
    )
    assert data_response.status_code == 400


def test_automation_status_route_returns_config_and_runs(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/automation/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["config"]["enabled"] is True
    assert payload["weekly_top10_count"] == 0
    assert payload["latest_daily_judgment_count"] == 0
    assert payload["recent_runs"] == []
    assert payload["diagnostics"]


def test_automation_config_route_updates_enabled_and_weights(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.put("/api/automation/config", json={"enabled": False, "top_n": 8, "volume_weight": 0.5})

    assert response.status_code == 200
    payload = response.json()
    assert payload["enabled"] is False
    assert payload["top_n"] == 8
    assert payload["volume_weight"] == 0.5


def test_automation_top10_and_judgments_routes_return_empty_defaults(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    top10 = client.get("/api/automation/radar/top10")
    judgments = client.get("/api/automation/judgments")

    assert top10.status_code == 200
    assert top10.json()["top"] == []
    assert judgments.status_code == 200
    assert judgments.json()["judgments"] == []
