import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Circle, Expand, LocateFixed, Plus, RotateCcw, Save, Search, Star } from "lucide-react";

import { api } from "../api/client";
import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { ParameterForm, validateStrategyParameterValues } from "../components/ParameterForm";
import { SegmentedControl } from "../components/SegmentedControl";
import { SourceEditor } from "../components/SourceEditor";
import { ToolbarButton } from "../components/ToolbarButton";
import { drawdownOption, priceOption, volumeOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps } from "./pageTypes";
import type { Bar, BacktestResponse, ResearchSignalPreview, SignalsResponse, StrategySpec } from "../types";

type WorkshopMode = "strategy" | "portfolio" | "backtest";
type ResultTab = "summary" | "trades" | "positions" | "factors" | "risk" | "attribution";

const MODE_OPTIONS: { label: string; value: WorkshopMode }[] = [
  { label: "策略", value: "strategy" },
  { label: "组合", value: "portfolio" },
  { label: "回测", value: "backtest" }
];

const RESULT_TABS: { label: string; value: ResultTab }[] = [
  { label: "回测结果", value: "summary" },
  { label: "交易明细", value: "trades" },
  { label: "持仓分析", value: "positions" },
  { label: "因子暴露", value: "factors" },
  { label: "风险分析", value: "risk" },
  { label: "绩效归因", value: "attribution" }
];

const PRICE_VOLUME_GROUP = "strategy-workshop-price-volume";

