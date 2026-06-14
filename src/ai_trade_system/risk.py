from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class RiskGuardrailConfig:
    max_drawdown_pct: float = 20.0
    max_order_cash: float = 50_000
    min_cash_balance: float = 0.0
    max_position_shares: int = 50_000
    cooldown_days: int = 0


@dataclass(frozen=True)
class RiskGuardrailStatus:
    ok: bool
    warnings: list[str] = field(default_factory=list)
    enabled: bool = True


def evaluate_risk_guardrails(
    metrics: Mapping[str, float | int | None],
    config: RiskGuardrailConfig,
    enabled: bool = True,
) -> RiskGuardrailStatus:
    if not enabled:
        return RiskGuardrailStatus(ok=True, warnings=[], enabled=False)

    warnings: list[str] = []
    drawdown = metrics.get("max_drawdown_pct")
    if drawdown is not None and abs(float(drawdown)) > config.max_drawdown_pct:
        warnings.append(f"最大回撤 {abs(float(drawdown)):.2f}% 超过阈值 {config.max_drawdown_pct:.2f}%")

    if config.max_order_cash <= 0:
        warnings.append("单笔最大金额必须大于 0")
    if config.min_cash_balance < 0:
        warnings.append("最小现金余额不能为负数")
    if config.max_position_shares <= 0:
        warnings.append("最大持仓股数必须大于 0")

    return RiskGuardrailStatus(ok=not warnings, warnings=warnings, enabled=True)
