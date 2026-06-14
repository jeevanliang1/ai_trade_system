import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { ParameterForm } from "../components/ParameterForm";
import { SegmentedControl } from "../components/SegmentedControl";
import { Switch } from "../components/Switch";
import { ToolbarButton } from "../components/ToolbarButton";
import { priceOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps } from "./pageTypes";

export function PortfolioPage({ state, actions }: PageProps) {
  const selected = currentStrategy(state);
  const allocations = state.portfolio.allocations;
  const updatePortfolio = (patch: Partial<typeof state.portfolio>) => actions.setPortfolio({ ...state.portfolio, ...patch });
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">组合实验室</div>
        <SegmentedControl
          value={state.portfolio.mode}
          onChange={(mode) => updatePortfolio({ mode })}
          options={[
            { label: "加权投票", value: "weighted_vote" },
            { label: "等权投票", value: "equal_vote" },
            { label: "优先级", value: "first_active" }
          ]}
        />
        <Switch checked={state.portfolio.ai_adjust} label="AI参与评分" onChange={(ai_adjust) => updatePortfolio({ ai_adjust })} />
        <ParameterForm parameters={selected?.parameters ?? []} values={state.strategyParams} onChange={actions.setStrategyParams} />
        <ToolbarButton
          variant="primary"
          onClick={() => {
            if (!selected) return;
            actions.setPortfolio({
              ...state.portfolio,
              allocations: [
                ...allocations,
                { strategy: { id: selected.id, params: state.strategyParams }, weight: 1 / Math.max(1, allocations.length + 1), enabled: true }
              ]
            });
          }}
        >
          添加当前策略
        </ToolbarButton>
        <ToolbarButton onClick={actions.previewPortfolio}>预览组合信号</ToolbarButton>
      </section>
      <section className="main-column">
        <ChartPanel title="组合信号" option={priceOption(state.bars, state.signals?.signals ?? [])} height={420} />
        <section className="panel">
          <div className="panel-title">策略配置</div>
          <DataTable
            rows={allocations.map((allocation) => ({
              策略: state.strategies.find((item) => item.id === allocation.strategy.id)?.name ?? allocation.strategy.id,
              权重: allocation.weight,
              启用: allocation.enabled ? "是" : "否"
            }))}
          />
        </section>
      </section>
    </div>
  );
}