export function StrategyPage({ state, actions }: PageProps) {
  const selected = currentStrategy(state);
  const [source, setSource] = useState("");
  const [newFile, setNewFile] = useState("my_strategy.py");
  const [newClass, setNewClass] = useState("MyStrategy");
  const [mode, setMode] = useState<WorkshopMode>("strategy");
  const [query, setQuery] = useState("");
  const [showSignals, setShowSignals] = useState(true);
  const [chartExpanded, setChartExpanded] = useState(false);
  const [activeResultTab, setActiveResultTab] = useState<ResultTab>("summary");
  const [sourceError, setSourceError] = useState("");
  const [sourceMessage, setSourceMessage] = useState("");
  const [templateError, setTemplateError] = useState("");
  const [templateMessage, setTemplateMessage] = useState("");
  const [parameterDraft, setParameterDraft] = useState<Record<string, unknown>>(state.strategyParams);
  const parameterDraftRef = useRef<Record<string, unknown>>(state.strategyParams);
  const fieldErrorsRef = useRef<string[]>([]);
  const [parameterErrors, setParameterErrors] = useState<string[]>([]);

  const filteredStrategies = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return state.strategies;
    return state.strategies.filter((strategy) => {
      const sourceLabel = strategy.source === "builtin" ? "内置 builtin" : "自定义 user";
      return `${strategy.name} ${strategy.class_name} ${sourceLabel}`.toLowerCase().includes(normalized);
    });
  }, [query, state.strategies]);

  const maLegend = useMemo(() => movingAverageLegend(state.bars), [state.bars]);
  const comparisonRows = useMemo(() => strategyComparisonRows(state.signals, state.backtest), [state.signals, state.backtest]);
  const researchRows = useMemo(() => researchSignalRows(state.researchSignals), [state.researchSignals]);

  useEffect(() => {
    let mounted = true;
    async function loadSource() {
      setSourceError("");
      setSourceMessage("");
      if (!selected?.editable || !selected.path) {
        setSource("");
        return;
      }
      try {
        const payload = await api.strategySource(selected.path);
        if (mounted) setSource(payload.source);
      } catch (error) {
        if (mounted) {
          setSource("");
          setSourceError(`源码加载失败：${formatActionError(error)}`);
        }
      }
    }
    void loadSource();
    return () => {
      mounted = false;
    };
  }, [selected?.editable, selected?.path]);

  useEffect(() => {
    parameterDraftRef.current = state.strategyParams;
    fieldErrorsRef.current = [];
    setParameterDraft(state.strategyParams);
    setParameterErrors([]);
  }, [selected?.id, state.strategyParams]);

  const saveSource = async () => {
    if (!selected?.path) return;
    setSourceError("");
    setSourceMessage("");
    try {
      await api.saveStrategySource(selected.path.split("/").at(-1) ?? selected.path, source);
      await actions.refreshStrategies(selected.id);
      setSourceMessage("源码已保存");
    } catch (error) {
      setSourceError(`保存源码失败：${formatActionError(error)}`);
    }
  };

  const createTemplate = async () => {
    setTemplateError("");
    setTemplateMessage("");
    try {
      const payload = await api.createStrategyTemplate(newFile, newClass);
      const created = findCreatedStrategy(payload.strategies, payload.path, newClass);
      await actions.refreshStrategies(created?.id);
      setTemplateMessage(created ? `已创建并选中 ${created.class_name}` : "已创建策略模板");
    } catch (error) {
      setTemplateError(`创建策略失败：${formatActionError(error)}`);
    }
  };

  const updateParameters = (values: Record<string, unknown>) => {
    parameterDraftRef.current = values;
    fieldErrorsRef.current = [];
    setParameterDraft(values);
    setParameterErrors([]);
    actions.setStrategyParams(values);
  };

  const updateParameterValidation = (errors: Record<string, string>) => {
    fieldErrorsRef.current = Object.values(errors);
    if (fieldErrorsRef.current.length === 0) setParameterErrors([]);
  };

  const previewSignals = async () => {
    if (fieldErrorsRef.current.length > 0) {
      setParameterErrors([]);
      return;
    }
    const errors = validateStrategyParameterValues(selected?.parameters ?? [], parameterDraftRef.current);
    setParameterErrors(errors);
    if (errors.length > 0) return;
    await actions.previewSignals();
  };

  return (
    <div className="workbench-grid">
      <section className="panel strategy-list">
        <div className="panel-title between">
          <span>策略列表</span>
        </div>
        <SegmentedControl options={MODE_OPTIONS} value={mode} onChange={setMode} />
        <details className="template-details">
          <summary>
            <Plus size={14} /> 新建策略
          </summary>
          <div className="template-row">
            <input aria-label="新策略文件名" value={newFile} onChange={(event) => setNewFile(event.currentTarget.value)} />
            <input aria-label="新策略类名" value={newClass} onChange={(event) => setNewClass(event.currentTarget.value)} />
            <button className="mini-button" onClick={createTemplate}>
              创建模板
            </button>
          </div>
          {templateError ? <p className="inline-alert">{templateError}</p> : null}
          {templateMessage ? <p className="inline-success">{templateMessage}</p> : null}
        </details>
        <label className="search-box">
          <Search size={13} />
          <input aria-label="搜索策略名称或来源" value={query} placeholder="搜索策略名称" onChange={(event) => setQuery(event.currentTarget.value)} />
        </label>
        <div className="strategy-items">
          {filteredStrategies.map((strategy) => (
            <button
              key={strategy.id}
              className={`strategy-item ${strategy.id === selected?.id ? "active" : ""}`}
              onClick={() => actions.setSelectedStrategyId(strategy.id)}
            >
              <Circle className="strategy-status-dot" size={9} />
              <span>{strategy.name}</span>
              <small>{strategy.source === "builtin" ? "内置" : "自定义"}</small>
              <Star className={strategy.id === selected?.id ? "favorite-icon active" : "favorite-icon"} size={14} />
            </button>
          ))}
        </div>
        <div className="panel-title">策略参数</div>
        <ParameterForm
          parameters={selected?.parameters ?? []}
          values={parameterDraft}
          onChange={updateParameters}
          onValidationChange={updateParameterValidation}
        />
        {parameterErrors.length ? (
          <div className="parameter-errors" role="alert">
            {parameterErrors.map((error) => (
              <span key={error}>{error}</span>
            ))}
          </div>
        ) : null}
        <ToolbarButton icon={<Save size={16} />} variant="primary" onClick={previewSignals}>
          预览信号
        </ToolbarButton>
        <ToolbarButton icon={<Activity size={16} />} onClick={actions.previewResearchSignals}>
          缠论/RSI研判
        </ToolbarButton>
        <div className="panel-title">策略源码</div>
        {selected?.editable ? (
          <>
            <SourceEditor
              value={source}
              onChange={(nextSource) => {
                setSource(nextSource);
                setSourceError("");
                setSourceMessage("");
              }}
            />
            {sourceError ? <p className="inline-alert">{sourceError}</p> : null}
            {sourceMessage ? <p className="inline-success">{sourceMessage}</p> : null}
            <ToolbarButton icon={<Save size={16} />} onClick={saveSource}>
              保存源码
            </ToolbarButton>
          </>
        ) : (
          <p className="caption">内置策略不可直接编辑，可新建用户策略模板后修改。</p>
        )}
      </section>
      <main className={chartExpanded ? "center-stage chart-expanded" : "center-stage"}>
        <div className="command-row">
          <select value={state.settings.symbol} onChange={(event) => actions.setSettings({ ...state.settings, symbol: event.currentTarget.value })}>
            <option>{state.settings.symbol} 沪深A股</option>
          </select>
          <button className="tab-button active">日线</button>
          <button className="tab-button">周线</button>
          <button className="tab-button">月线</button>
          <span className="date-range">{state.settings.start_date} - {state.settings.end_date}</span>
        </div>
        <ChartPanel
          title="信号标记 · K线回测视图"
          option={priceOption(state.bars, showSignals ? state.signals?.signals ?? [] : [])}
          height={360}
          group={PRICE_VOLUME_GROUP}
          toolbar={
            <>
              <label className="chart-check">
                <input type="checkbox" aria-label="显示信号标记" checked={showSignals} onChange={(event) => setShowSignals(event.currentTarget.checked)} />
                信号
              </label>
              <span className="legend-chip">
                <strong>MA20</strong> {maLegend.ma20}
              </span>
              <span className="legend-chip">
                <strong>MA60</strong> {maLegend.ma60}
              </span>
              <button
                aria-label="重置视图"
                className="icon-button"
                onClick={() => {
                  setShowSignals(true);
                  setChartExpanded(false);
                }}
              >
                <RotateCcw size={14} />
              </button>
              <button aria-label="适配视图" className="icon-button" onClick={() => setChartExpanded(false)}>
                <LocateFixed size={14} />
              </button>
              <button aria-label="全屏图表" className="icon-button" onClick={() => setChartExpanded((current) => !current)}>
                <Expand size={14} />
              </button>
            </>
          }
        />
        <ChartPanel title="成交量" option={volumeOption(state.bars)} height={130} group={PRICE_VOLUME_GROUP} />
        <ChartPanel title="回撤曲线" option={drawdownOption(state.backtest)} height={120} />
        <section className="panel">
          <div className="tabs">
            {RESULT_TABS.map((tab) => (
              <button key={tab.value} className={activeResultTab === tab.value ? "active" : ""} onClick={() => setActiveResultTab(tab.value)}>
                {tab.label}
              </button>
            ))}
          </div>
          <MetricStrip
            metrics={[
              { label: "信号数量", value: state.signals?.summary.signals ?? 0 },
              { label: "买入信号", value: state.signals?.summary.buys ?? 0, tone: "positive" },
              { label: "卖出信号", value: state.signals?.summary.sells ?? 0, tone: "negative" },
              { label: "基准收益", value: formatPercent(state.backtest?.metrics.benchmark_return_pct) },
              { label: "超额收益", value: formatPercent(state.backtest?.metrics.excess_return_pct), tone: (state.backtest?.metrics.excess_return_pct ?? 0) >= 0 ? "positive" : "negative" },
              { label: "最大回撤", value: `${state.backtest?.metrics.max_drawdown_pct.toFixed(2) ?? "0.00"}%` },
              { label: "累计收益", value: `${state.backtest?.metrics.total_return_pct.toFixed(2) ?? "0.00"}%`, tone: "positive" }
            ]}
          />
          <ResultTabContent
            activeTab={activeResultTab}
            backtest={state.backtest}
            signals={state.signals}
            comparisonRows={comparisonRows}
          />
        </section>
        <ResearchSignalPanel preview={state.researchSignals} rows={researchRows} />
      </main>
    </div>
  );
}

