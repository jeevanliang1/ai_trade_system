import { useMemo, useState } from "react";
import { Play } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { ToolbarButton } from "../components/ToolbarButton";
import { equityOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps, PlatformState } from "./pageTypes";

type PaperMode = "single" | "portfolio";
type PaperEventFilters = {
  event: string;
  side: string;
  symbol: string;
};

const defaultPaperEventFilters: PaperEventFilters = { event: "all", side: "all", symbol: "" };

export function PaperPage({ state, actions }: PageProps) {
  const [filters, setFilters] = useState<PaperEventFilters>(defaultPaperEventFilters);
  const running = state.activePaperMode !== null;
  const config = paperRunConfig(state, "single");
  const paperEvents = state.paper?.events ?? [];
  const paperOrders = (state.paper?.orders ?? []) as Record<string, unknown>[];
  const filteredEvents = useMemo(() => filterPaperRows(paperEvents, filters), [paperEvents, filters]);
  const filteredOrders = useMemo(() => filterPaperRows(paperOrders, filters), [paperOrders, filters]);
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">纸面交易</div>
        <PaperRunStatus runningMode={state.activePaperMode} busy={state.busy} hasResult={Boolean(state.paper)} />
        <label className="field">
          <span>事件日志</span>
          <input value={state.settings.log_path} onChange={(event) => actions.setSettings({ ...state.settings, log_path: event.currentTarget.value })} />
        </label>
        <ToolbarButton disabled={state.busy || running} icon={<Play size={16} />} variant="success" onClick={() => actions.runPaper("single")}>
          {running ? "运行中..." : "运行纸面交易"}
        </ToolbarButton>
      </section>
      <section className="main-column">
        <PaperRunConfigPanel config={config} />
        <ChartPanel
          title="纸面权益"
          option={equityOption(
            state.paper
              ? {
                  bars: [],
                  metrics: {} as never,
                  trades: [],
                  drawdowns: [],
                  risk_status: { ok: true, warnings: [], enabled: true },
                  equity_curve: state.paper.equity.map((row) => ({
                    trading_day: String(row.trading_day),
                    equity: Number(row.equity),
                    cash: Number(row.cash)
                  }))
                }
              : null
          )}
          height={320}
        />
        <PaperEventFiltersPanel
          filters={filters}
          totalEvents={paperEvents.length}
          visibleEvents={filteredEvents.length}
          onChange={setFilters}
          onClear={() => setFilters(defaultPaperEventFilters)}
        />
        <PaperEventTimeline events={filteredEvents} />
        <section className="panel">
          <div className="panel-title">订单事件</div>
          <DataTable rows={filteredOrders} />
        </section>
      </section>
    </div>
  );
}

function PaperEventFiltersPanel({
  filters,
  totalEvents,
  visibleEvents,
  onChange,
  onClear
}: {
  filters: PaperEventFilters;
  totalEvents: number;
  visibleEvents: number;
  onChange: (filters: PaperEventFilters) => void;
  onClear: () => void;
}) {
  return (
    <section className="panel paper-filter-panel" aria-label="纸面事件过滤">
      <div className="panel-title between">
        <span>事件过滤</span>
        <button className="ghost-button" type="button" onClick={onClear}>
          清除过滤
        </button>
      </div>
      <div className="paper-filter-grid">
        <label className="field">
          <span>事件类型</span>
          <select value={filters.event} onChange={(event) => onChange({ ...filters, event: event.currentTarget.value })}>
            <option value="all">全部事件</option>
            <option value="service_started">service_started</option>
            <option value="service_stopped">service_stopped</option>
            <option value="order_accepted">order_accepted</option>
            <option value="order_rejected">order_rejected</option>
            <option value="equity">equity</option>
          </select>
        </label>
        <label className="field">
          <span>方向</span>
          <select value={filters.side} onChange={(event) => onChange({ ...filters, side: event.currentTarget.value })}>
            <option value="all">全部方向</option>
            <option value="buy">buy</option>
            <option value="sell">sell</option>
          </select>
        </label>
        <label className="field">
          <span>标的过滤</span>
          <input value={filters.symbol} onChange={(event) => onChange({ ...filters, symbol: event.currentTarget.value })} placeholder="代码或名称" />
        </label>
      </div>
      <p className="paper-filter-summary">{`显示 ${visibleEvents} / ${totalEvents} 条事件`}</p>
    </section>
  );
}

function PaperEventTimeline({ events }: { events: Record<string, unknown>[] }) {
  return (
    <section className="panel paper-timeline-panel" aria-label="纸面事件时间线">
      <div className="panel-title">事件时间线</div>
      {events.length ? (
        <div className="paper-timeline">
          {events.map((event, index) => {
            const view = paperEventView(event);
            return (
              <article className={`paper-event ${view.tone}`} key={`${view.eventName}-${view.tradingDay}-${index}`}>
                <span className="paper-event-badge">{view.label}</span>
                <strong>{view.title}</strong>
                <small>{view.detail}</small>
              </article>
            );
          })}
        </div>
      ) : (
        <p className="paper-timeline-empty">运行纸面交易后显示服务、订单和权益事件。</p>
      )}
    </section>
  );
}

