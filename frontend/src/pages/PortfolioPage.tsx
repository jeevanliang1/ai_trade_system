import { useEffect, useMemo, useState } from "react";
import { Plus, Trash2 } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { ParameterForm } from "../components/ParameterForm";
import { SegmentedControl } from "../components/SegmentedControl";
import { Switch } from "../components/Switch";
import { ToolbarButton } from "../components/ToolbarButton";
import { priceOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps } from "./pageTypes";
import type { PortfolioAllocation, PortfolioPreviewAllocation, PortfolioRequest, PortfolioSignalContribution, SignalsResponse, StrategySpec } from "../types";

const MODE_DETAILS: Record<
  PortfolioRequest["mode"],
  {
    label: string;
    summary: string;
    detail: string;
    bestFor: string;
  }
> = {
  weighted_vote: {
    label: "加权投票",
    summary: "按每行权重累计买入/卖出得分，权重越高的策略影响越大。",
    detail: "买卖方向分别累计启用策略的原始权重，得分更高的一侧生成组合信号。",
    bestFor: "适合策略可信度不同、需要表达主次仓位影响的组合。"
  },
  equal_vote: {
    label: "等权投票",
    summary: "每个启用策略一票，忽略原始权重，只比较买卖信号数量。",
    detail: "权重仅影响归一化展示，不参与投票得分。",
    bestFor: "适合先验证策略方向一致性，避免单个高权重策略压过其他信号。"
  },
  first_active: {
    label: "优先级",
    summary: "按分配行顺序采用第一个有效信号，适合主备策略或优先级执行。",
    detail: "第一条有效信号会直接成为组合信号，后续策略不会继续竞争。",
    bestFor: "适合有明确主策略、备用策略或人工排序优先级的场景。"
  }
};

