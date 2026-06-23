from __future__ import annotations

import threading
from datetime import date, datetime
from typing import Any, Callable, Iterable

from ai_trade_system.agent.openclaw import OpenClawConnector
from ai_trade_system.automation.analysis import analyze_weekly_radar_result
from ai_trade_system.automation.models import (
    AutomationConfig,
    AutomationRunRecord,
    AutomationStatus,
    DailyJudgment,
    RadarCandidateScore,
    WeeklyAnalysisResult,
    WeeklyRadarResult,
)
from ai_trade_system.automation.radar import scan_star_radar_candidates, scan_weekly_radar_candidates
from ai_trade_system.automation.store import AutomationStore
from ai_trade_system.data_manager import update_stock_data
from ai_trade_system.stock_catalog import StockInfo, load_stock_catalog
from ai_trade_system.watchlist import load_watchlist


class BusyAutomationError(RuntimeError):
    pass


class AutomationService:
    def __init__(
        self,
        *,
        store: AutomationStore | None = None,
        load_catalog: Callable[[], list[StockInfo]] = load_stock_catalog,
        load_watchlist: Callable[[], list[StockInfo]] = load_watchlist,
        update_stock_data: Callable = update_stock_data,
        scan_star_radar: Callable = scan_star_radar_candidates,
        scan_weekly_radar: Callable | None = None,
        analyze_weekly_result: Callable | None = None,
        notify_weekly_analysis: Callable | None = None,
    ):
        self.store = store or AutomationStore()
        self.load_catalog = load_catalog
        self.load_watchlist = load_watchlist
        self.update_stock_data = update_stock_data
        self.scan_star_radar = scan_star_radar
        if scan_weekly_radar is None and scan_star_radar is scan_star_radar_candidates:
            scan_weekly_radar = scan_weekly_radar_candidates
        self.scan_weekly_radar = scan_weekly_radar
        self.analyze_weekly_result = analyze_weekly_result or _default_weekly_analysis
        self.notify_weekly_analysis = notify_weekly_analysis or _default_weekly_analysis_notification
        self._lock = threading.Lock()

    def run_weekly_full_maintenance(self, now: datetime | None = None) -> WeeklyRadarResult:
        current = now or datetime.now()
        if not self._lock.acquire(blocking=False):
            raise BusyAutomationError("automation task is already running")
        started_at = current.replace(microsecond=0).isoformat()
        try:
            config = self.store.load_config()
            start_date, end_date = _two_year_date_range(current.date())
            catalog = self.load_catalog()
            star_stocks = [stock for stock in catalog if stock.exchange == "SSE" and stock.code.startswith("688")]
            chinext_stocks = [
                stock
                for stock in catalog
                if stock.exchange == "SZSE" and stock.code.startswith(("300", "301"))
            ]
            update_stocks = _dedupe_stocks([*star_stocks, *chinext_stocks, *self.load_watchlist()])
            for stock in update_stocks:
                self.update_stock_data(
                    stock,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=config.adjust,
                    if_stale=True,
                )
            if self.scan_weekly_radar is not None:
                result = self.scan_weekly_radar(
                    {"star": star_stocks, "chinext": chinext_stocks},
                    config,
                    generated_at=started_at,
                )
            else:
                result = self.scan_star_radar(star_stocks, config, generated_at=started_at)
            self.store.save_weekly_result(result)
            analysis = None
            if config.weekly_analysis_enabled:
                analysis = self.analyze_weekly_result(result, config=config, generated_at=started_at)
                self.store.save_weekly_analysis(analysis)
                if config.weekly_delivery_enabled:
                    delivery = self.notify_weekly_analysis(analysis, config=config)
                    analysis.delivery_status = str(delivery.get("status", "unknown"))
                    analysis.delivery_summary = str(delivery.get("summary", ""))
                    self.store.save_weekly_analysis(analysis)
            state = self.store.load_state()
            final_status = _weekly_task_status(result, analysis)
            message = _weekly_task_message(result, analysis)
            state.update(
                {
                    "last_weekly_success_date": current.date().isoformat() if final_status in {"success", "partial"} else state.get("last_weekly_success_date"),
                    "last_weekly_analysis_run": analysis.run_id if analysis else state.get("last_weekly_analysis_run"),
                    "last_weekly_run": _run_payload("weekly", final_status, started_at, datetime.now().replace(microsecond=0).isoformat(), message),
                }
            )
            self.store.save_state(state)
            self.store.append_run(AutomationRunRecord.from_dict(state["last_weekly_run"]))
            return result
        except Exception as exc:
            finished_at = datetime.now().replace(microsecond=0).isoformat()
            run = _run_payload("weekly", "failed", started_at, finished_at, str(exc))
            self.store.save_state({**self.store.load_state(), "last_weekly_run": run})
            self.store.append_run(AutomationRunRecord.from_dict(run))
            raise
        finally:
            self._lock.release()

    def run_daily_top10_judgment(self, now: datetime | None = None) -> list[DailyJudgment]:
        current = now or datetime.now()
        if not self._lock.acquire(blocking=False):
            raise BusyAutomationError("automation task is already running")
        started_at = current.replace(microsecond=0).isoformat()
        try:
            weekly = self.store.load_weekly_result()
            if weekly is None:
                judgments: list[DailyJudgment] = []
            else:
                config = self.store.load_config()
                start_date, end_date = _two_year_date_range(current.date())
                stocks = [StockInfo(item.code, item.name, item.exchange) for item in weekly.top]
                for stock in stocks:
                    self.update_stock_data(stock, start_date=start_date, end_date=end_date, adjust=config.adjust, if_stale=True)
                current_scores = self.scan_star_radar(stocks, config, generated_at=started_at)
                score_by_code = {item.code: item for item in current_scores.top}
                judgments = [_judgment_for(item, score_by_code.get(item.code)) for item in weekly.top]
            day = current.date().isoformat()
            self.store.save_daily_judgments(day, judgments)
            finished_at = datetime.now().replace(microsecond=0).isoformat()
            run = _run_payload("daily", "success", started_at, finished_at, f"{len(judgments)} judgments")
            state = self.store.load_state()
            state.update({"last_daily_success_date": day, "last_daily_run": run})
            self.store.save_state(state)
            self.store.append_run(AutomationRunRecord.from_dict(run))
            return judgments
        except Exception as exc:
            finished_at = datetime.now().replace(microsecond=0).isoformat()
            run = _run_payload("daily", "failed", started_at, finished_at, str(exc))
            self.store.save_state({**self.store.load_state(), "last_daily_run": run})
            self.store.append_run(AutomationRunRecord.from_dict(run))
            raise
        finally:
            self._lock.release()

    def status(self, now: datetime | None = None) -> AutomationStatus:
        state = self.store.load_state()
        weekly = self.store.load_weekly_result()
        analysis = self.store.load_latest_weekly_analysis()
        current = now or datetime.now()
        recent_runs = _recent_runs(self.store.load_runs())
        return AutomationStatus(
            config=self.store.load_config(),
            running=self._lock.locked(),
            last_weekly_run=state.get("last_weekly_run"),
            last_daily_run=state.get("last_daily_run"),
            weekly_top10_count=len(weekly.top) if weekly else 0,
            latest_daily_judgment_count=len(self.store.load_daily_judgments(current.date().isoformat())),
            weekly_analysis_status=analysis.status if analysis else None,
            weekly_analysis_run_id=analysis.run_id if analysis else None,
            weekly_delivery_status=analysis.delivery_status if analysis else None,
            recent_runs=[run.as_dict() for run in recent_runs],
            diagnostics=_automation_diagnostics(self._lock.locked(), weekly, analysis, recent_runs),
        )

    def update_config(self, patch: dict[str, Any]) -> AutomationConfig:
        current = self.store.load_config().as_dict()
        for key, value in patch.items():
            if value is not None and key in current:
                current[key] = value
        config = AutomationConfig.from_dict(current)
        self.store.save_config(config)
        return config


