import { Play, RefreshCw, Square, RadioTower } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import { formatRequestError } from "../api/errors";
import { MetricStrip } from "../components/MetricStrip";
import { ToolbarButton } from "../components/ToolbarButton";
import type { RealtimeMonitorEvent, RealtimeMonitorStatus } from "../types";
import { currentStrategy, strategyDisplayName } from "./pageTypes";
import type { PageProps } from "./pageTypes";

type RealtimeAction = "start" | "stop" | "refresh" | null;

const EMPTY_STATUS: RealtimeMonitorStatus = {
  running: false,
  started_at: null,
  stopped_at: null,
  strategy_id: null,
  symbols: [],
  timeframe: null,
  poll_interval_seconds: null,
  event_count: 0,
  last_event_at: null,
  last_bar_time: null,
  last_error: null
};

export function RealtimePage({ state, actions }: PageProps) {
  const [status, setStatus] = useState<RealtimeMonitorStatus>(state.realtime?.status ?? EMPTY_STATUS);
  const [events, setEvents] = useState<RealtimeMonitorEvent[]>(state.realtime?.events ?? []);
  const [pollInterval, setPollInterval] = useState(30);
  const [action, setAction] = useState<RealtimeAction>(null);
  const [message, setMessage] = useState("");

  const refresh = useCallback(async () => {
    setAction("refresh");
    try {
      const [nextStatus, nextEvents] = await Promise.all([api.realtimeStatus(), api.realtimeEvents(100)]);
      setStatus(nextStatus);
      setEvents(nextEvents.events);
      setMessage("实时盯盘状态已刷新");
    } catch (error) {
      setMessage(`实时盯盘刷新失败：${formatRequestError(error)}`);
    } finally {
      setAction(null);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!status.running) return;
    const interval = window.setInterval(() => {
      void refresh();
    }, 3000);
    return () => window.clearInterval(interval);
  }, [refresh, status.running]);

  const start = async () => {
    setAction("start");
    try {
      await actions.startRealtimeMonitor(pollInterval);
      setMessage("实时盯盘已启动");
      await refresh();
    } catch (error) {
      setMessage(`启动失败：${formatRequestError(error)}`);
    } finally {
      setAction(null);
    }
  };

  const stop = async () => {
    setAction("stop");
    try {
      await actions.stopRealtimeMonitor();
      setMessage("实时盯盘已停止");
      await refresh();
    } catch (error) {
      setMessage(`停止失败：${formatRequestError(error)}`);
    } finally {
      setAction(null);
    }
  };

  const selectedStrategy = strategyDisplayName(currentStrategy(state)) ?? "-";
  const latestSignal = events.find((event) => event.event === "signal_triggered");
  const metrics = useMemo(
    () => [
      { label: "运行状态", value: status.running ? "运行中" : "已停止", tone: status.running ? "positive" as const : "neutral" as const },
      { label: "监听标的", value: status.symbols.length || 1 },
      { label: "事件数量", value: status.event_count || events.length },
      { label: "最新信号", value: latestSignal ? signalSideLabel(latestSignal.side) : "-", tone: latestSignal?.side === "buy" ? "positive" as const : latestSignal?.side === "sell" ? "negative" as const : "neutral" as const }
    ],
    [events.length, latestSignal, status.event_count, status.running, status.symbols.length]
  );

  return (
    <div className="realtime-page page-grid">
      <section className="panel side-panel realtime-controls">
        <div className="panel-title between">
          <span>实时盯盘</span>
          <RadioTower size={16} />
        </div>
        <div className="automation-status-stack">
          <StatusItem label="当前标的" value={`${state.settings.symbol} ${state.settings.exchange}`} />
          <StatusItem label="当前策略" value={selectedStrategy} />
          <StatusItem label="行情周期" value={state.settings.timeframe} />
          <StatusItem label="最新K线" value={status.last_bar_time ? formatDateTime(status.last_bar_time) : "-"} />
        </div>
        <label className="field">
          <span>轮询间隔</span>
          <input
            aria-label="轮询间隔"
            min={5}
            max={3600}
            step={5}
            type="number"
            value={pollInterval}
            onChange={(event) => setPollInterval(Number(event.currentTarget.value) || 30)}
          />
        </label>
        <div className="button-row automation-actions">
          <ToolbarButton icon={<Play size={16} />} variant="success" disabled={action !== null} onClick={start}>
            启动盯盘
          </ToolbarButton>
          <ToolbarButton icon={<Square size={16} />} disabled={action !== null} onClick={stop}>
            停止盯盘
          </ToolbarButton>
        </div>
        <div className="button-row automation-actions">
          <ToolbarButton icon={<RefreshCw size={16} />} disabled={action !== null} onClick={refresh}>
            刷新事件
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
        <section className="panel realtime-summary">
          <div className="panel-title between">
            <span>盯盘状态</span>
            <span className="caption">{status.started_at ? formatDateTime(status.started_at) : "尚未启动"}</span>
          </div>
          <div className="realtime-status-grid">
            <StatusItem label="策略 ID" value={status.strategy_id ?? "-"} />
            <StatusItem label="监听列表" value={status.symbols.length ? status.symbols.join(", ") : `${state.settings.symbol}.${state.settings.exchange}`} />
            <StatusItem label="事件时间" value={status.last_event_at ? formatDateTime(status.last_event_at) : "-"} />
            <StatusItem label="错误" value={status.last_error ?? "-"} tone={status.last_error ? "warning" : "neutral"} />
          </div>
        </section>

        <section className="panel realtime-events">
          <div className="panel-title between">
            <span>事件流</span>
            <span className="caption">{events.length} 条</span>
          </div>
          {events.length ? (
            <div className="realtime-event-list">
              {events.slice().reverse().map((event) => (
                <article className={`realtime-event event-${event.event}`} key={event.id}>
                  <header>
                    <strong>{eventLabel(event)}</strong>
                    <span>{formatDateTime(event.created_at)}</span>
                  </header>
                  <div className="realtime-event-meta">
                    <span>{event.symbol ? `${event.symbol} ${event.exchange ?? ""}` : event.symbols?.join(", ") ?? "-"}</span>
                    <span>{event.timeframe ?? status.timeframe ?? state.settings.timeframe}</span>
                    <span>{event.bar_time ? formatDateTime(event.bar_time) : "-"}</span>
                  </div>
                  <p>{eventReason(event)}</p>
                </article>
              ))}
            </div>
          ) : (
            <div className="paper-timeline-empty">暂无实时盯盘事件。</div>
          )}
        </section>
      </section>
    </div>
  );
}

