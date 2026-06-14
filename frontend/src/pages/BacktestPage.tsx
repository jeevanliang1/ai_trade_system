import { Download, Play } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { SegmentedControl } from "../components/SegmentedControl";
import { ToolbarButton } from "../components/ToolbarButton";
import type { BacktestResponse, PortfolioRequest, PlatformSettings, SignalRow, StrategySpec } from "../types";
import { drawdownOption, equityOption, priceOption } from "./chartOptions";
import type { PageProps, PlatformState } from "./pageTypes";
import { useState } from "react";

type BacktestMode = "single" | "portfolio";

type BacktestRunConfig = {
  symbol: string;
  dateRange: string;
  modeLabel: string;
  strategyOrPortfolio: string;
  initialCash: string;
  commission: string;
  slippage: string;
};

type CsvColumn<T extends object> = Extract<keyof T, string>;

type BacktestReadinessIssue = {
  key: string;
  title: string;
  detail: string;
};

const TRADE_EXPORT_COLUMNS = [
  "trading_day",
  "side",
  "symbol",
  "price",
  "volume",
  "commission"
] satisfies CsvColumn<BacktestResponse["trades"][number]>[];

const EQUITY_EXPORT_COLUMNS = [
  "trading_day",
  "equity",
  "cash",
  "close_price"
] satisfies CsvColumn<BacktestResponse["equity_curve"][number]>[];

export function BacktestPage({ state, actions }: PageProps) {
  const [mode, setMode] = useState<BacktestMode>("single");
  const backtestRunning = state.activeBacktestMode !== null;
  const runConfig = backtestRunConfig(state.settings, state.strategies, state.selectedStrategyId, state.portfolio, mode);
  const readinessIssues = backtestReadinessIssues(state, mode);
  const canRunBacktest = !state.busy && readinessIssues.length === 0;
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">回测设置</div>
        <SegmentedControl
          value={mode}
          onChange={setMode}
          disabled={state.busy}
          options={[
            { label: "单策略", value: "single" },
            { label: "组合策略", value: "portfolio" }
          ]}
        />
        <BacktestRunStatus busy={state.busy} message={state.message} runningMode={state.activeBacktestMode} selectedMode={mode} />
        <BacktestReadinessPanel issues={readinessIssues} />
        <label className="field">
          <span>初始资金</span>
          <input
            type="number"
            value={state.settings.initial_cash}
            onChange={(event) => actions.setSettings({ ...state.settings, initial_cash: Number(event.currentTarget.value) })}
          />
        </label>
        <label className="field">
          <span>手续费率</span>
          <input
            type="number"
            step="0.0001"
            value={state.settings.commission_rate}
            onChange={(event) => actions.setSettings({ ...state.settings, commission_rate: Number(event.currentTarget.value) })}
          />
        </label>
        <label className="field">
          <span>单笔最大金额</span>
          <input
            type="number"
            value={state.settings.max_order_cash}
            onChange={(event) => actions.setSettings({ ...state.settings, max_order_cash: Number(event.currentTarget.value) })}
          />
        </label>
        <ToolbarButton disabled={!canRunBacktest} icon={<Play size={16} />} variant="success" onClick={() => actions.runBacktest(mode)}>
          {backtestRunning ? "运行中..." : "运行回测"}
        </ToolbarButton>
      </section>
      <BacktestResultPanel result={state.backtest} config={runConfig} readinessIssues={readinessIssues} />
    </div>
  );
}

function BacktestRunStatus({
  busy,
  message,
  runningMode,
  selectedMode
}: {
  busy: boolean;
  message: string;
  runningMode: BacktestMode | null;
  selectedMode: BacktestMode;
}) {
  const running = runningMode !== null;
  const mode = runningMode ?? selectedMode;
  return (
    <div className={running ? "backtest-run-status running" : "backtest-run-status"} aria-label="回测运行状态" role="status">
      <strong>{running ? `${backtestModeLabel(mode)}回测运行中` : busy ? "等待当前任务结束" : "等待运行"}</strong>
      <span>{running ? `当前运行：${backtestModeLabel(mode)}` : `当前模式：${backtestModeLabel(mode)}`}</span>
      <small>{running ? message : "运行后会刷新资金曲线、回撤曲线、买卖点和交易明细。"}</small>
    </div>
  );
}