def _dedupe_stocks(stocks: Iterable[StockInfo]) -> list[StockInfo]:
    seen: set[tuple[str, str]] = set()
    deduped: list[StockInfo] = []
    for stock in stocks:
        key = (stock.exchange, stock.code)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(stock)
    return deduped


def _two_year_date_range(today: date) -> tuple[str, str]:
    try:
        start = today.replace(year=today.year - 2)
    except ValueError:
        start = today.replace(year=today.year - 2, day=28)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


def _recent_runs(runs: list[AutomationRunRecord], limit: int = 8) -> list[AutomationRunRecord]:
    return list(reversed(runs[-limit:]))


def _automation_diagnostics(
    running: bool,
    weekly: WeeklyRadarResult | None,
    analysis: WeeklyAnalysisResult | None,
    recent_runs: list[AutomationRunRecord],
) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    if running:
        diagnostics.append(
            {
                "code": "TASK_RUNNING",
                "severity": "info",
                "task": "automation",
                "message": "自动任务正在运行，等待当前任务结束后再手动触发。",
                "suggestion": "稍后刷新状态。",
                "run_id": None,
                "created_at": None,
            }
        )
    for run in recent_runs:
        if run.status == "failed":
            diagnostics.append(
                {
                    "code": "RUN_FAILED",
                    "severity": "high",
                    "task": run.task,
                    "message": f"{_task_label(run.task)}失败：{run.message}",
                    "suggestion": _failure_suggestion(run.task),
                    "run_id": run.run_id,
                    "created_at": run.finished_at or run.started_at,
                }
            )
    if weekly is None:
        diagnostics.append(
            {
                "code": "NO_WEEKLY_RESULT",
                "severity": "info",
                "task": "weekly",
                "message": "尚未生成周榜结果，自动任务页面无法展示 Top10 候选。",
                "suggestion": "执行一次周扫描或等待下一次周任务。",
                "run_id": None,
                "created_at": None,
            }
        )
    elif weekly.missing:
        diagnostics.append(
            {
                "code": "MISSING_DATA",
                "severity": "medium",
                "task": "weekly",
                "message": f"最近周扫描有 {weekly.missing} 个候选缺少可用本地行情数据。",
                "suggestion": "检查行情源和托管 CSV 后重跑周扫描。",
                "run_id": weekly.run_id,
                "created_at": weekly.generated_at,
            }
        )
    if weekly is not None and analysis is None:
        diagnostics.append(
            {
                "code": "NO_WEEKLY_ANALYSIS",
                "severity": "medium",
                "task": "weekly",
                "message": "最近周扫描尚未生成 AI 深度分析缓存。",
                "suggestion": "重跑周六完整任务，或检查 OpenClaw/通知配置。",
                "run_id": weekly.run_id,
                "created_at": weekly.generated_at,
            }
        )
    elif analysis is not None and analysis.delivery_status not in {None, "ok"}:
        diagnostics.append(
            {
                "code": "WEEKLY_DELIVERY_INCOMPLETE",
                "severity": "medium",
                "task": "weekly",
                "message": f"最近周度 AI 分析投递未完成：{analysis.delivery_status}。",
                "suggestion": "检查 AI_TRADE_OPENCLAW_NOTIFY_COMMAND、微信或飞书 reply_channel 配置后重跑周任务。",
                "run_id": analysis.run_id,
                "created_at": analysis.generated_at,
            }
        )
    return diagnostics