function findCreatedStrategy(strategies: StrategySpec[], path: string, className: string): StrategySpec | undefined {
  return (
    strategies.find((strategy) => strategy.path === path) ??
    strategies.find((strategy) => strategy.source === "user" && strategy.class_name === className) ??
    strategies.find((strategy) => strategy.source === "user" && strategy.editable)
  );
}

function formatActionError(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "未知错误";
}

function movingAverageLegend(bars: Bar[]) {
  return {
    ma20: formatNullableAverage(bars, 20),
    ma60: formatNullableAverage(bars, 60)
  };
}

function formatNullableAverage(bars: Bar[], window: number) {
  if (bars.length < window) return "-";
  const rows = bars.slice(-window);
  const average = rows.reduce((total, bar) => total + bar.close_price, 0) / window;
  return average.toFixed(2);
}

function ResultTabContent({
  activeTab,
  backtest,
  signals,
  comparisonRows
}: {
  activeTab: ResultTab;
  backtest: BacktestResponse | null;
  signals: SignalsResponse | null;
  comparisonRows: Record<string, unknown>[];
}) {
  if (activeTab === "trades") {
    return (
      <>
        <div className="panel-title compact-title">交易明细</div>
        <DataTable rows={tradeRows(backtest)} columns={["交易日", "方向", "标的", "价格", "数量", "手续费"]} emptyText="运行回测后显示交易明细" />
      </>
    );
  }
  if (activeTab === "positions") {
    return (
      <>
        <div className="panel-title compact-title">持仓分析</div>
        <DataTable rows={positionRows(backtest)} columns={["指标", "数值"]} emptyText="运行回测后显示持仓分析" />
      </>
    );
  }
  if (activeTab === "factors") {
    return (
      <>
        <div className="panel-title compact-title">因子暴露</div>
        <DataTable rows={factorRows(signals, backtest)} columns={["因子", "暴露"]} emptyText="等待预览或回测数据" />
      </>
    );
  }
  if (activeTab === "risk") {
    return (
      <>
        <div className="panel-title compact-title">风险分析</div>
        <DataTable rows={riskRows(backtest)} columns={["项目", "状态"]} emptyText="运行回测后显示风险分析" />
      </>
    );
  }
  if (activeTab === "attribution") {
    return (
      <>
        <div className="panel-title compact-title">绩效归因</div>
        <DataTable rows={attributionRows(backtest)} columns={["来源", "贡献"]} emptyText="运行回测后显示绩效归因" />
      </>
    );
  }
  return (
    <>
      <div className="panel-title compact-title">策略表现对比</div>
      <DataTable rows={comparisonRows} columns={["指标", "策略回测", "现金基准", "长持"]} emptyText="等待预览或回测数据" />
    </>
  );
}

