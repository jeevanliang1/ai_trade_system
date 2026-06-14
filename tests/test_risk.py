from ai_trade_system.risk import RiskGuardrailConfig, evaluate_risk_guardrails


def test_risk_guardrails_warn_when_drawdown_breaches_limit():
    status = evaluate_risk_guardrails(
        metrics={"max_drawdown_pct": -22.5},
        config=RiskGuardrailConfig(max_drawdown_pct=20.0, max_order_cash=50_000, min_cash_balance=0),
    )

    assert status.ok is False
    assert "最大回撤" in status.warnings[0]


def test_risk_guardrails_pass_when_metrics_inside_limits():
    status = evaluate_risk_guardrails(
        metrics={"max_drawdown_pct": -8.0},
        config=RiskGuardrailConfig(max_drawdown_pct=20.0, max_order_cash=50_000, min_cash_balance=0),
    )

    assert status.ok is True
    assert status.warnings == []
