from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from ai_trade_system.agent.openclaw import OpenClawConnector
from ai_trade_system.automation.models import (
    AutomationConfig,
    RadarCandidateScore,
    WeeklyAnalysisItem,
    WeeklyAnalysisResult,
    WeeklyAnalysisSection,
    WeeklyRadarResult,
)


Analyzer = Callable[[str, dict[str, Any]], dict[str, Any]]


SECTION_LABELS = {
    "star": "科创板 Top10",
    "chinext": "创业板 Top10",
    "combined_non_st": "综合非 ST Top10",
}


def analyze_weekly_radar_result(
    weekly: WeeklyRadarResult,
    *,
    config: AutomationConfig,
    generated_at: str | None = None,
    analyzer: Analyzer | None = None,
) -> WeeklyAnalysisResult:
    generated = generated_at or datetime.now().replace(microsecond=0).isoformat()
    analyze = analyzer or OpenClawConnector().research
    sections: list[WeeklyAnalysisSection] = []
    for key, candidates in _analysis_sections(weekly).items():
        items = [
            _analyze_candidate(candidate, key, index, weekly, analyze)
            for index, candidate in enumerate(candidates[: config.weekly_analysis_top_n], start=1)
        ]
        ok_count = sum(1 for item in items if item.analysis_status == "ok")
        section_status = "success" if ok_count == len(items) and items else "partial" if items else "empty"
        if items and ok_count == 0:
            section_status = items[0].analysis_status
        sections.append(
            WeeklyAnalysisSection(
                key=key,
                label=SECTION_LABELS.get(key, key),
                status=section_status,
                summary=f"{SECTION_LABELS.get(key, key)} 深度分析完成：ok={ok_count}/{len(items)}。",
                items=items,
            )
        )
    statuses = {section.status for section in sections}
    if not sections or statuses <= {"empty"}:
        status = "failed"
    elif statuses <= {"success", "empty"}:
        status = "success"
    elif statuses <= {"not_configured", "empty"}:
        status = "not_configured"
    else:
        status = "partial"
    message = weekly_analysis_message(weekly, sections)
    return WeeklyAnalysisResult(
        run_id=f"analysis-{_week_key(generated)}",
        weekly_run_id=weekly.run_id,
        generated_at=generated,
        status=status,
        delivery_channel=config.weekly_delivery_channel,
        sections=sections,
        message=message,
    )


def weekly_analysis_message(weekly: WeeklyRadarResult, sections: list[WeeklyAnalysisSection]) -> str:
    lines = [
        "本周股票扫描与AI深度分析",
        f"周扫描：{weekly.run_id}（生成时间：{weekly.generated_at}）",
        f"扫描覆盖：候选 {weekly.total_candidates}；已扫描 {weekly.scanned}；缺数据 {weekly.missing}",
        "",
    ]
    for section in sections:
        lines.append(section.label)
        if not section.items:
            lines.append("- 暂无候选。")
            lines.append("")
            continue
        for item in section.items:
            score = f"{item.scan_score:.2f}" if isinstance(item.scan_score, (int, float)) else "-"
            lines.append(f"{item.rank}. {item.name or item.code}({item.code}.{item.exchange}) 分数 {score}")
            lines.append(f"   本地缠论：{_chan_basis_line(item.scan_signal_title, item.chan_multilevel_basis, item.scan_reason)}")
            lines.append(f"   扫描：{item.scan_signal_title or '-'}；{item.scan_reason or '-'}")
            lines.append(f"   AI深度分析：{_compact_summary(item.summary)}")
            lines.append(f"   证据：{item.evidence_status}；置信度：{item.confidence}；状态：{item.analysis_status}")
        lines.append("")
    lines.append("结论仅用于研究复核，不构成实盘买卖指令；交易动作仍需回测、风控和纸面交易验证。")
    return "\n".join(lines)


def _analysis_sections(weekly: WeeklyRadarResult) -> dict[str, list[RadarCandidateScore]]:
    sections: dict[str, list[RadarCandidateScore]] = {}
    for key in ("star", "chinext", "combined_non_st"):
        candidates = weekly.board_top.get(key, [])
        if candidates:
            sections[key] = candidates
    if not sections:
        sections["combined_non_st"] = weekly.top
    return sections