function BacktestReadinessPanel({ issues }: { issues: BacktestReadinessIssue[] }) {
  const blocked = issues.length > 0;
  return (
    <div className={blocked ? "backtest-readiness-panel blocked" : "backtest-readiness-panel ready"} aria-label="回测准备状态">
      <strong>{blocked ? "需要处理" : "准备完成"}</strong>
      {blocked ? (
        <ul>
          {issues.map((issue) => (
            <li key={issue.key}>
              <span>{issue.title}</span>
              <small>{issue.detail}</small>
            </li>
          ))}
        </ul>
      ) : (
        <small>行情、策略和当前模式设置已满足回测条件。</small>
      )}
    </div>
  );
}

export function BacktestResultPanel({
  result,
  config,
  readinessIssues = []
}: {
  result: BacktestResponse | null;
  config?: BacktestRunConfig;
  readinessIssues?: BacktestReadinessIssue[];
}) {
  return (
    <section className="main-column">
      <MetricStrip
        metrics={[
          { label: "最终权益", value: result ? result.metrics.final_equity.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "-" },
          { label: "累计收益", value: result ? `${result.metrics.total_return_pct.toFixed(2)}%` : "-" },
          { label: "最大回撤", value: result ? `${result.metrics.max_drawdown_pct.toFixed(2)}%` : "-" },
          { label: "交易次数", value: result?.metrics.trade_count ?? "-" },
          { label: "胜率", value: result?.metrics.win_rate_pct == null ? "-" : `${result.metrics.win_rate_pct.toFixed(2)}%` }
        ]}
      />
      {config ? <BacktestRunConfigPanel config={config} /> : null}
      <BacktestExportPanel result={result} />
      {!result ? <BacktestResultStatePanel issues={readinessIssues} /> : null}
      <ChartPanel title="资金曲线" option={equityOption(result)} height={260} />
      <ChartPanel title="回撤曲线" option={drawdownOption(result)} height={220} />
      <ChartPanel title="买卖点" option={priceOption(result?.bars ?? [], backtestTradeSignals(result?.trades ?? []))} height={320} />
      <section className="panel">
        <div className="panel-title">交易明细</div>
        <DataTable rows={(result?.trades ?? []) as unknown as Record<string, unknown>[]} />
      </section>
    </section>
  );
}

