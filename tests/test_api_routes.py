from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from ai_trade_system.api import service
from ai_trade_system.api.app import create_app
from ai_trade_system.data import write_bars_csv
from ai_trade_system.data_manager import data_file_for_stock
from ai_trade_system.market import Bar
from ai_trade_system.stock_catalog import StockInfo, write_stock_catalog


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.chdir(tmp_path)
    return TestClient(create_app())


def _strategy_payload() -> dict:
    return {
        "id": "builtin:dual_moving_average:DualMovingAverageStrategy",
        "params": {"symbol": "000001", "fast": 5, "slow": 20, "size": 100},
    }


def _settings_payload() -> dict:
    return {
        "symbol": "000001",
        "exchange": "SZSE",
        "start_date": "20220101",
        "end_date": "20250516",
        "adjust": "qfq",
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
    assert payload["settings"]["csv_path"] == "data/000001_daily.csv"
    assert payload["watchlist"] == []
    assert payload["catalog_available"] is False
    assert payload["strategies"][0]["id"].startswith("builtin:")
    assert payload["strategies"][0]["display_name"]
    assert payload["strategies"][0]["description"]
    assert payload["strategies"][0]["parameters"]
    fast_window = next(parameter for parameter in payload["strategies"][0]["parameters"] if parameter["name"] == "fast_window")
    assert fast_window["display_name"] == "快线周期"
    assert "短期均线" in fast_window["description"]
    assert "更平滑" in fast_window["increase_effect"]
    assert "更敏感" in fast_window["decrease_effect"]


def test_bootstrap_returns_portfolio_presets_for_strategy_combinations(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    presets = payload["portfolio_presets"]
    conservative = next(preset for preset in presets if preset["id"] == "conservative_trend_reversion")

    assert conservative["name"] == "稳健趋势均值组合"
    assert conservative["mode"] == "weighted_vote"
    assert "趋势" in conservative["description"]
    assert "均值回归" in conservative["description"]
    assert len(conservative["allocations"]) >= 4
    strategy_ids = [allocation["strategy"]["id"] for allocation in conservative["allocations"]]
    assert "builtin:dual_moving_average:DualMovingAverageStrategy" in strategy_ids
    assert "builtin:popular:RsiMeanReversionStrategy" in strategy_ids
    assert "builtin:popular:AtrVolatilityBreakoutStrategy" in strategy_ids
    assert conservative["allocations"][0]["strategy"]["params"]["symbol"] == "000001"
    assert conservative["allocations"][0]["weight"] > 0
    assert conservative["allocations"][0]["enabled"] is True
    assert {preset["id"] for preset in presets} >= {
        "conservative_trend_reversion",
        "momentum_breakout_stack",
        "chan_research_stack",
    }


def test_portfolio_preview_accepts_bootstrap_preset_allocations(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 120})
    assert demo_response.status_code == 200
    bootstrap = client.get("/api/bootstrap").json()
    preset = next(item for item in bootstrap["portfolio_presets"] if item["id"] == "conservative_trend_reversion")

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
    assert payload["allocations"][0]["name"] == "双均线趋势"
    assert len(payload["allocations"]) == len(preset["allocations"])
    assert payload["breakdown"]["mode"] == "weighted_vote"


def test_default_settings_use_two_year_range_from_current_date():
    settings = service.default_settings(today=date(2026, 6, 18))

    assert settings.start_date == "20240618"
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
    dual = next(strategy for strategy in strategies if strategy["name"] == "DualMovingAverageStrategy")
    rsi = next(strategy for strategy in strategies if strategy["name"] == "RsiMeanReversionStrategy")

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
                        "strategy": {"id": dual["id"], "params": {"symbol": "000001", "fast": 5, "slow": 20, "size": 100}},
                        "weight": 2,
                        "enabled": True,
                    },
                    {
                        "strategy": {"id": rsi["id"], "params": {"symbol": "000001", "rsi_period": 14, "trade_size": 100}},
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
    assert payload["allocations"][0]["name"] == "双均线趋势"
    assert payload["allocations"][1]["index"] == 1
    assert payload["allocations"][1]["name"] == "RSI均值回归"


def test_portfolio_preview_returns_ai_adjustment_weight_preview(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    settings = _settings_payload()
    demo_response = client.post("/api/data/demo", json={"settings": settings, "count": 80})
    assert demo_response.status_code == 200
    strategies = client.get("/api/bootstrap").json()["strategies"]
    dual = next(strategy for strategy in strategies if strategy["name"] == "DualMovingAverageStrategy")
    rsi = next(strategy for strategy in strategies if strategy["name"] == "RsiMeanReversionStrategy")

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
                        "strategy": {"id": dual["id"], "params": {"symbol": "000001", "fast": 5, "slow": 20, "size": 100}},
                        "weight": 2,
                        "enabled": True,
                    },
                    {
                        "strategy": {"id": rsi["id"], "params": {"symbol": "000001", "rsi_period": 14, "trade_size": 100}},
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
    assert payload["allocations"][0]["name"] == "双均线趋势"
    assert payload["allocations"][0]["adjusted_weight"] == 2.05
    assert payload["allocations"][0]["ai_delta"] == 0.05
    assert payload["allocations"][0]["ai_adjusted"] is True
    assert payload["allocations"][0]["weight"] == 2.05
    assert payload["allocations"][1]["base_weight"] == 1
    assert payload["allocations"][1]["name"] == "RSI均值回归"
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
    assert payload["score_mode"] == "research"
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