export function PortfolioPage({ state, actions }: PageProps) {
  const selected = currentStrategy(state);
  const [draftPortfolio, setDraftPortfolio] = useState<PortfolioRequest>(state.portfolio);
  const allocations = draftPortfolio.allocations;
  const weightSummary = useMemo(() => normalizedWeightSummary(allocations, state.strategies), [allocations, state.strategies]);
  const activeMode = MODE_DETAILS[draftPortfolio.mode];

  useEffect(() => {
    setDraftPortfolio(state.portfolio);
  }, [state.portfolio]);

  const commitPortfolio = (portfolio: PortfolioRequest) => {
    setDraftPortfolio(portfolio);
    actions.setPortfolio(portfolio);
  };
  const updatePortfolio = (patch: Partial<typeof state.portfolio>) => commitPortfolio({ ...draftPortfolio, ...patch });
  const updateAllocation = (index: number, nextAllocation: PortfolioAllocation) => {
    commitPortfolio({
      ...draftPortfolio,
      allocations: allocations.map((allocation, currentIndex) => (currentIndex === index ? nextAllocation : allocation))
    });
  };
  const addAllocation = () => {
    const strategy = selected ?? state.strategies[0];
    if (!strategy) return;
    commitPortfolio({
      ...draftPortfolio,
      allocations: [
        ...allocations,
        { strategy: { id: strategy.id, params: paramsFromStrategy(strategy, state.settings.symbol) }, weight: 1, enabled: true }
      ]
    });
  };
  const removeAllocation = (index: number) => {
    commitPortfolio({
      ...draftPortfolio,
      allocations: allocations.filter((_, currentIndex) => currentIndex !== index)
    });
  };

  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">组合实验室</div>
        <SegmentedControl
          value={draftPortfolio.mode}
          onChange={(mode) => updatePortfolio({ mode })}
          options={[
            { label: "加权投票", value: "weighted_vote" },
            { label: "等权投票", value: "equal_vote" },
            { label: "优先级", value: "first_active" }
          ]}
        />
        <section className="mode-explainer" aria-label="组合模式说明">
          <div className="panel-title compact-title">模式说明</div>
          <div className="active-mode-card">
            <strong>当前模式：{activeMode.label}</strong>
            <p>{activeMode.summary}</p>
            <small>{activeMode.detail}</small>
          </div>
          <div className="mode-detail-grid">
            {(Object.keys(MODE_DETAILS) as PortfolioRequest["mode"][]).map((mode) => {
              const detail = MODE_DETAILS[mode];
              return (
                <article className={mode === draftPortfolio.mode ? "mode-detail-card active" : "mode-detail-card"} key={mode}>
                  <strong>{detail.label}</strong>
                  <p>{detail.summary}</p>
                  <small>{detail.bestFor}</small>
                </article>
              );
            })}
          </div>
        </section>
        <Switch checked={draftPortfolio.ai_adjust} label="AI参与评分" onChange={(ai_adjust) => updatePortfolio({ ai_adjust })} />
        <div className="portfolio-editor">
          <div className="panel-title compact-title between">
            <span>策略分配</span>
            <button className="mini-button" onClick={addAllocation}>
              <Plus size={14} /> 新增分配
            </button>
          </div>
          {allocations.map((allocation, index) => {
            const strategy = state.strategies.find((item) => item.id === allocation.strategy.id);
            return (
              <div className="allocation-row" key={`${allocation.strategy.id}-${index}`}>
                <label className="field">
                  <span>策略</span>
                  <select
                    aria-label={`第${index + 1}行策略`}
                    value={allocation.strategy.id}
                    onChange={(event) => {
                      const nextStrategy = state.strategies.find((item) => item.id === event.currentTarget.value);
                      if (!nextStrategy) return;
                      updateAllocation(index, {
                        ...allocation,
                        strategy: { id: nextStrategy.id, params: paramsFromStrategy(nextStrategy, state.settings.symbol) }
                      });
                    }}
                  >
                    {state.strategies.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field">
                  <span>权重</span>
                  <input
                    aria-label={`第${index + 1}行权重`}
                    min={0}
                    step={0.01}
                    type="number"
                    value={String(allocation.weight)}
                    onChange={(event) => {
                      const nextWeight = event.currentTarget.value === "" ? 0 : Number(event.currentTarget.value);
                      updateAllocation(index, {
                        ...allocation,
                        weight: Number.isFinite(nextWeight) ? Math.max(0, nextWeight) : 0
                      });
                    }}
                  />
                </label>
                <label className="allocation-toggle">
                  <input
                    aria-label={`第${index + 1}行启用`}
                    type="checkbox"
                    checked={allocation.enabled}
                    onChange={(event) => updateAllocation(index, { ...allocation, enabled: event.currentTarget.checked })}
                  />
                  启用
                </label>
                <button className="icon-button" aria-label={`删除第${index + 1}行`} onClick={() => removeAllocation(index)}>
                  <Trash2 size={14} />
                </button>
                <small>{strategy?.source === "user" ? "自定义策略" : "内置策略"}</small>
              </div>
            );
          })}
          <div className="weight-summary">
            <div className="panel-title compact-title">归一化权重</div>
            <strong>启用权重合计 {weightSummary.total.toFixed(2)}</strong>
            {weightSummary.rows.length ? (
              weightSummary.rows.map((row, index) => (
                <span key={`${row.id}-${index}`}>
                  {row.name} {row.percent}
                </span>
              ))
            ) : (
              <span>暂无启用权重</span>
            )}
          </div>
        </div>
        <ParameterForm parameters={selected?.parameters ?? []} values={state.strategyParams} onChange={actions.setStrategyParams} />
        <ToolbarButton onClick={actions.previewPortfolio}>预览组合信号</ToolbarButton>
      </section>
      <section className="main-column">
        <ChartPanel title="组合信号" option={priceOption(state.bars, state.signals?.signals ?? [])} height={420} />
        <AiWeightPreviewPanel signals={state.signals} portfolio={draftPortfolio} allocations={allocations} strategies={state.strategies} />
        <PortfolioBreakdownPanel signals={state.signals} allocations={allocations} strategies={state.strategies} />
        <section className="panel">
          <div className="panel-title">策略配置</div>
          <DataTable
            rows={allocations.map((allocation) => ({
              策略: state.strategies.find((item) => item.id === allocation.strategy.id)?.name ?? allocation.strategy.id,
              权重: allocation.weight,
              归一化: normalizedWeightLabel(allocation, allocations),
              启用: allocation.enabled ? "是" : "否"
            }))}
          />
        </section>
      </section>
    </div>
  );
}