function filterPaperRows(rows: Record<string, unknown>[], filters: PaperEventFilters) {
  const symbolQuery = filters.symbol.trim().toLowerCase();
  return rows.filter((row) => {
    if (filters.event !== "all" && String(row.event ?? "") !== filters.event) return false;
    if (filters.side !== "all" && String(row.side ?? "") !== filters.side) return false;
    if (symbolQuery) {
      const symbol = String(row.symbol ?? "").toLowerCase();
      return symbol.includes(symbolQuery);
    }
    return true;
  });
}

function paperEventView(event: Record<string, unknown>) {
  const eventName = String(event.event ?? "unknown");
  const tradingDay = String(event.trading_day ?? "-");
  const side = String(event.side ?? "-");
  const symbol = String(event.symbol ?? "-");
  const price = event.price == null ? "-" : String(event.price);
  const volume = event.volume == null ? "-" : String(event.volume);
  const reason = String(event.reason ?? "").trim();
  if (eventName === "order_accepted") {
    return {
      eventName,
      tradingDay,
      label: "已接受",
      tone: "accepted",
      title: `${tradingDay} ${side} ${symbol}`,
      detail: `价格 ${price}，数量 ${volume}${reason ? `，原因 ${reason}` : ""}`
    };
  }
  if (eventName === "order_rejected") {
    return {
      eventName,
      tradingDay,
      label: "已拒绝",
      tone: "rejected",
      title: `${tradingDay} ${side} ${symbol}`,
      detail: `价格 ${price}，数量 ${volume}${reason ? `，原因 ${reason}` : ""}`
    };
  }
  if (eventName === "equity") {
    return {
      eventName,
      tradingDay,
      label: "权益快照",
      tone: "equity",
      title: `${tradingDay} 权益 ${String(event.equity ?? "-")}`,
      detail: `现金 ${String(event.cash ?? "-")}`
    };
  }
  return {
    eventName,
    tradingDay,
    label: eventName === "service_stopped" ? "服务完成" : "服务事件",
    tone: "service",
    title: eventName === "service_stopped" ? `最终权益 ${String(event.final_equity ?? "-")}` : eventName,
    detail: "纸面交易服务状态事件"
  };
}

function PaperRunStatus({ runningMode, busy, hasResult }: { runningMode: PaperMode | null; busy: boolean; hasResult: boolean }) {
  const running = runningMode !== null;
  return (
    <div className={running ? "backtest-run-status running" : "backtest-run-status"} aria-label="纸面交易状态" role="status">
      <span>纸面交易状态</span>
      <strong>{running ? `运行中：${paperModeLabel(runningMode)}` : hasResult ? "已完成" : busy ? "等待当前任务结束" : "待运行"}</strong>
      <span>{running ? "正在重放CSV行情并写入事件日志。" : "运行后会刷新纸面权益、订单事件和底部状态。"}</span>
    </div>
  );
}

function PaperRunConfigPanel({ config }: { config: ReturnType<typeof paperRunConfig> }) {
  return (
    <section className="panel backtest-config-panel" aria-label="纸面交易运行配置">
      <div className="panel-title">运行配置</div>
      <div className="backtest-config-grid">
        <PaperConfigItem label="标的" value={config.symbol} />
        <PaperConfigItem label="区间" value={config.dateRange} />
        <PaperConfigItem label="策略/组合" value={config.strategyOrPortfolio} />
        <PaperConfigItem label="初始资金" value={config.initialCash} />
        <PaperConfigItem label="手续费" value={config.commission} />
        <PaperConfigItem label="滑点" value={config.slippage} />
        <PaperConfigItem label="日志" value={config.logPath} />
      </div>
    </section>
  );
}

function PaperConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="config-item">
      <span>{`${label} ${value}`}</span>
    </div>
  );
}

function paperRunConfig(state: PlatformState, mode: PaperMode) {
  const strategy = currentStrategy(state);
  const strategyLabel = strategy?.name ?? (state.selectedStrategyId || "-");
  return {
    symbol: `${state.settings.symbol} ${state.settings.exchange}`,
    dateRange: `${state.settings.start_date || "起始"} - ${state.settings.end_date || "最新"}`,
    strategyOrPortfolio: mode === "portfolio" ? `组合：${portfolioModeLabel(state.portfolio.mode)}` : `单策略：${strategyLabel}`,
    initialCash: String(state.settings.initial_cash),
    commission: String(state.settings.commission_rate),
    slippage: String(state.settings.slippage),
    logPath: state.settings.log_path
  };
}

function paperModeLabel(mode: PaperMode | null) {
  return mode === "portfolio" ? "组合策略" : "单策略";
}

function portfolioModeLabel(mode: PlatformState["portfolio"]["mode"]) {
  if (mode === "equal_vote") return "等权投票";
  if (mode === "first_active") return "优先级";
  return "加权投票";
}
