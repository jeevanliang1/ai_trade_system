from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from ai_trade_system.api.app import create_app


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


def test_bootstrap_returns_defaults_and_strategy_metadata(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/bootstrap")

    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["csv_path"] == "data/000001_daily.csv"
    assert payload["catalog_available"] is False
    assert payload["strategies"][0]["id"].startswith("builtin:")
    assert payload["strategies"][0]["parameters"]


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
    assert payload["allocations"][0]["name"] == "DualMovingAverageStrategy"
    assert payload["allocations"][1]["index"] == 1


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
    assert payload["allocations"][0]["adjusted_weight"] == 2.05
    assert payload["allocations"][0]["ai_delta"] == 0.05
    assert payload["allocations"][0]["ai_adjusted"] is True
    assert payload["allocations"][0]["weight"] == 2.05
    assert payload["allocations"][1]["base_weight"] == 1
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


def test_strategy_source_and_data_paths_reject_traversal(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    source_response = client.get("/api/strategies/source", params={"path": "../outside.py"})
    assert source_response.status_code == 400

    data_response = client.post(
        "/api/data/load",
        json={"settings": {**_settings_payload(), "csv_path": "../outside.csv"}},
    )
    assert data_response.status_code == 400