function StatusItem({ label, value, tone = "neutral" }: { label: string; value: string | number; tone?: "ok" | "warning" | "neutral" }) {
  return (
    <div className={`automation-status-item ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function eventLabel(event: RealtimeMonitorEvent): string {
  if (event.event === "signal_triggered") return `${signalSideLabel(event.side)} 信号`;
  if (event.event === "bar_updated") return event.warmup ? "最新K线预热" : "最新K线";
  if (event.event === "monitor_heartbeat") return "盯盘心跳";
  if (event.event === "monitor_error") return "盯盘错误";
  if (event.event === "monitor_started") return "盯盘启动";
  if (event.event === "monitor_stopped") return "盯盘停止";
  if (event.event === "data_empty") return "暂无行情";
  return event.event;
}

function eventReason(event: RealtimeMonitorEvent): string {
  if (event.event === "signal_triggered") return event.reason || `${event.side} @ ${event.price ?? "-"}`;
  if (event.event === "bar_updated") return `收盘 ${formatNumber(event.close_price)}，成交量 ${formatNumber(event.volume)}`;
  if (event.event === "monitor_heartbeat") return `更新K线 ${event.updated_bars ?? 0}，触发信号 ${event.signals ?? 0}`;
  if (event.event === "monitor_error") return event.message ?? "盯盘轮询失败";
  if (event.event === "data_empty") return "行情源本次未返回可用K线";
  return event.message ?? "-";
}

function signalSideLabel(side: string | undefined): string {
  if (side === "buy") return "买入";
  if (side === "sell") return "卖出";
  return "-";
}

function formatDateTime(value: string): string {
  return value.replace("T", " ").replace("+08:00", "").replace("Z", "");
}

function formatNumber(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return "-";
  return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(2);
}
