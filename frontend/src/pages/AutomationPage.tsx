import { AlertTriangle, Play, RefreshCw, Save, Settings, TimerReset } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { MetricStrip } from "../components/MetricStrip";
import { ToolbarButton } from "../components/ToolbarButton";
import type { AutomationConfig, AutomationStatus, DailyJudgmentResponse, WeeklyRadarResult } from "../types";
import type { PageProps } from "./pageTypes";

type AutomationAction = "save" | "weekly" | "daily" | "refresh" | null;

export function AutomationPage(_props: PageProps) {
  const [status, setStatus] = useState<AutomationStatus | null>(null);
  const [weekly, setWeekly] = useState<WeeklyRadarResult | null>(null);
  const [daily, setDaily] = useState<DailyJudgmentResponse | null>(null);
  const [draft, setDraft] = useState<AutomationConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [action, setAction] = useState<AutomationAction>(null);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    setAction("refresh");
    try {
      const [nextStatus, nextWeekly, nextDaily] = await Promise.all([api.automationStatus(), api.automationTop10(), api.automationJudgments()]);
      setStatus(nextStatus);
      setWeekly(nextWeekly);
      setDaily(nextDaily);
      setDraft(nextStatus.config);
      setMessage("自动任务状态已刷新");
    } catch (error) {
      setMessage(`自动任务加载失败：${formatRequestError(error)}`);
    } finally {
      setLoading(false);
      setAction(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const metrics = useMemo(
    () => [
      { label: "周榜数量", value: status?.weekly_top10_count ?? weekly?.top.length ?? 0 },
      { label: "日判断", value: status?.latest_daily_judgment_count ?? daily?.judgments.length ?? 0 },
      { label: "扫描覆盖", value: `${weekly?.scanned ?? 0}/${weekly?.total_candidates ?? 0}` },
      { label: "缺数据", value: weekly?.missing ?? 0, tone: weekly?.missing ? "negative" as const : "neutral" as const }
    ],
    [daily?.judgments.length, status?.latest_daily_judgment_count, status?.weekly_top10_count, weekly?.missing, weekly?.scanned, weekly?.top.length, weekly?.total_candidates]
  );

  const saveConfig = async () => {
    if (!draft) return;
    setAction("save");
    try {
      const config = await api.updateAutomationConfig({
        enabled: draft.enabled,
        top_n: draft.top_n,
        chan_weight: draft.chan_weight,
        volume_weight: draft.volume_weight
      });
      setDraft(config);
      setStatus((current) => (current ? { ...current, config } : current));
      setMessage("自动任务配置已保存");
    } catch (error) {
      setMessage(`保存失败：${formatRequestError(error)}`);
    } finally {
      setAction(null);
    }
  };

  const runWeekly = async () => {
    setAction("weekly");
    try {
      const result = await api.runAutomationWeekly();
      const nextStatus = await api.automationStatus();
      setWeekly(result);
      setStatus(nextStatus);
      setDraft(nextStatus.config);
      setMessage("周扫描已完成");
    } catch (error) {
      setMessage(`周扫描失败：${formatRequestError(error)}`);
    } finally {
      setAction(null);
    }
  };

  const runDaily = async () => {
    setAction("daily");
    try {
      const result = await api.runAutomationDaily();
      const nextStatus = await api.automationStatus();
      setDaily(result);
      setStatus(nextStatus);
      setDraft(nextStatus.config);
      setMessage("日判断已完成");
    } catch (error) {
      setMessage(`日判断失败：${formatRequestError(error)}`);
    } finally {
      setAction(null);
    }
  };

  const disabled = loading || action !== null || !draft;

  return (
    <div className="automation-page page-grid">
      <section className="panel side-panel automation-controls">
        <div className="panel-title between">
          <span>自动任务管理</span>
          <TimerReset size={16} />
        </div>
        <div className="automation-status-stack">
          <StatusItem label="运行状态" value={status?.running ? "运行中" : draft?.enabled ? "已启用" : "已停用"} tone={status?.running ? "warning" : draft?.enabled ? "ok" : "neutral"} />
          <StatusItem label="周任务" value={draft ? `${weekdayLabel(draft.weekly_weekday)} ${draft.weekly_time}` : "-"} />
          <StatusItem label="日任务" value={draft?.daily_time ?? "-"} />
        </div>
        {draft && (
          <>
            <label className="compact-switch">
              <input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.currentTarget.checked })} />
              启用自动维护
            </label>
            <label className="field">
              <span>Top N 数量</span>
              <input
                aria-label="Top N 数量"
                min={1}
                max={50}
                type="number"
                value={draft.top_n}
                onChange={(event) => setDraft({ ...draft, top_n: Number(event.currentTarget.value) })}
              />
            </label>
            <label className="field">
              <span>缠论权重</span>
              <input
                aria-label="缠论权重"
                min={0}
                max={5}
                step={0.05}
                type="number"
                value={draft.chan_weight}
                onChange={(event) => setDraft({ ...draft, chan_weight: Number(event.currentTarget.value) })}
              />
            </label>
            <label className="field">
              <span>量价权重</span>
              <input
                aria-label="量价权重"
                min={0}
                max={5}
                step={0.05}
                type="number"
                value={draft.volume_weight}
                onChange={(event) => setDraft({ ...draft, volume_weight: Number(event.currentTarget.value) })}
              />
            </label>
          </>
        )}
        <div className="button-row automation-actions">
          <ToolbarButton icon={<Save size={16} />} variant="primary" disabled={disabled || action === "save"} onClick={saveConfig}>
            保存配置
          </ToolbarButton>
          <ToolbarButton icon={<RefreshCw size={16} />} disabled={action !== null} onClick={refresh}>
            刷新状态
          </ToolbarButton>
        </div>
        <div className="button-row automation-actions">
          <ToolbarButton icon={<Play size={16} />} disabled={disabled} onClick={runWeekly}>
            立即跑周扫描
          </ToolbarButton>
          <ToolbarButton icon={<Play size={16} />} disabled={disabled} onClick={runDaily}>
            立即跑日判断
          </ToolbarButton>
        </div>
        {message && (
          <div className={message.includes("失败") ? "inline-alert" : "inline-success"} role={message.includes("失败") ? "alert" : "status"}>
            {message}
          </div>
        )}
      </section>

      <section className="main-column">
        <MetricStrip metrics={metrics} />
        <section className="panel automation-weekly">
          <div className="panel-title between">
            <span>周六全量雷达 Top10</span>
            <span className="caption">{weekly?.generated_at ? formatDateTime(weekly.generated_at) : "尚未生成"}</span>
          </div>
          {weekly?.top.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>股票</th>
                    <th>综合分</th>
                    <th>缠论</th>
                    <th>量价</th>
                    <th>最新</th>
                    <th>原因</th>
                  </tr>
                </thead>
                <tbody>
                  {weekly.top.map((candidate) => (
                    <tr key={`${candidate.exchange}:${candidate.code}`}>
                      <td>{candidate.rank}</td>
                      <td>
                        <strong>{candidate.name}</strong>
                        <small>{candidate.code} {candidate.exchange}</small>
                      </td>
                      <td>{candidate.composite_score.toFixed(1)}</td>
                      <td>{candidate.chan_score.toFixed(1)}</td>
                      <td>{candidate.volume_score.toFixed(1)}</td>
                      <td>{candidate.latest_close?.toFixed(2) ?? "-"}</td>
                      <td>{candidate.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState text={loading ? "正在加载周榜..." : "尚未生成周榜，先执行周扫描或等待周六自动任务。"} />
          )}
        </section>

        <section className="panel automation-daily">
          <div className="panel-title between">
            <span>下一周每日判断</span>
            <span className="caption">{daily?.date ?? "-"}</span>
          </div>
          {daily?.judgments.length ? (
            <div className="automation-judgment-grid">
              {daily.judgments.map((judgment) => (
                <article className={`automation-judgment ${judgmentTone(judgment.judgment)}`} key={`${judgment.exchange}:${judgment.code}`}>
                  <header>
                    <div>
                      <strong>{judgment.name}</strong>
                      <span>{judgment.code} {judgment.exchange}</span>
                    </div>
                    <b>{judgmentLabel(judgment.judgment)}</b>
                  </header>
                  <div className="automation-score-line">
                    <span>当前 {judgment.current_score.toFixed(1)}</span>
                    <span>基准 {judgment.baseline_score.toFixed(1)}</span>
                    <span>{judgment.latest_close?.toFixed(2) ?? "-"}</span>
                  </div>
                  <p>{judgment.reason}</p>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState text={loading ? "正在加载每日判断..." : "尚未生成每日判断，先执行日判断或等待每日自动任务。"} />
          )}
        </section>
      </section>
    </div>
  );
}

function StatusItem({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "ok" | "warning" }) {
  return (
    <div className={`automation-status-item ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty-table">
      <AlertTriangle size={16} />
      <span>{text}</span>
    </div>
  );
}

function weekdayLabel(day: number): string {
  return ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][day] ?? `周${day}`;
}

function formatDateTime(value: string): string {
  return value.replace("T", " ").replace("+08:00", "");
}

function judgmentLabel(judgment: string): string {
  if (judgment === "aggressive_add") return "激进加仓";
  if (judgment === "clear_exit") return "清仓";
  if (judgment === "build_position") return "建仓";
  if (judgment === "reduce_position") return "减仓";
  return "观察";
}

function judgmentTone(judgment: string): string {
  if (judgment === "aggressive_add" || judgment === "build_position") return "positive";
  if (judgment === "clear_exit" || judgment === "reduce_position") return "negative";
  return "neutral";
}