function AiWeightPreviewPanel({
  signals,
  portfolio,
  allocations,
  strategies
}: {
  signals: SignalsResponse | null;
  portfolio: PortfolioRequest;
  allocations: PortfolioAllocation[];
  strategies: StrategySpec[];
}) {
  if (!portfolio.ai_adjust && !signals?.ai_adjustment?.enabled) return null;
  const adjustment = signals?.ai_adjustment;
  const rows = aiWeightRows(signals, allocations, strategies);
  const direction = directionLabel(adjustment?.direction ?? portfolio.ai_direction);
  const stateLabel = adjustment ? (adjustment.applied ? "已应用" : "未触发调整") : "等待预览";

  return (
    <section className="panel ai-weight-preview-panel" aria-label="AI权重调整预览">
      <div className="panel-title between">
        <span>AI权重预览</span>
        <small>
          <span>方向：{direction}</span>
          <span>{stateLabel}</span>
        </small>
      </div>
      {adjustment ? (
        <div className="ai-weight-rows">
          {rows.map((row) => (
            <article className={row.adjusted ? "ai-weight-row adjusted" : "ai-weight-row"} key={row.key}>
              <strong>{row.name}</strong>
              <span>{formatNumber(row.baseWeight)} -&gt; {formatNumber(row.adjustedWeight)}</span>
              <small>{formatDelta(row.delta)}</small>
            </article>
          ))}
        </div>
      ) : (
        <p className="breakdown-empty">点击“预览组合信号”后，这里会显示 AI 参与评分前后的组合权重。</p>
      )}
    </section>
  );
}

function PortfolioBreakdownPanel({
  signals,
  allocations,
  strategies
}: {
  signals: SignalsResponse | null;
  allocations: PortfolioAllocation[];
  strategies: StrategySpec[];
}) {
  const breakdown = signals?.breakdown;
  const rows = portfolioBreakdownRows(signals, allocations, strategies);

  return (
    <section className="panel signal-breakdown-panel" aria-label="组合信号拆解">
      <div className="panel-title between">
        <span>信号拆解</span>
        {breakdown ? <small>{modeLabel(breakdown.mode)} · 最近预览</small> : <small>等待组合预览</small>}
      </div>
      {breakdown ? (
        <>
          <div className="breakdown-summary">
            <span>买入得分 {formatNumber(breakdown.buy_score)}</span>
            <span>卖出得分 {formatNumber(breakdown.sell_score)}</span>
            <span>参与信号 {breakdown.active_signals}</span>
          </div>
          <div className="breakdown-list">
            {rows.map((row) => (
              <article className={row.selected ? "breakdown-row selected" : "breakdown-row"} key={row.key}>
                <div className="breakdown-row-header">
                  <strong>{row.name}</strong>
                  <span className={`signal-badge ${row.actionClass}`}>{row.actionLabel}</span>
                  <span className={row.selected ? "selected-badge selected" : "selected-badge"}>{row.selectedLabel}</span>
                </div>
                <div className="breakdown-row-meta">
                  <span>贡献 {formatNumber(row.score)}</span>
                  <span>权重 {formatNumber(row.weight)}</span>
                  <span>量 {row.volume}</span>
                </div>
                <p>{row.reason}</p>
              </article>
            ))}
          </div>
        </>
      ) : (
        <p className="breakdown-empty">点击“预览组合信号”后，这里会显示每个策略的原始信号、贡献得分和是否被组合采用。</p>
      )}
    </section>
  );
}

function paramsFromStrategy(strategy: StrategySpec, symbol: string): Record<string, unknown> {
  const params: Record<string, unknown> = {};
  for (const parameter of strategy.parameters) {
    params[parameter.name] = parameter.name === "symbol" ? symbol : parameter.default;
  }
  return params;
}

function normalizedWeightSummary(allocations: PortfolioAllocation[], strategies: StrategySpec[]) {
  const enabledRows = allocations.filter((allocation) => allocation.enabled && allocation.weight > 0);
  const total = enabledRows.reduce((sum, allocation) => sum + allocation.weight, 0);
  return {
    total,
    rows: enabledRows.map((allocation) => ({
      id: allocation.strategy.id,
      name: strategies.find((strategy) => strategy.id === allocation.strategy.id)?.name ?? allocation.strategy.id,
      percent: total > 0 ? `${((allocation.weight / total) * 100).toFixed(2)}%` : "0.00%"
    }))
  };
}

