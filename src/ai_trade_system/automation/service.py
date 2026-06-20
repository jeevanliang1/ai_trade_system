from __future__ import annotations

import threading
from datetime import date, datetime
from typing import Any, Callable, Iterable

from ai_trade_system.automation.models import (
    AutomationConfig,
    AutomationRunRecord,
    AutomationStatus,
    DailyJudgment,
    RadarCandidateScore,
    WeeklyRadarResult,
)
from ai_trade_system.automation.radar import scan_star_radar_candidates
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
    ):
        self.store = store or AutomationStore()
        self.load_catalog = load_catalog
        self.load_watchlist = load_watchlist
        self.update_stock_data = update_stock_data
        self.scan_star_radar = scan_star_radar
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
            update_stocks = _dedupe_stocks([*star_stocks, *self.load_watchlist()])
            for stock in update_stocks:
                self.update_stock_data(
                    stock,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=config.adjust,
                    if_stale=True,
                )
            result = self.scan_star_radar(star_stocks, config, generated_at=started_at)
            self.store.save_weekly_result(result)
            state = self.store.load_state()
            state.update(
                {
                    "last_weekly_success_date": current.date().isoformat() if result.status in {"success", "partial"} else state.get("last_weekly_success_date"),
                    "last_weekly_run": _run_payload("weekly", result.status, started_at, datetime.now().replace(microsecond=0).isoformat(), result.status),
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
        current = now or datetime.now()
        return AutomationStatus(
            config=self.store.load_config(),
            running=self._lock.locked(),
            last_weekly_run=state.get("last_weekly_run"),
            last_daily_run=state.get("last_daily_run"),
            weekly_top10_count=len(weekly.top) if weekly else 0,
            latest_daily_judgment_count=len(self.store.load_daily_judgments(current.date().isoformat())),
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
