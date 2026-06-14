import { Play } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { ToolbarButton } from "../components/ToolbarButton";
import { equityOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps, PlatformState } from "./pageTypes";

type PaperMode = "single" | "portfolio";

export function PaperPage({ state, actions }: PageProps) {
  const running = state.activePaperMode !== null;
  const config = paperRunConfig(state, "single");
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
        <section className="panel">
          <div className="panel-title">订单事件</div>
          <DataTable rows={(state.paper?.orders ?? []) as Record<string, unknown>[]} />
        </section>
      </section>
    </div>
  );
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
