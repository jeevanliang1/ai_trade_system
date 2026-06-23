from __future__ import annotations

from datetime import datetime
from typing import Any

from ai_trade_system.agent.openclaw import OpenClawConnector
from ai_trade_system.strategy_defaults import (
    DEFAULT_SCAN_SCORE_MODE,
    DEFAULT_SCAN_STRATEGY_ID,
    chan_daily_anchor_scan_params,
)


DEFAULT_STRATEGY_ID = DEFAULT_SCAN_STRATEGY_ID

WEEKLY_BOARD_SECTION_LABELS = {
    "star": "科创板 Top10",
    "chinext": "创业板 Top10",
    "combined_non_st": "综合非 ST Top10",
}
WEEKLY_BOARD_SECTION_ORDER = ("star", "chinext", "combined_non_st")


class AgentSystemToolExecutor:
    def __init__(self, openclaw: OpenClawConnector | None = None):
        self.openclaw = openclaw or OpenClawConnector()

    def run(
        self,
        tool_name: str,
        prompt: str,
        source: str,
        context: dict[str, Any],
        previous_outputs: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        previous = previous_outputs or {}
        try:
            if tool_name == "data.update":
                return self._data_update(context)
            if tool_name == "automation.weekly_result":
                return self._automation_weekly_result(prompt, context)
            if tool_name == "research.fundamental":
                return self._fundamental_research(prompt, context)
            if tool_name == "research.batch_fundamental":
                return self._batch_fundamental_research(prompt, context, previous)
            if tool_name == "radar.scan":
                return self._radar_scan(context)
            if tool_name == "backtest.run":
                return self._backtest_run(context)
            if tool_name == "risk.evaluate":
                return self._risk_evaluate(context, previous)
            if tool_name == "paper.run":
                return self._paper_run(context)
            if tool_name == "share.weixin":
                return self._weixin_share(context, previous)
        except Exception as exc:
            return {"status": "failed", "summary": f"{tool_name} 执行失败：{exc}", "error": str(exc)}
        return {"status": "failed", "summary": f"未知 Agent system tool：{tool_name}", "error": "unknown_tool"}

    def _data_update(self, context: dict[str, Any]) -> dict[str, Any]:
        from ai_trade_system.api.schemas import DataUpdateWatchlistRequest
        from ai_trade_system.api import service as api_service
        from ai_trade_system.data_manager import update_stock_data

        settings = self._settings(context)
        if settings.symbol:
            stock = self._stock(context, settings)
            result = update_stock_data(
                stock,
                start_date=settings.start_date,
                end_date=settings.end_date,
                adjust=settings.adjust,
                timeframe=settings.timeframe,
                if_stale=bool(context.get("if_stale", True)),
            ).as_dict()
            return {
                "status": result["status"],
                "summary": f"{settings.symbol} 行情数据{self._data_status_label(result['status'])}，本地文件 {result['latest_path']}。",
                "target": {"symbol": settings.symbol, "exchange": settings.exchange},
                "file": self._compact_data_file(result),
            }

        payload = api_service.update_watchlist_data(
            DataUpdateWatchlistRequest(
                start_date=context.get("start_date"),
                end_date=context.get("end_date"),
                adjust=context.get("adjust", "qfq"),
                timeframe=context.get("timeframe", "daily"),
                if_stale=bool(context.get("if_stale", True)),
            )
        )
        return {
            "status": "ok" if payload.get("failed", 0) == 0 else "failed",
            "summary": f"自选股数据维护完成：updated={payload.get('updated', 0)} skipped={payload.get('skipped', 0)} failed={payload.get('failed', 0)}。",
            "counts": {key: payload.get(key, 0) for key in ("updated", "skipped", "failed")},
            "files": [self._compact_data_file(item) for item in payload.get("files", [])[:10]],
        }

    def _fundamental_research(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        return self.openclaw.research(prompt, context)

    def _automation_weekly_result(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        from ai_trade_system.api import service as api_service
        from ai_trade_system.automation.models import WeeklyRadarResult
        from ai_trade_system.automation.store import AutomationStore, week_key_for_datetime

        store = AutomationStore()
        weekly = store.load_weekly_result()
        limit = int(context.get("limit", context.get("top_n", 10)))
        now = _parse_datetime(context.get("now")) or datetime.now()
        require_current_week = any(term in prompt for term in ("这周", "本周")) or context.get("week") in {"current", "this_week"}
        require_analysis = self._weekly_prompt_needs_analysis(prompt, context)
        auto_run_enabled = context.get("auto_run_weekly_scan", True) is not False
        analysis = store.load_weekly_analysis(week_key_for_datetime(weekly.generated_at)) if weekly else None
        missing_reason = self._weekly_missing_reason(store, weekly, require_current_week, require_analysis, analysis, now)
        auto_ran_scan = False

        if missing_reason and auto_run_enabled:
            try:
                weekly = WeeklyRadarResult.from_dict(api_service.run_automation_weekly())
                auto_ran_scan = True
            except Exception as exc:
                return {
                    "status": "failed",
                    "summary": f"未找到可用的本周扫描结果，自动触发周扫描失败：{exc}",
                    "missing_reason": missing_reason,
                    "auto_run_attempted": True,
                    "auto_ran_scan": False,
                    "top_candidates": [],
                }

        if weekly is None:
            return {
                "status": "failed",
                "summary": "未找到周扫描结果；当前没有可读取的持久化周榜。",
                "missing_reason": missing_reason or "missing_result_file",
                "auto_run_attempted": auto_run_enabled,
                "auto_ran_scan": auto_ran_scan,
                "top_candidates": [],
            }

        generated_at = _parse_datetime(weekly.generated_at)
        is_current_week = bool(generated_at and generated_at.isocalendar()[:2] == now.isocalendar()[:2])
        status = "stale" if require_current_week and not is_current_week else "ok"
        top_candidates = [self._compact_weekly_candidate(candidate) for candidate in weekly.top[:limit]]
        board_top = {
            key: [self._compact_weekly_candidate(candidate) for candidate in candidates]
            for key, candidates in weekly.board_top.items()
        }
        analysis = store.load_weekly_analysis(week_key_for_datetime(weekly.generated_at))
        freshness = "本周" if is_current_week else "非本周"
        auto_run_note = "；已自动触发周扫描" if auto_ran_scan else ""
        section_note = (
            "；分板块 "
            + " ".join(
                f"{WEEKLY_BOARD_SECTION_LABELS.get(key, key)}={len(items)}"
                for key, items in board_top.items()
            )
            if board_top
            else ""
        )
        return {
            "status": status,
            "summary": f"周扫描结果读取完成：{freshness} run_id={weekly.run_id} top={len(top_candidates)} scanned={weekly.scanned} missing={weekly.missing}{section_note}{auto_run_note}。",
            "run_id": weekly.run_id,
            "generated_at": weekly.generated_at,
            "is_current_week": is_current_week,
            "missing_reason": missing_reason,
            "auto_run_attempted": bool(missing_reason and auto_run_enabled),
            "auto_ran_scan": auto_ran_scan,
            "total_candidates": weekly.total_candidates,
            "scanned": weekly.scanned,
            "missing": weekly.missing,
            "top_candidates": top_candidates,
            "board_top": board_top,
            "board_top_counts": {key: len(items) for key, items in board_top.items()},
            "analysis_cache": analysis.as_dict() if analysis else None,
            "source_path": store.weekly_path.as_posix(),
        }

    def _weekly_missing_reason(
        self,
        store,
        weekly,
        require_current_week: bool,
        require_analysis: bool,
        analysis: Any,
        now: datetime,
    ) -> str | None:
        if weekly is None:
            weekly_runs = [run for run in store.load_runs() if run.task == "weekly"]
            if not weekly_runs:
                return "never_scanned"
            latest = weekly_runs[-1]
            if latest.status in {"success", "partial"}:
                return "result_not_persisted"
            if latest.status == "failed":
                return "previous_scan_failed"
            return "missing_result_file"
        generated_at = _parse_datetime(weekly.generated_at)
        is_current_week = bool(generated_at and generated_at.isocalendar()[:2] == now.isocalendar()[:2])
        if require_current_week and not is_current_week:
            return "stale_result"
        if require_current_week and require_analysis and not weekly.board_top and not self._weekly_analysis_has_core_boards(analysis):
            return "legacy_result_missing_board_top"
        return None

    def _weekly_prompt_needs_analysis(self, prompt: str, context: dict[str, Any]) -> bool:
        if context.get("require_weekly_analysis") is True:
            return True
        return any(term in prompt for term in ("分析", "结论", "输出给我", "分享", "发给我", "发送"))

    def _weekly_analysis_has_core_boards(self, analysis: Any) -> bool:
        if analysis is None:
            return False
        sections = getattr(analysis, "sections", None)
        if not isinstance(sections, list):
            return False
        counts = {section.key: len(section.items) for section in sections if hasattr(section, "key")}
        return counts.get("star", 0) > 0 and counts.get("chinext", 0) > 0

    def _batch_fundamental_research(self, prompt: str, context: dict[str, Any], previous_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        weekly_output = previous_outputs.get("automation.weekly_result") or {}
        cached = self._cached_weekly_analysis_research(weekly_output.get("analysis_cache"))
        if cached:
            return cached
        board_sections = self._weekly_board_sections(weekly_output.get("board_top"), context)
        if board_sections:
            return self._batch_board_fundamental_research(prompt, context, board_sections)
        candidates = context.get("candidates")
        if not isinstance(candidates, list):
            candidates = weekly_output.get("top_candidates", [])
        if not candidates:
            return {
                "status": "failed",
                "summary": "没有可研究的周扫描候选；请先读取或生成周扫描结果。",
                "items": [],
            }

        limit = int(context.get("research_limit", min(int(context.get("limit", 5)), len(candidates))))
        items: list[dict[str, Any]] = []
        for candidate in candidates[:limit]:
            items.append(self._research_weekly_candidate(prompt, context, candidate))

        statuses = {item["status"] for item in items}
        if statuses and statuses <= {"failed"}:
            status = "failed"
        elif statuses and statuses <= {"not_configured"}:
            status = "not_configured"
        else:
            status = "ok"
        return {
            "status": status,
            "summary": f"批量基本面/信息面研究完成：requested={limit} researched={len(items)} ok={sum(1 for item in items if item['status'] == 'ok')}。",
            "requested": limit,
            "researched": len(items),
            "items": items,
        }

    def _weekly_board_sections(self, board_top: object, context: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(board_top, dict) or not board_top:
            return []
        section_limit = int(context.get("section_limit", context.get("weekly_analysis_top_n", 10)))
        ordered_keys = [
            *[key for key in WEEKLY_BOARD_SECTION_ORDER if key in board_top],
            *[key for key in board_top if key not in WEEKLY_BOARD_SECTION_ORDER],
        ]
        sections: list[dict[str, Any]] = []
        for key in ordered_keys:
            raw_items = board_top.get(key)
            if not isinstance(raw_items, list) or not raw_items:
                continue
            compact_items = [self._compact_candidate_dict(item) for item in raw_items[:section_limit]]
            sections.append(
                {
                    "key": key,
                    "label": WEEKLY_BOARD_SECTION_LABELS.get(str(key), str(key)),
                    "items": compact_items,
                }
            )
        return sections

    def _batch_board_fundamental_research(
        self,
        prompt: str,
        context: dict[str, Any],
        board_sections: list[dict[str, Any]],
    ) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        sections: list[dict[str, Any]] = []
        for section in board_sections:
            section_items: list[dict[str, Any]] = []
            for candidate in section["items"]:
                item = self._research_weekly_candidate(
                    prompt,
                    context,
                    candidate,
                    section_key=section["key"],
                    section_label=section["label"],
                )
                items.append(item)
                section_items.append(item)
            section_status = self._research_status(section_items)
            sections.append(
                {
                    "key": section["key"],
                    "label": section["label"],
                    "status": section_status,
                    "summary": f"{section['label']} 外部研究完成：requested={len(section_items)} ok={sum(1 for item in section_items if item['status'] == 'ok')}。",
                    "items": section_items,
                }
            )
        return {
            "status": self._research_status(items),
            "summary": f"批量基本面/信息面研究完成：sections={len(sections)} requested={len(items)} researched={len(items)} ok={sum(1 for item in items if item['status'] == 'ok')}。",
            "requested": len(items),
            "researched": len(items),
            "items": items,
            "sections": sections,
        }

    def _research_status(self, items: list[dict[str, Any]]) -> str:
        statuses = {item.get("status") for item in items}
        if not statuses:
            return "empty"
        if statuses <= {"ok"}:
            return "ok"
        if statuses <= {"failed"}:
            return "failed"
        if statuses <= {"not_configured"}:
            return "not_configured"
        return "partial"

    def _research_weekly_candidate(
        self,
        prompt: str,
        context: dict[str, Any],
        candidate: Any,
        *,
        section_key: str | None = None,
        section_label: str | None = None,
    ) -> dict[str, Any]:
        compact = self._compact_candidate_dict(candidate)
        symbol = compact.get("code") or compact.get("symbol")
        exchange = compact.get("exchange")
        name = compact.get("name") or symbol
        board = compact.get("board") or section_key
        chan_basis = self._chan_multilevel_basis(compact)
        research_context = {
            **context,
            "symbol": symbol,
            "code": symbol,
            "exchange": exchange,
            "name": name,
            "board": board,
            "section": section_key,
            "section_label": section_label,
            "weekly_candidate": compact,
            "chan_multilevel_basis": chan_basis,
            "source_workflow": "weekly_scan_share",
        }
        research_prompt = (
            f"请对周度扫描候选 {name}({symbol}.{exchange}) 做基本面和信息面研究。"
            "重点覆盖主营业务、财务质量、公告新闻、行业催化、主要风险和研究结论。"
            f"本地扫描板块：{section_label or WEEKLY_BOARD_SECTION_LABELS.get(str(board), str(board or '综合榜'))}；"
            f"本地缠论多级联动依据：{chan_basis}。"
            "技术结构部分必须先解释日线锚定与低级别反转/风险确认如何影响跟踪结论；不要只输出基本面泛评。"
            f"用户原始任务：{prompt}"
        )
        payload = self.openclaw.research(research_prompt, research_context)
        research_status = payload.get("status", "ok")
        sources = payload.get("sources", [])
        summary = payload.get("summary", "")
        confidence = payload.get("confidence", "medium")
        evidence_status = "verified" if self._has_external_research_evidence(sources) else "missing_external_evidence"
        if research_status == "ok" and evidence_status != "verified":
            research_status = "failed"
            confidence = "low"
            summary = (
                "外部证据不足：OpenClaw 返回了研究文本，但没有可验证的网页 URL 或外部来源；"
                "为避免 AI 编造，本次不采纳该基本面/信息面摘要。"
            )
        return {
            "rank": compact.get("rank"),
            "code": symbol,
            "name": name,
            "exchange": exchange,
            "board": board,
            "section": section_key,
            "section_label": section_label,
            "scan_score": compact.get("composite_score"),
            "scan_signal_title": compact.get("chan_signal_title"),
            "scan_reason": compact.get("reason"),
            "chan_multilevel_basis": chan_basis,
            "status": research_status,
            "summary": summary,
            "sources": sources,
            "confidence": confidence,
            "evidence_status": evidence_status,
        }

    def _cached_weekly_analysis_research(self, analysis_cache: object) -> dict[str, Any] | None:
        if not isinstance(analysis_cache, dict):
            return None
        if analysis_cache.get("status") not in {"success", "partial"}:
            return None
        sections = analysis_cache.get("sections")
        if not isinstance(sections, list) or not sections:
            return None
        items: list[dict[str, Any]] = []
        compact_sections: list[dict[str, Any]] = []
        for section in sections:
            if not isinstance(section, dict):
                continue
            section_items: list[dict[str, Any]] = []
            for raw_item in section.get("items", []):
                if not isinstance(raw_item, dict):
                    continue
                item = {
                    "rank": raw_item.get("rank"),
                    "code": raw_item.get("code"),
                    "name": raw_item.get("name"),
                    "exchange": raw_item.get("exchange"),
                    "board": raw_item.get("board") or section.get("key"),
                    "section": section.get("key"),
                    "section_label": section.get("label"),
                    "scan_score": raw_item.get("scan_score"),
                    "scan_signal_title": raw_item.get("scan_signal_title"),
                    "scan_reason": raw_item.get("scan_reason"),
                    "chan_multilevel_basis": raw_item.get("chan_multilevel_basis")
                    or self._chan_multilevel_basis(raw_item),
                    "status": raw_item.get("analysis_status", "cached"),
                    "summary": raw_item.get("summary", ""),
                    "sources": raw_item.get("sources", []),
                    "confidence": raw_item.get("confidence", "medium"),
                    "evidence_status": raw_item.get("evidence_status", "unknown"),
                }
                items.append(item)
                section_items.append(item)
            compact_sections.append(
                {
                    "key": section.get("key"),
                    "label": section.get("label"),
                    "status": section.get("status"),
                    "summary": section.get("summary"),
                    "items": section_items,
                }
            )
        return {
            "status": "cached",
            "summary": f"已复用本地周度AI深度分析缓存：sections={len(compact_sections)} items={len(items)}。",
            "requested": len(items),
            "researched": len(items),
            "items": items,
            "sections": compact_sections,
            "cache_run_id": analysis_cache.get("run_id"),
            "weekly_run_id": analysis_cache.get("weekly_run_id"),
            "message": analysis_cache.get("message", ""),
        }

    def _has_external_research_evidence(self, sources: object) -> bool:
        if not isinstance(sources, list):
            return False
        for source in sources:
            if not isinstance(source, dict):
                continue
            url = str(source.get("url") or "").strip()
            if url.startswith(("http://", "https://")):
                return True
        return False

    def _radar_scan(self, context: dict[str, Any]) -> dict[str, Any]:
        from ai_trade_system.api import service as api_service
        from ai_trade_system.api.schemas import ResearchSignalBatchRequest

        settings = self._settings(context)
        request = ResearchSignalBatchRequest(
            settings=settings,
            query=str(context.get("query", "")),
            limit=int(context.get("limit", context.get("scan_limit", 20))),
            min_bars=int(context.get("min_bars", 60)),
            lookback=int(context.get("lookback", 120)),
            universe=context.get("universe", "current"),
            score_mode=context.get("score_mode", DEFAULT_SCAN_SCORE_MODE),
            auto_update_data=bool(context.get("auto_update_data", False)),
            if_stale=bool(context.get("if_stale", True)),
            adjust=context.get("adjust"),
        )
        payload = api_service.batch_research_signals(request)
        top_rows = [
            {
                "rank": row.get("rank"),
                "code": row.get("code"),
                "name": row.get("name"),
                "exchange": row.get("exchange"),
                "status": row.get("status"),
                "score": row.get("score"),
                "latest_signal": row.get("latest_signal"),
                "blockers": row.get("blockers", []),
            }
            for row in payload.get("rows", [])[:5]
        ]
        return {
            "status": "ok" if payload.get("available", 0) else "failed",
            "summary": f"信号雷达扫描完成：scanned={payload.get('scanned', 0)} available={payload.get('available', 0)} missing={payload.get('missing', 0)}。",
            "query": payload.get("query"),
            "universe": payload.get("universe"),
            "score_mode": payload.get("score_mode"),
            "scanned": payload.get("scanned", 0),
            "available": payload.get("available", 0),
            "missing": payload.get("missing", 0),
            "top_rows": top_rows,
            "data_update": payload.get("data_update"),
        }

    def _backtest_run(self, context: dict[str, Any]) -> dict[str, Any]:
        from ai_trade_system.api import service as api_service
        from ai_trade_system.api.schemas import BacktestRequest

        settings = self._settings(context)
        request = BacktestRequest(
            settings=settings,
            strategy=self._strategy(context, settings),
            portfolio=context.get("portfolio"),
            mode=context.get("mode", "single"),
        )
        payload = api_service.run_backtest_request(request)
        metrics = payload.get("metrics", {})
        compact_metrics = {
            "total_return_pct": metrics.get("total_return_pct"),
            "benchmark_return_pct": metrics.get("benchmark_return_pct"),
            "max_drawdown_pct": metrics.get("max_drawdown_pct"),
            "win_rate": metrics.get("win_rate"),
            "trade_count": metrics.get("trade_count"),
            "final_equity": metrics.get("final_equity"),
        }
        return {
            "status": "ok",
            "summary": f"回测完成：final_equity={compact_metrics.get('final_equity')} trades={compact_metrics.get('trade_count')} max_drawdown={compact_metrics.get('max_drawdown_pct')}。",
            "metrics": compact_metrics,
            "trade_count": len(payload.get("trades", [])),
            "risk_status": payload.get("risk_status"),
        }

    def _risk_evaluate(self, context: dict[str, Any], previous_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        from ai_trade_system.api import service as api_service
        from ai_trade_system.api.schemas import RiskConfigView

        settings = self._settings(context)
        metrics = context.get("metrics")
        if not isinstance(metrics, dict):
            metrics = (previous_outputs.get("backtest.run") or {}).get("metrics", {})
        config_payload = context.get("risk_config") if isinstance(context.get("risk_config"), dict) else {}
        config = RiskConfigView(
            max_drawdown_pct=config_payload.get("max_drawdown_pct", settings.max_drawdown_pct),
            max_order_cash=config_payload.get("max_order_cash", settings.max_order_cash),
            min_cash_balance=config_payload.get("min_cash_balance", settings.min_cash_balance),
            max_position_shares=config_payload.get("max_position_shares", settings.max_position_shares),
            cooldown_days=config_payload.get("cooldown_days", 0),
            enabled=config_payload.get("enabled", settings.risk_enabled),
        )
        payload = api_service.evaluate_risk(metrics, config)
        warnings = payload.get("warnings", [])
        if not payload.get("enabled", True):
            status = "disabled"
        elif payload.get("ok", False):
            status = "passed"
        else:
            status = "blocked"
        return {
            "status": "ok" if status in {"passed", "disabled"} else "failed",
            "summary": f"风控评估完成：status={status} warnings={len(warnings)}。",
            "risk_status": payload,
            "metrics": metrics,
        }

    def _paper_run(self, context: dict[str, Any]) -> dict[str, Any]:
        from ai_trade_system.api import service as api_service
        from ai_trade_system.api.schemas import PaperRunRequest

        settings = self._settings(context)
        request = PaperRunRequest(
            settings=settings,
            strategy=self._strategy(context, settings),
            portfolio=context.get("portfolio"),
            mode=context.get("mode", "single"),
        )
        payload = api_service.run_paper_request(request)
        summary = payload.get("summary", {})
        return {
            "status": "ok",
            "summary": f"纸面交易回放完成：events={len(payload.get('events', []))} orders={len(payload.get('orders', []))}。",
            "event_count": len(payload.get("events", [])),
            "order_count": len(payload.get("orders", [])),
            "summary_payload": summary,
        }

    def _weixin_share(self, context: dict[str, Any], previous_outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        weekly = previous_outputs.get("automation.weekly_result") or {}
        research = previous_outputs.get("research.batch_fundamental") or {}
        section_message = self._sectioned_weekly_share(context, weekly, research)
        if section_message is not None:
            return section_message
        candidates = weekly.get("top_candidates", [])
        research_items = research.get("items", [])
        research_by_code = {item.get("code"): item for item in research_items}
        researched_candidates = [
            (self._compact_candidate_dict(candidate), research_by_code.get(self._compact_candidate_dict(candidate).get("code")))
            for candidate in candidates
            if research_by_code.get(self._compact_candidate_dict(candidate).get("code"))
        ]
        scan_only_candidates = [
            self._compact_candidate_dict(candidate)
            for candidate in candidates
            if not research_by_code.get(self._compact_candidate_dict(candidate).get("code"))
        ]
        report_hint = str(context.get("report_path") or context.get("full_report_path") or "").strip()
        lines = [
            "本周股票扫描与AI研究结论",
            f"周扫描：{weekly.get('run_id', '未记录')}（生成时间：{weekly.get('generated_at', '未记录')}）",
            f"候选数量：{len(candidates)}；深度研究：{len(researched_candidates)}；仅扫描：{len(scan_only_candidates)}",
            "",
        ]
        if report_hint:
            lines.extend([f"完整报告：{report_hint}", ""])
        if not candidates:
            lines.append("未找到可分享的周扫描候选。")
        if researched_candidates:
            lines.append("深度研究候选：")
        for index, (compact, item) in enumerate(researched_candidates, start=1):
            score = compact.get("composite_score")
            score_text = f"{score:.2f}" if isinstance(score, (int, float)) else str(score or "-")
            lines.append(f"{index}. {compact.get('name') or compact.get('code')}({compact.get('code')}.{compact.get('exchange')})")
            chan_line = self._optional_chan_basis_line(item or compact)
            if chan_line:
                lines.append(f"   本地缠论：{chan_line}")
            lines.append(f"   扫描结论：综合分 {score_text}；{compact.get('reason') or '未记录扫描原因'}")
            lines.append(f"   外部研究：{self._compact_research_summary((item or {}).get('summary', ''))}")
            lines.append(f"   置信度：{(item or {}).get('confidence', 'medium')}；状态：{(item or {}).get('status', 'ok')}")
        if scan_only_candidates:
            if researched_candidates:
                lines.append("")
            lines.append("仅扫描候选（未做深度外部研究）：")
            for compact in scan_only_candidates:
                score = compact.get("composite_score")
                score_text = f"{score:.2f}" if isinstance(score, (int, float)) else str(score or "-")
                chan_line = self._optional_chan_basis_line(compact)
                detail = f"本地缠论 {chan_line}；{compact.get('reason') or '未记录扫描原因'}" if chan_line else compact.get("reason") or "未记录扫描原因"
                lines.append(
                    f"- {compact.get('name') or compact.get('code')}({compact.get('code')}.{compact.get('exchange')})："
                    f"综合分 {score_text}；{detail}"
                )
        lines.extend(
            [
                "",
                "AI结论：以上结果用于研究和复核，不构成实盘买卖指令；后续如需交易动作仍必须经过回测、风控和纸面交易验证。",
            ]
        )
        message = "\n".join(lines)
        return {
            "status": "prepared",
            "summary": f"微信分享文本已准备：items={len(candidates)}。",
            "delivery": "agent_response",
            "target": context.get("share_target", "weixin"),
            "message": message,
            "item_count": len(candidates),
            "researched_item_count": len(researched_candidates),
            "scan_only_item_count": len(scan_only_candidates),
            "message_chars": len(message),
            "full_report_hint": report_hint or None,
        }

    def _sectioned_weekly_share(
        self,
        context: dict[str, Any],
        weekly: dict[str, Any],
        research: dict[str, Any],
    ) -> dict[str, Any] | None:
        sections = research.get("sections")
        if not isinstance(sections, list) or not sections:
            return None
        lines = [
            "本周股票扫描与AI深度分析结论",
            f"周扫描：{weekly.get('run_id', research.get('weekly_run_id', '未记录'))}（生成时间：{weekly.get('generated_at', '未记录')}）",
            f"缓存：{research.get('cache_run_id', '未记录')}；状态：{research.get('status', 'cached')}",
            "",
        ]
        for section in sections:
            if not isinstance(section, dict):
                continue
            lines.append(str(section.get("label") or section.get("key") or "Top10"))
            items = section.get("items") if isinstance(section.get("items"), list) else []
            if not items:
                lines.append("- 暂无候选。")
                lines.append("")
                continue
            for item in items:
                score = item.get("scan_score")
                score_text = f"{score:.2f}" if isinstance(score, (int, float)) else str(score or "-")
                lines.append(f"{item.get('rank')}. {item.get('name') or item.get('code')}({item.get('code')}.{item.get('exchange')}) 分数 {score_text}")
                lines.append(f"   本地缠论：{self._chan_basis_line(item)}")
                lines.append(f"   扫描：{item.get('scan_reason') or '未记录扫描原因'}")
                lines.append(f"   AI深度分析：{self._compact_research_summary(str(item.get('summary') or ''))}")
                lines.append(f"   证据：{item.get('evidence_status', 'unknown')}；置信度：{item.get('confidence', 'medium')}；状态：{item.get('status', 'cached')}")
            lines.append("")
        lines.append("AI结论：以上结果用于研究和复核，不构成实盘买卖指令；后续如需交易动作仍必须经过回测、风控和纸面交易验证。")
        message = "\n".join(lines)
        item_count = sum(len(section.get("items", [])) for section in sections if isinstance(section, dict))
        return {
            "status": "prepared",
            "summary": f"{context.get('share_target', 'weixin')} 分享文本已准备：sections={len(sections)} items={item_count}。",
            "delivery": "agent_response",
            "target": context.get("share_target", "weixin"),
            "message": message,
            "item_count": item_count,
            "researched_item_count": item_count,
            "scan_only_item_count": 0,
            "message_chars": len(message),
            "full_report_hint": research.get("cache_run_id"),
        }

    def _compact_research_summary(self, summary: str, max_chars: int = 220) -> str:
        clean_lines = []
        for raw_line in str(summary or "").splitlines():
            line = raw_line.strip()
            if not line or line in {"---"}:
                continue
            if line.startswith("**") and line.endswith("**"):
                continue
            clean_lines.append(line)
            if len(" ".join(clean_lines)) >= max_chars:
                break
        if not clean_lines:
            return "未返回摘要"
        return self._truncate_text(" ".join(clean_lines), max_chars)

    def _truncate_text(self, text: str, max_chars: int) -> str:
        normalized = " ".join(str(text).split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1].rstrip() + "…"

    def _settings(self, context: dict[str, Any]):
        from ai_trade_system.api.schemas import PlatformSettings
        from ai_trade_system.data_manager import data_file_for_stock

        settings_payload = dict(context.get("settings") or {})
        symbol = context.get("symbol") or settings_payload.get("symbol")
        exchange = context.get("exchange") or settings_payload.get("exchange")
        adjust = context.get("adjust") or settings_payload.get("adjust") or "qfq"
        timeframe = context.get("timeframe") or settings_payload.get("timeframe") or "daily"
        if symbol:
            settings_payload["symbol"] = symbol
        if exchange:
            settings_payload["exchange"] = exchange
        if adjust:
            settings_payload["adjust"] = adjust
        if timeframe:
            settings_payload["timeframe"] = timeframe
        if symbol and exchange and "csv_path" not in settings_payload:
            settings_payload["csv_path"] = data_file_for_stock(
                self._stock(context, PlatformSettings(**settings_payload)),
                adjust=adjust,
                timeframe=timeframe,
            ).latest_path.as_posix()
        for key in ("start_date", "end_date", "log_path"):
            if key in context and key not in settings_payload:
                settings_payload[key] = context[key]
        return PlatformSettings(**settings_payload)

    def _strategy(self, context: dict[str, Any], settings):
        from ai_trade_system.api.schemas import StrategySelection

        strategy_payload = context.get("strategy")
        if isinstance(strategy_payload, StrategySelection):
            return strategy_payload
        if isinstance(strategy_payload, dict):
            return StrategySelection(**strategy_payload)
        return StrategySelection(
            id=DEFAULT_STRATEGY_ID,
            params=chan_daily_anchor_scan_params(
                symbol=settings.symbol,
                exchange=settings.exchange,
                adjust=settings.adjust,
            ),
        )

    def _stock(self, context: dict[str, Any], settings):
        from ai_trade_system.stock_catalog import StockInfo

        return StockInfo(str(settings.symbol), str(context.get("name") or settings.symbol), str(settings.exchange))

    def _compact_data_file(self, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "code": result.get("code"),
            "exchange": result.get("exchange"),
            "status": result.get("status"),
            "latest_path": result.get("latest_path"),
            "latest_rows": result.get("latest_rows"),
            "latest_start": result.get("latest_start"),
            "latest_end": result.get("latest_end"),
            "timeframe": result.get("timeframe", "daily"),
            "message": result.get("message"),
        }

    def _data_status_label(self, status: str) -> str:
        return {"updated": "已更新", "skipped": "已跳过", "failed": "失败"}.get(status, status)

    def _compact_weekly_candidate(self, candidate: Any) -> dict[str, Any]:
        return self._compact_candidate_dict(candidate)

    def _compact_candidate_dict(self, candidate: Any) -> dict[str, Any]:
        if hasattr(candidate, "as_dict"):
            payload = candidate.as_dict()
        elif isinstance(candidate, dict):
            payload = dict(candidate)
        else:
            payload = {}
        compact = {
            "rank": payload.get("rank"),
            "code": payload.get("code") or payload.get("symbol"),
            "name": payload.get("name"),
            "exchange": payload.get("exchange"),
            "composite_score": payload.get("composite_score"),
            "chan_score": payload.get("chan_score"),
            "volume_score": payload.get("volume_score"),
            "latest_day": payload.get("latest_day"),
            "latest_close": payload.get("latest_close"),
            "chan_signal_title": payload.get("chan_signal_title"),
            "chan_signal_action": payload.get("chan_signal_action"),
            "volume_entry_ready": payload.get("volume_entry_ready"),
            "reason": payload.get("reason"),
        }
        if payload.get("board") is not None:
            compact["board"] = payload.get("board")
        return compact

    def _chan_multilevel_basis(self, candidate: dict[str, Any]) -> str:
        signal = candidate.get("scan_signal_title") or candidate.get("chan_signal_title") or "未记录信号"
        reason = candidate.get("scan_reason") or candidate.get("reason") or "未记录扫描原因"
        details = [str(signal)]
        chan_score = candidate.get("chan_score")
        if isinstance(chan_score, (int, float)):
            details.append(f"Chan分 {chan_score:.2f}")
        volume_score = candidate.get("volume_score")
        if isinstance(volume_score, (int, float)):
            details.append(f"量价分 {volume_score:.2f}")
        volume_ready = candidate.get("volume_entry_ready")
        if isinstance(volume_ready, bool):
            details.append("量能确认" if volume_ready else "量能未确认")
        latest_day = candidate.get("latest_day")
        if latest_day:
            details.append(f"最新日 {latest_day}")
        details.append(f"扫描原因 {reason}")
        return "缠论多级联动：" + "；".join(details)

    def _chan_basis_line(self, candidate: dict[str, Any]) -> str:
        signal = candidate.get("scan_signal_title") or candidate.get("chan_signal_title") or "未记录信号"
        basis = candidate.get("chan_multilevel_basis") or self._chan_multilevel_basis(candidate)
        body = basis.split("：", 1)[1] if str(basis).startswith("缠论多级联动：") else str(basis)
        if body.startswith(str(signal)):
            return body
        return f"{signal}；{body}"

    def _optional_chan_basis_line(self, candidate: dict[str, Any]) -> str | None:
        has_basis = any(
            candidate.get(key) not in {None, ""}
            for key in (
                "scan_signal_title",
                "chan_signal_title",
                "chan_multilevel_basis",
                "chan_score",
                "volume_score",
                "volume_entry_ready",
            )
        )
        return self._chan_basis_line(candidate) if has_basis else None


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