def _default_weekly_analysis(
    weekly: WeeklyRadarResult,
    *,
    config: AutomationConfig,
    generated_at: str | None = None,
) -> WeeklyAnalysisResult:
    return analyze_weekly_radar_result(weekly, config=config, generated_at=generated_at)


def _default_weekly_analysis_notification(analysis: WeeklyAnalysisResult, *, config: AutomationConfig) -> dict[str, Any]:
    connector = OpenClawConnector()
    reply_channel = {
        "weixin": "openclaw-weixin",
        "wechat": "openclaw-weixin",
        "feishu": "openclaw-feishu",
        "lark": "openclaw-feishu",
    }.get(config.weekly_delivery_channel, config.weekly_delivery_channel)
    return connector.notify_message(
        analysis.message,
        {
            "source": config.weekly_delivery_channel,
            "reply_channel": reply_channel,
            "source_workflow": "weekly_scan_deep_analysis",
            "weekly_analysis_run_id": analysis.run_id,
            "weekly_run_id": analysis.weekly_run_id,
        },
    )


def _weekly_task_status(result: WeeklyRadarResult, analysis: WeeklyAnalysisResult | None) -> str:
    if result.status == "failed":
        return "failed"
    if analysis is None:
        return result.status
    if analysis.status == "success" and analysis.delivery_status in {"ok", None}:
        return result.status
    if analysis.status in {"partial", "not_configured"} or analysis.delivery_status not in {"ok", "not_configured", None}:
        return "partial"
    return "failed"