def _analyze_candidate(
    candidate: RadarCandidateScore,
    board: str,
    rank: int,
    weekly: WeeklyRadarResult,
    analyzer: Analyzer,
) -> WeeklyAnalysisItem:
    chan_basis = _chan_multilevel_basis(candidate)
    prompt = (
        f"请对本周扫描候选 {candidate.name}({candidate.code}.{candidate.exchange}) 做AI深度分析。"
        "需要覆盖：技术结构、基本面、公告新闻、行业催化、主要风险、下周跟踪重点。"
        f"本地扫描板块：{SECTION_LABELS.get(board, board)}；排名 {rank}；综合分 {candidate.composite_score}；"
        f"信号 {candidate.chan_signal_title or '未记录'}；扫描原因：{candidate.reason}。"
        f"本地缠论多级联动依据：{chan_basis}。"
        "技术结构部分必须先解释日线锚定与低级别反转/风险确认如何影响跟踪结论；不要只输出基本面泛评。"
        "请给出审慎结论，并保留外部证据来源。"
    )
    context = {
        "symbol": candidate.code,
        "code": candidate.code,
        "name": candidate.name,
        "exchange": candidate.exchange,
        "board": board,
        "weekly_run_id": weekly.run_id,
        "weekly_candidate": candidate.as_dict(),
        "source_workflow": "weekly_scan_deep_analysis",
    }
    payload = analyzer(prompt, context)
    analysis_status = str(payload.get("status", "ok"))
    sources = _source_dicts(payload.get("sources", []))
    evidence_status = "verified" if _has_external_evidence(sources) else "missing_external_evidence"
    summary = str(payload.get("summary") or "")
    confidence = str(payload.get("confidence") or "medium")
    if analysis_status == "ok" and evidence_status != "verified":
        analysis_status = "failed"
        confidence = "low"
        summary = "外部证据不足：AI 返回了研究文本，但没有可验证 URL；本次不采纳为已验证深度分析。"
    return WeeklyAnalysisItem(
        rank=rank,
        code=candidate.code,
        name=candidate.name,
        exchange=candidate.exchange,
        board=board,
        scan_score=candidate.composite_score,
        latest_day=candidate.latest_day,
        scan_signal_title=candidate.chan_signal_title,
        scan_reason=candidate.reason,
        analysis_status=analysis_status,
        summary=summary,
        confidence=confidence,
        evidence_status=evidence_status,
        sources=sources,
        chan_multilevel_basis=chan_basis,
    )


def _source_dicts(sources: object) -> list[dict[str, Any]]:
    if not isinstance(sources, list):
        return []
    normalized: list[dict[str, Any]] = []
    for source in sources:
        if isinstance(source, dict):
            normalized.append(dict(source))
        elif isinstance(source, str):
            normalized.append({"url": source})
    return normalized


def _has_external_evidence(sources: list[dict[str, Any]]) -> bool:
    return any(str(source.get("url") or "").startswith(("http://", "https://")) for source in sources)


def _compact_summary(summary: str, max_chars: int = 160) -> str:
    text = " ".join(str(summary or "未返回摘要").split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _chan_multilevel_basis(candidate: RadarCandidateScore) -> str:
    details = [
        candidate.chan_signal_title or "未记录信号",
        f"Chan分 {_format_number(candidate.chan_score)}",
        f"量价分 {_format_number(candidate.volume_score)}",
        "量能确认" if candidate.volume_entry_ready else "量能未确认",
        f"最新日 {candidate.latest_day or '-'}",
        f"扫描原因 {candidate.reason or '-'}",
    ]
    return "缠论多级联动：" + "；".join(details)


def _chan_basis_line(signal_title: str | None, basis: str | None, reason: str | None) -> str:
    if basis:
        body = basis.split("：", 1)[1] if basis.startswith("缠论多级联动：") else basis
    else:
        body = reason or "-"
    signal = signal_title or "未记录信号"
    if body.startswith(signal):
        return body
    return f"{signal}；{body}"


def _format_number(value: float | int | None) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.2f}"
    return "-"


def _week_key(value: str) -> str:
    day = value[:10]
    year, week, _weekday = datetime.fromisoformat(day).date().isocalendar()
    return f"{year}-W{week:02d}"
