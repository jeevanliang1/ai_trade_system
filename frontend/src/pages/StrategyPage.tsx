import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, Circle, Expand, LocateFixed, Plus, RotateCcw, Save, Search } from "lucide-react";

import { api } from "../api/client";
import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { ParameterForm, validateStrategyParameterValues } from "../components/ParameterForm";
import { SourceEditor } from "../components/SourceEditor";
import { ToolbarButton } from "../components/ToolbarButton";
import { priceOption, volumeOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps } from "./pageTypes";
import type { Bar, ResearchSignalPreview, SignalRow, StrategySpec } from "../types";

const PRICE_VOLUME_GROUP = "strategy-workshop-price-volume";

export function StrategyPage({ state, actions }: PageProps) {
  const selected = currentStrategy(state);
  const [source, setSource] = useState("");
  const [newFile, setNewFile] = useState("my_strategy.py");
  const [newClass, setNewClass] = useState("MyStrategy");
  const [query, setQuery] = useState("");
  const [showSignals, setShowSignals] = useState(true);
  const [chartExpanded, setChartExpanded] = useState(false);
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
      return `${strategy.display_name} ${strategy.description} ${strategy.name} ${strategy.class_name} ${sourceLabel}`.toLowerCase().includes(normalized);
    });
  }, [query, state.strategies]);

  const maLegend = useMemo(() => movingAverageLegend(state.bars), [state.bars]);
  const signalRows = useMemo(() => signalPreviewRows(state.signals?.signals ?? []), [state.signals]);
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
              <span className="strategy-label">
                <strong>{strategy.display_name}</strong>
                <em>{strategy.class_name}</em>
                <b>{strategy.description}</b>
              </span>
              <small>{strategy.source === "builtin" ? "内置" : "自定义"}</small>
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
          <span className="timeframe-pill active">日线</span>
          <span className="date-range">{state.settings.start_date} - {state.settings.end_date}</span>
        </div>
        <ChartPanel
          title="信号标记 · K线视图"
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
        <SignalPreviewPanel summary={state.signals?.summary} rows={signalRows} />
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

function SignalPreviewPanel({
  summary,
  rows
}: {
  summary: { signals: number; buys: number; sells: number } | undefined;
  rows: Record<string, unknown>[];
}) {
  return (
    <section className="panel signal-preview-panel">
      <div className="panel-title between">
        <span>信号预览</span>
        <span className="caption">完整回测请进入回测中心</span>
      </div>
      <MetricStrip
        metrics={[
          { label: "信号数量", value: summary?.signals ?? 0 },
          { label: "买入信号", value: summary?.buys ?? 0, tone: "positive" },
          { label: "卖出信号", value: summary?.sells ?? 0, tone: "negative" }
        ]}
      />
      <DataTable rows={rows} columns={["日期", "方向", "标的", "价格", "数量", "原因"]} emptyText="点击“预览信号”后显示策略信号" />
    </section>
  );
}

function signalPreviewRows(signals: SignalRow[]): Record<string, unknown>[] {
  return signals.map((signal) => ({
    日期: signal.trading_day,
    方向: signal.action,
    标的: signal.symbol,
    价格: signal.price,
    数量: signal.volume,
    原因: signal.reason
  }));
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
