from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_trade_system.strategy_registry import StrategySpec, inspect_strategy_parameters


@dataclass(frozen=True)
class PortfolioPresetAllocationSpec:
    strategy_name: str
    weight: float
    role: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PortfolioPresetSpec:
    id: str
    name: str
    description: str
    mode: str
    allocations: tuple[PortfolioPresetAllocationSpec, ...]


PORTFOLIO_PRESETS: tuple[PortfolioPresetSpec, ...] = (
    PortfolioPresetSpec(
        id="chan_research_stack",
        name="缠论研究组合",
        description="以缠论结构策略为主，叠加缠论RSI研究，用于验证结构买卖点与研究信号是否同向。",
        mode="weighted_vote",
        allocations=(
            PortfolioPresetAllocationSpec("ChanStructureStrategy", 1.0, "缠论结构"),
            PortfolioPresetAllocationSpec("ChanRsiResearchStrategy", 0.75, "缠论RSI"),
        ),
    ),
    PortfolioPresetSpec(
        id="chan_offensive_fusion_stack",
        name="缠论进攻融合组合",
        description="以缠论量价融合为主的进攻组合，缠论结构和缠论多级别反转只做冲突过滤和顺向小幅加仓。",
        mode="primary_assist",
        allocations=(
            PortfolioPresetAllocationSpec(
                "ChanVolumeFusionStrategy",
                1.0,
                "缠论量价主策略",
                params={
                    "high_confidence_units": 2,
                    "max_units": 3,
                    "volume_boost_units": 1,
                    "weak_volume_requires_trend_break": True,
                    "continuation_trend_window": 60,
                    "severe_weak_momentum_pct": -0.04,
                },
            ),
            PortfolioPresetAllocationSpec("ChanStructureStrategy", 0.25, "缠论结构确认"),
            PortfolioPresetAllocationSpec("ChanMultiLevelReversalStrategy", 0.2, "多级别执行确认"),
        ),
    ),
    PortfolioPresetSpec(
        id="chan_multilevel_execution_stack",
        name="缠论多级别执行组合",
        description="以日线缠论结构为核心，用多级别反转策略提供 60m/30m 执行确认，并保留缠论量价融合做顺向增强。",
        mode="weighted_vote",
        allocations=(
            PortfolioPresetAllocationSpec("ChanMultiLevelReversalStrategy", 1.0, "日线锚定与低级别确认"),
            PortfolioPresetAllocationSpec("ChanStructureStrategy", 0.8, "日线结构底座"),
            PortfolioPresetAllocationSpec("ChanVolumeFusionStrategy", 0.6, "量价融合增强"),
        ),
    ),
)


def portfolio_preset_views(strategies: list[StrategySpec], symbol: str) -> list[dict[str, Any]]:
    strategies_by_name = {strategy.name: strategy for strategy in strategies}
    views: list[dict[str, Any]] = []
    for preset in PORTFOLIO_PRESETS:
        allocations = []
        for allocation in preset.allocations:
            strategy = strategies_by_name.get(allocation.strategy_name)
            if strategy is None:
                continue
            allocations.append(
                {
                    "strategy": {
                        "id": strategy.id,
                        "params": _params_for_strategy(strategy, symbol, allocation.params),
                    },
                    "weight": allocation.weight,
                    "enabled": allocation.enabled,
                    "role": allocation.role,
                    "display_name": strategy.display_name or strategy.name,
                }
            )
        if allocations:
            views.append(
                {
                    "id": preset.id,
                    "name": preset.name,
                    "description": preset.description,
                    "mode": preset.mode,
                    "allocations": allocations,
                }
            )
    return views


def _params_for_strategy(strategy: StrategySpec, symbol: str, overrides: dict[str, Any]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for parameter in inspect_strategy_parameters(strategy):
        params[parameter.name] = symbol if parameter.name == "symbol" else parameter.default
    params.update(overrides)
    return params