function normalizedWeightLabel(allocation: PortfolioAllocation, allocations: PortfolioAllocation[]) {
  if (!allocation.enabled || allocation.weight <= 0) return "0.00%";
  const total = allocations.filter((item) => item.enabled && item.weight > 0).reduce((sum, item) => sum + item.weight, 0);
  return total > 0 ? `${((allocation.weight / total) * 100).toFixed(2)}%` : "0.00%";
}

type BreakdownRow = {
  key: string;
  name: string;
  actionLabel: string;
  actionClass: string;
  selectedLabel: string;
  selected: boolean;
  score: number;
  weight: number;
  volume: number;
  reason: string;
};

type AiWeightRow = {
  key: string;
  name: string;
  baseWeight: number;
  adjustedWeight: number;
  delta: number;
  adjusted: boolean;
};

function aiWeightRows(
  signals: SignalsResponse | null,
  allocations: PortfolioAllocation[],
  strategies: StrategySpec[]
): AiWeightRow[] {
  const responseAllocations = signals?.allocations ?? currentAllocationViews(allocations, strategies);
  return responseAllocations.map((allocation) => {
    const baseWeight = allocation.base_weight ?? allocation.weight;
    const adjustedWeight = allocation.adjusted_weight ?? allocation.weight;
    const delta = allocation.ai_delta ?? adjustedWeight - baseWeight;
    return {
      key: `${allocation.index}-${allocation.name}`,
      name: allocation.name,
      baseWeight,
      adjustedWeight,
      delta,
      adjusted: allocation.ai_adjusted ?? delta !== 0
    };
  });
}

function portfolioBreakdownRows(
  signals: SignalsResponse | null,
  allocations: PortfolioAllocation[],
  strategies: StrategySpec[]
): BreakdownRow[] {
  const responseAllocations = signals?.allocations ?? currentAllocationViews(allocations, strategies);
  const contributions = new Map<number, PortfolioSignalContribution>();
  for (const contribution of signals?.breakdown?.contributions ?? []) {
    contributions.set(contribution.allocation_index, contribution);
  }
  return responseAllocations.map((allocation) => {
    const contribution = contributions.get(allocation.index);
    const enabled = allocation.enabled;
    const actionLabel = contribution ? signalActionLabel(contribution.action) : enabled ? "未触发" : "未启用";
    return {
      key: `${allocation.index}-${allocation.name}`,
      name: allocation.name,
      actionLabel,
      actionClass: contribution ? contribution.action : enabled ? "idle" : "disabled",
      selectedLabel: contribution ? (contribution.selected ? "采用" : "未采用") : enabled ? "观察" : "停用",
      selected: contribution?.selected ?? false,
      score: contribution?.score ?? 0,
      weight: contribution?.weight ?? allocation.weight,
      volume: contribution?.volume ?? 0,
      reason: contribution?.reason ?? (enabled ? "最近一个交易日没有原始信号" : "该分配未启用")
    };
  });
}

function currentAllocationViews(allocations: PortfolioAllocation[], strategies: StrategySpec[]): PortfolioPreviewAllocation[] {
  return allocations.map((allocation, index) => ({
    index,
    name: strategies.find((strategy) => strategy.id === allocation.strategy.id)?.name ?? allocation.strategy.id,
    weight: allocation.weight,
    enabled: allocation.enabled
  }));
}

function signalActionLabel(action: string) {
  if (action === "buy") return "买入";
  if (action === "sell") return "卖出";
  return action;
}

function directionLabel(direction: string | null | undefined) {
  if (direction === "bullish") return "看多";
  if (direction === "bearish") return "看空";
  if (direction === "neutral") return "中性";
  return "等待";
}

function modeLabel(mode: string) {
  return MODE_DETAILS[mode as PortfolioRequest["mode"]]?.label ?? mode;
}

function formatNumber(value: number) {
  return value.toFixed(2);
}

function formatDelta(value: number) {
  if (value > 0) return `+${formatNumber(value)}`;
  return formatNumber(value);
}