function ResearchSignalPanel({ preview, rows }: { preview: ResearchSignalPreview | null; rows: Record<string, unknown>[] }) {
  if (!preview) {
    return (
      <section className="panel research-signal-panel">
        <div className="panel-title between">
          <span>缠论/RSI研判</span>
          <span className="caption">未生成</span>
        </div>
        <div className="empty-table">暂无研判结果</div>
      </section>
    );
  }

  return (
    <section className="panel research-signal-panel">
      <div className="panel-title between">
        <span>缠论/RSI研判</span>
        <span className={`status-pill ${preview.score.direction}`}>{preview.score.direction}</span>
      </div>
      <MetricStrip
        metrics={[
          { label: "综合分", value: preview.score.total_score.toFixed(1), tone: preview.score.total_score >= 0 ? "positive" : "negative" },
          { label: "置信度", value: `${Math.round(preview.score.confidence * 100)}%` },
          { label: "缠论", value: preview.score.chan_score.toFixed(1) },
          { label: "RSI", value: preview.score.rsi_score.toFixed(1) }
        ]}
      />
      {preview.blockers.length ? (
        <div className="parameter-errors" role="alert">
          {preview.blockers.map((blocker) => (
            <span key={blocker.code}>{blocker.message}</span>
          ))}
        </div>
      ) : null}
      <p className="caption">{preview.score.summary}</p>
      <DataTable rows={rows} columns={["日期", "类型", "方向", "价格", "分数", "原因"]} emptyText="暂无缠论/RSI触发信号" />
    </section>
  );
}

function researchSignalRows(preview: ResearchSignalPreview | null): Record<string, unknown>[] {
  return (preview?.signals ?? []).map((signal) => ({
    日期: signal.trading_day,
    类型: signal.kind,
    方向: signal.action,
    价格: signal.price,
    分数: signal.score,
    原因: signal.reason
  }));
}

