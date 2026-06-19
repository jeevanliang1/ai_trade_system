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
        id="conservative_trend_reversion",
        name="稳健趋势均值组合",
        description="用双均线和ATR突破确认趋势方向，再用RSI/布林带均值回归控制震荡修复机会。",
        mode="weighted_vote",
        allocations=(
            PortfolioPresetAllocationSpec("DualMovingAverageStrategy", 1.0, "趋势底座"),
            PortfolioPresetAllocationSpec("AtrVolatilityBreakoutStrategy", 0.8, "波动突破"),
            PortfolioPresetAllocationSpec("VolumeConfirmedMomentumStrategy", 0.7, "量价确认"),
            PortfolioPresetAllocationSpec("RsiMeanReversionStrategy", 0.55, "超卖修复"),
            PortfolioPresetAllocationSpec("BollingerMeanReversionStrategy", 0.45, "通道回归"),
        ),
    ),
    PortfolioPresetSpec(
        id="momentum_breakout_stack",
        name="动量突破组合",
        description="集中使用价格动量、量价动量、MACD、Donchian和ATR突破策略，适合验证强趋势行情。",
        mode="weighted_vote",
        allocations=(
            PortfolioPresetAllocationSpec("VolumeConfirmedMomentumStrategy", 1.0, "量价动量"),
            PortfolioPresetAllocationSpec("AtrVolatilityBreakoutStrategy", 0.9, "ATR突破"),
            PortfolioPresetAllocationSpec("DonchianBreakoutStrategy", 0.75, "通道突破"),
            PortfolioPresetAllocationSpec("PriceMomentumStrategy", 0.65, "价格动量"),
            PortfolioPresetAllocationSpec("MacdTrendStrategy", 0.55, "MACD确认"),
        ),
    ),
    PortfolioPresetSpec(
        id="chan_research_stack",
        name="缠论研究组合",
        description="以缠论结构策略为主，叠加缠论RSI研究和量价动量确认，用于验证结构信号和技术动量是否同向。",
        mode="weighted_vote",
        allocations=(
            PortfolioPresetAllocationSpec("ChanStructureStrategy", 1.0, "缠论结构"),
            PortfolioPresetAllocationSpec("ChanRsiResearchStrategy", 0.75, "缠论RSI"),
            PortfolioPresetAllocationSpec("VolumeConfirmedMomentumStrategy", 0.55, "量价确认"),
            PortfolioPresetAllocationSpec("AtrVolatilityBreakoutStrategy", 0.45, "波动确认"),
        ),
    ),
    PortfolioPresetSpec(
        id="chan_offensive_fusion_stack",
        name="缠论进攻融合组合",
        description="以缠论量价融合为主的进攻组合，辅助策略只做冲突过滤和顺向小幅加仓，目标是在强趋势中提高收益上限并保留下限控制。",
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
            PortfolioPresetAllocationSpec("VolumeConfirmedMomentumStrategy", 0.2, "量价趋势确认"),
            PortfolioPresetAllocationSpec("MacdTrendStrategy", 0.15, "趋势延续确认"),
            PortfolioPresetAllocationSpec("AtrVolatilityBreakoutStrategy", 0.15, "波动突破确认"),
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