function BacktestResultStatePanel({ issues }: { issues: BacktestReadinessIssue[] }) {
  const blocked = issues.length > 0;
  return (
    <section className={blocked ? "panel backtest-empty-state blocked" : "panel backtest-empty-state"} aria-label="回测结果状态">
      <div className="panel-title">{blocked ? "无法运行回测" : "等待回测结果"}</div>
      <p>{blocked ? "当前配置还不能启动回测，请先处理下面的阻塞项。" : "运行回测后，这里会显示资金曲线、回撤、买卖点和交易明细。"}</p>
      {blocked ? (
        <ul>
          {issues.map((issue) => (
            <li key={issue.key}>
              <strong>{issue.title}</strong>
              <span>{issue.detail}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function backtestTradeSignals(trades: BacktestResponse["trades"]): SignalRow[] {
  return trades.flatMap((trade) => {
    const action: SignalRow["action"] | null = trade.side === "buy" ? "buy" : trade.side === "sell" ? "sell" : null;
    if (!action) return [];
    return [
      {
        trading_day: trade.trading_day,
        action,
        symbol: trade.symbol,
        price: trade.price,
        volume: trade.volume,
        reason: "回测成交"
      }
    ];
  });
}

function BacktestExportPanel({ result }: { result: BacktestResponse | null }) {
  return (
    <section className="panel backtest-export-panel" aria-label="回测结果导出">
      <div className="panel-title">结果导出</div>
      <div className="export-actions">
        <ToolbarButton
          disabled={!result}
          icon={<Download size={14} />}
          onClick={() =>
            result &&
            downloadTextFile(
              "backtest_trades.csv",
              toCsv(result.trades, TRADE_EXPORT_COLUMNS),
              "text/csv;charset=utf-8"
            )
          }
        >
          导出交易
        </ToolbarButton>
        <ToolbarButton
          disabled={!result}
          icon={<Download size={14} />}
          onClick={() =>
            result &&
            downloadTextFile(
              "backtest_metrics.json",
              JSON.stringify(result.metrics, null, 2),
              "application/json;charset=utf-8"
            )
          }
        >
          导出指标
        </ToolbarButton>
        <ToolbarButton
          disabled={!result}
          icon={<Download size={14} />}
          onClick={() =>
            result &&
            downloadTextFile(
              "backtest_equity_curve.csv",
              toCsv(result.equity_curve, EQUITY_EXPORT_COLUMNS),
              "text/csv;charset=utf-8"
            )
          }
        >
          导出资金曲线
        </ToolbarButton>
      </div>
    </section>
  );
}

function BacktestRunConfigPanel({ config }: { config: BacktestRunConfig }) {
  return (
    <section className="panel backtest-config-panel" aria-label="回测运行配置">
      <div className="panel-title">运行配置</div>
      <div className="backtest-config-grid">
        <ConfigItem label="标的" value={config.symbol} />
        <ConfigItem label="区间" value={config.dateRange} />
        <ConfigItem label="模式" value={config.modeLabel} />
        <ConfigItem label="策略/组合" value={config.strategyOrPortfolio} />
        <ConfigItem label="初始资金" value={config.initialCash} />
        <ConfigItem label="手续费" value={config.commission} />
        <ConfigItem label="滑点" value={config.slippage} />
      </div>
    </section>
  );
}

function ConfigItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="config-item">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function backtestRunConfig(
  settings: PlatformSettings,
  strategies: StrategySpec[],
  selectedStrategyId: string,
  portfolio: PortfolioRequest,
  mode: BacktestMode
): BacktestRunConfig {
  const selectedStrategy = strategies.find((strategy) => strategy.id === selectedStrategyId);
  const strategyLabel = selectedStrategy?.name ?? (selectedStrategyId || "-");
  return {
    symbol: `${settings.symbol} ${settings.exchange}`,
    dateRange: `${settings.start_date || "起始"} - ${settings.end_date || "最新"}`,
    modeLabel: backtestModeLabel(mode),
    strategyOrPortfolio: mode === "portfolio" ? portfolioModeLabel(portfolio.mode) : strategyLabel,
    initialCash: settings.initial_cash.toLocaleString(),
    commission: `${(settings.commission_rate * 100).toFixed(2)}%`,
    slippage: String(settings.slippage)
  };
}

function backtestModeLabel(mode: BacktestMode) {
  return mode === "portfolio" ? "组合策略" : "单策略";
}

function portfolioModeLabel(mode: PortfolioRequest["mode"]) {
  if (mode === "equal_vote") return "等权投票";
  if (mode === "first_active") return "优先级";
  return "加权投票";
}

function backtestReadinessIssues(state: PlatformState, mode: BacktestMode): BacktestReadinessIssue[] {
  const issues: BacktestReadinessIssue[] = [];
  const csvPath = state.settings.csv_path.trim();
  const hasLoadedBars = state.bars.length > 0 && state.dataSummary !== null;
  const strategyIds = new Set(state.strategies.map((strategy) => strategy.id));
  const selectedStrategyReady = Boolean(state.selectedStrategyId && strategyIds.has(state.selectedStrategyId));

  if (!csvPath || !hasLoadedBars) {
    issues.push({
      key: "csv",
      title: "缺少行情CSV",
      detail: csvPath
        ? `请先在数据中心加载、下载或生成演示行情。当前CSV：${csvPath}`
        : "请先在数据中心填写CSV路径，并加载、下载或生成演示行情。"
    });
  }

  if (mode === "single" && !selectedStrategyReady) {
    issues.push({
      key: "strategy",
      title: "缺少回测策略",
      detail: "请先在策略工坊创建或选择一个策略，再运行单策略回测。"
    });
  }

  if (mode === "portfolio") {
    const enabledAllocations = state.portfolio.allocations.filter((allocation) => allocation.enabled);
    const validAllocations = enabledAllocations.filter(
      (allocation) => Number.isFinite(allocation.weight) && allocation.weight > 0 && strategyIds.has(allocation.strategy.id)
    );
    if (validAllocations.length === 0) {
      issues.push({
        key: "portfolio",
        title: "组合分配无效",
        detail: "至少启用一个权重大于 0 的策略分配，并确保分配中的策略仍然存在。"
      });
    }
  }

  return issues;
}

function toCsv<T extends object>(rows: T[], columns: CsvColumn<T>[]) {
  const header = columns.join(",");
  const body = rows.map((row) => columns.map((column) => csvCell(row[column])).join(","));
  return [header, ...body].join("\n");
}

function csvCell(value: unknown) {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, "\"\"")}"` : text;
}

function downloadTextFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