function strategyComparisonRows(signals: SignalsResponse | null, backtest: BacktestResponse | null): Record<string, unknown>[] {
  if (!signals && !backtest) return [];
  const metrics = backtest?.metrics;
  return [
    { 指标: "累计收益", 策略回测: formatPercent(metrics?.total_return_pct), 现金基准: "0.00%", 长持: formatPercent(metrics?.benchmark_return_pct) },
    { 指标: "基准收益", 策略回测: formatPercent(metrics?.benchmark_return_pct), 现金基准: "0.00%", 长持: formatPercent(metrics?.benchmark_return_pct) },
    { 指标: "超额收益", 策略回测: formatPercent(metrics?.excess_return_pct), 现金基准: "-", 长持: "0.00%" },
    { 指标: "最大回撤", 策略回测: formatPercent(metrics?.max_drawdown_pct), 现金基准: "0.00%", 长持: "-" },
    { 指标: "年化波动", 策略回测: formatPercent(metrics?.annual_volatility_pct), 现金基准: "0.00%", 长持: "-" },
    { 指标: "夏普比率", 策略回测: formatNumber(metrics?.sharpe_ratio), 现金基准: "-", 长持: "-" },
    { 指标: "交易胜率", 策略回测: formatPercent(metrics?.win_rate_pct), 现金基准: "-", 长持: `${signals?.summary.buys ?? 0} 买 / ${signals?.summary.sells ?? 0} 卖` },
    { 指标: "盈亏比", 策略回测: formatNumber(metrics?.profit_factor), 现金基准: "-", 长持: `${metrics?.trade_count ?? 0} 笔交易` }
  ];
}

function tradeRows(backtest: BacktestResponse | null): Record<string, unknown>[] {
  return (backtest?.trades ?? []).map((trade) => ({
    交易日: trade.trading_day,
    方向: trade.side,
    标的: trade.symbol,
    价格: trade.price,
    数量: trade.volume,
    手续费: trade.commission
  }));
}

function positionRows(backtest: BacktestResponse | null): Record<string, unknown>[] {
  const metrics = backtest?.metrics;
  if (!metrics) return [];
  return [
    { 指标: "平均持仓", 数值: formatPercent(metrics.exposure_pct) },
    { 指标: "交易次数", 数值: metrics.trade_count },
    { 指标: "最终权益", 数值: metrics.final_equity.toFixed(2) }
  ];
}

function factorRows(signals: SignalsResponse | null, backtest: BacktestResponse | null): Record<string, unknown>[] {
  if (!signals && !backtest) return [];
  return [
    { 因子: "趋势信号", 暴露: `${signals?.summary.signals ?? 0} 个` },
    { 因子: "买入压力", 暴露: `${signals?.summary.buys ?? 0} 个买入` },
    { 因子: "卖出压力", 暴露: `${signals?.summary.sells ?? 0} 个卖出` },
    { 因子: "策略波动", 暴露: formatPercent(backtest?.metrics.annual_volatility_pct) }
  ];
}

function riskRows(backtest: BacktestResponse | null): Record<string, unknown>[] {
  if (!backtest) return [];
  const status = backtest.risk_status;
  return [
    { 项目: "风控状态", 状态: status.ok ? "通过" : "未通过" },
    { 项目: "最大回撤", 状态: formatPercent(backtest.metrics.max_drawdown_pct) },
    { 项目: "风险提示", 状态: status.warnings.length ? status.warnings.join("；") : "暂无" }
  ];
}

function attributionRows(backtest: BacktestResponse | null): Record<string, unknown>[] {
  const metrics = backtest?.metrics;
  if (!metrics) return [];
  return [
    { 来源: "策略收益", 贡献: formatPercent(metrics.total_return_pct) },
    { 来源: "基准收益", 贡献: formatPercent(metrics.benchmark_return_pct) },
    { 来源: "超额收益", 贡献: formatPercent(metrics.excess_return_pct) },
    { 来源: "交易摩擦", 贡献: `${backtest.trades.length} 笔交易` }
  ];
}

function formatNumber(value: number | null | undefined) {
  return value === null || value === undefined ? "-" : value.toFixed(2);
}

function formatPercent(value: number | null | undefined) {
  return value === null || value === undefined ? "-" : `${value.toFixed(2)}%`;
}
