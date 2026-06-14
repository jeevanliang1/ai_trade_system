from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Mapping

from ai_trade_system.indicators import IndicatorSnapshot


PROMPT_VERSION = "ai-quant-research-v1"


@dataclass(frozen=True)
class LLMResearchRequest:
    symbol: str
    horizon: str
    indicator_snapshot: IndicatorSnapshot
    information_notes: list[str] = field(default_factory=list)
    risk_context: Mapping[str, float | int | str | None] = field(default_factory=dict)
    prompt_mode: str = "balanced"


@dataclass(frozen=True)
class LLMInsight:
    symbol: str
    horizon: str
    direction: str
    confidence: int
    suggested_action: str
    technical_evidence: list[str]
    information_evidence: list[str]
    risk_warnings: list[str]
    prompt_version: str
    provider: str
    created_at: str


def build_research_prompt(request: LLMResearchRequest) -> str:
    snapshot = request.indicator_snapshot
    notes = "\n".join(f"- {note}" for note in request.information_notes) or "- 无"
    risk_lines = "\n".join(f"- {key}: {value}" for key, value in request.risk_context.items()) or "- 无"
    return "\n".join(
        [
            f"你是 A 股量化研究员，模式：{request.prompt_mode}。",
            f"股票：{request.symbol}，观察周期：{request.horizon}。",
            "请结合技术指标、信息面和风控约束，输出结构化研究观点，不要输出实盘下单指令。",
            "技术指标：",
            f"- 日期：{snapshot.trading_day}",
            f"- 收盘价：{snapshot.close_price:.2f}",
            f"- 短均线：{_format_optional(snapshot.short_ma)}",
            f"- 长均线：{_format_optional(snapshot.long_ma)}",
            f"- RSI：{_format_optional(snapshot.rsi)}",
            f"- 动量：{_format_optional(snapshot.momentum)}%",
            f"- 回撤：{snapshot.drawdown_pct:.2f}%",
            f"- 趋势：{snapshot.trend}",
            "信息面：",
            notes,
            "风控上下文：",
            risk_lines,
        ]
    )


class MockLLMProvider:
    name = "MockLLMProvider"

    def generate_insight(self, request: LLMResearchRequest) -> LLMInsight:
        snapshot = request.indicator_snapshot
        information_score = _information_score(request.information_notes)
        technical_score = _technical_score(snapshot)
        risk_penalty, risk_warnings = _risk_penalty(snapshot, request.risk_context)
        raw_score = technical_score + information_score - risk_penalty

        if raw_score >= 2:
            direction = "bullish"
            suggested_action = "buy"
        elif raw_score <= -2:
            direction = "bearish"
            suggested_action = "reduce"
        else:
            direction = "neutral"
            suggested_action = "hold"

        confidence = max(35, min(92, 55 + raw_score * 8))
        if request.prompt_mode == "conservative":
            confidence = max(30, confidence - 8)
        elif request.prompt_mode == "aggressive":
            confidence = min(95, confidence + 5)

        return LLMInsight(
            symbol=request.symbol,
            horizon=request.horizon,
            direction=direction,
            confidence=int(confidence),
            suggested_action=suggested_action,
            technical_evidence=_technical_evidence(snapshot),
            information_evidence=request.information_notes or ["未提供信息面输入，结论主要来自技术指标。"],
            risk_warnings=risk_warnings,
            prompt_version=PROMPT_VERSION,
            provider=self.name,
            created_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        )


def _technical_score(snapshot: IndicatorSnapshot) -> int:
    score = 0
    if snapshot.trend == "bullish":
        score += 2
    elif snapshot.trend == "bearish":
        score -= 2
    if snapshot.momentum is not None:
        if snapshot.momentum > 3:
            score += 1
        elif snapshot.momentum < -3:
            score -= 1
    if snapshot.rsi is not None:
        if snapshot.rsi >= 75:
            score -= 1
        elif snapshot.rsi <= 30:
            score += 1
    return score


def _information_score(notes: list[str]) -> int:
    positive_terms = ("利好", "改善", "支持", "增长", "突破", "回购", "增持")
    negative_terms = ("利空", "下滑", "风险", "处罚", "减持", "亏损", "监管")
    text = " ".join(notes)
    return sum(term in text for term in positive_terms) - sum(term in text for term in negative_terms)


def _risk_penalty(snapshot: IndicatorSnapshot, risk_context: Mapping[str, float | int | str | None]) -> tuple[int, list[str]]:
    warnings: list[str] = []
    penalty = 0
    max_drawdown = risk_context.get("max_drawdown_pct")
    if isinstance(max_drawdown, (int, float)) and abs(snapshot.drawdown_pct) > float(max_drawdown):
        penalty += 2
        warnings.append(f"当前回撤 {abs(snapshot.drawdown_pct):.2f}% 超过风控阈值 {float(max_drawdown):.2f}%。")
    if snapshot.rsi is not None and snapshot.rsi >= 75:
        penalty += 1
        warnings.append("RSI 已处于偏热区间，追高风险上升。")
    if snapshot.drawdown_pct <= -15:
        penalty += 1
        warnings.append("价格相对近期高点回撤较深，需确认是否处于趋势破坏阶段。")
    return penalty, warnings or ["未触发主要风控警示。"]


def _technical_evidence(snapshot: IndicatorSnapshot) -> list[str]:
    evidence = [f"趋势状态为 {snapshot.trend}。"]
    if snapshot.short_ma is not None and snapshot.long_ma is not None:
        evidence.append(f"短均线 {snapshot.short_ma:.2f}，长均线 {snapshot.long_ma:.2f}。")
    if snapshot.momentum is not None:
        evidence.append(f"动量为 {snapshot.momentum:.2f}%。")
    if snapshot.rsi is not None:
        evidence.append(f"RSI 为 {snapshot.rsi:.2f}。")
    return evidence


def _format_optional(value: float | None) -> str:
    return "无" if value is None else f"{value:.2f}"