def _weekly_task_message(result: WeeklyRadarResult, analysis: WeeklyAnalysisResult | None) -> str:
    if analysis is None:
        return result.status
    return (
        f"scan={result.status} scanned={result.scanned} missing={result.missing}; "
        f"analysis={analysis.status} sections={len(analysis.sections)}; "
        f"delivery={analysis.delivery_status or 'not_attempted'}"
    )


def _task_label(task: str) -> str:
    return {"weekly": "周扫描", "daily": "日判断"}.get(task, task)


def _failure_suggestion(task: str) -> str:
    if task == "weekly":
        return "检查股票目录、行情源和本地数据维护后重跑周扫描。"
    if task == "daily":
        return "检查行情源网络后重跑日判断。"
    return "查看 logs/automation/runs.jsonl 中的错误信息后重试。"


def _judgment_for(baseline: RadarCandidateScore, current: RadarCandidateScore | None) -> DailyJudgment:
    if current is None:
        return DailyJudgment(
            code=baseline.code,
            name=baseline.name,
            exchange=baseline.exchange,
            judgment="missing_data",
            reason="未找到可用本地数据，无法刷新每日判断",
            current_score=0.0,
            baseline_score=baseline.composite_score,
            latest_day=None,
            latest_close=None,
            chan_signal_title=None,
            volume_entry_ready=False,
        )
    judgment = _judgment_label(baseline, current)
    reason = _judgment_reason(judgment, current)
    return DailyJudgment(
        code=current.code,
        name=current.name,
        exchange=current.exchange,
        judgment=judgment,
        reason=reason,
        current_score=current.composite_score,
        baseline_score=baseline.composite_score,
        latest_day=current.latest_day,
        latest_close=current.latest_close,
        chan_signal_title=current.chan_signal_title,
        volume_entry_ready=current.volume_entry_ready,
    )


def _judgment_label(baseline: RadarCandidateScore, current: RadarCandidateScore) -> str:
    title = current.chan_signal_title or ""
    if current.chan_signal_action == "sell" or current.composite_score <= baseline.composite_score * 0.7:
        return "risk_watch"
    if ("三买" in title or "确认" in title) and current.volume_entry_ready:
        return "strong_follow"
    if current.chan_signal_action == "buy":
        return "starter_follow" if current.volume_entry_ready else "watch_only"
    return "watch_only"


def _judgment_reason(judgment: str, current: RadarCandidateScore) -> str:
    if judgment == "strong_follow":
        return f"{current.chan_signal_title or '结构买点'}叠加量价确认，保持强跟踪"
    if judgment == "starter_follow":
        return f"{current.chan_signal_title or '结构买点'}出现，量价支持，适合建仓观察"
    if judgment == "risk_watch":
        return f"{current.chan_signal_title or '结构转弱'}，综合分回落到 {current.composite_score:.2f}"
    return f"{current.chan_signal_title or '结构偏多'}仍在，量能未确认"


def _run_payload(task: str, status: str, started_at: str, finished_at: str, message: str) -> dict[str, Any]:
    return {
        "run_id": f"{task}-{started_at}",
        "task": task,
        "status": status,
        "started_at": started_at,
        "finished_at": finished_at,
        "message": message,
    }
