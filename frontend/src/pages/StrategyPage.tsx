import { useEffect, useState } from "react";
import { Plus, Save, Star } from "lucide-react";

import { api } from "../api/client";
import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { ParameterForm } from "../components/ParameterForm";
import { ToolbarButton } from "../components/ToolbarButton";
import { priceOption, volumeOption } from "./chartOptions";
import { currentStrategy } from "./pageTypes";
import type { PageProps } from "./pageTypes";

export function StrategyPage({ state, actions }: PageProps) {
  const selected = currentStrategy(state);
  const [source, setSource] = useState("");
  const [newFile, setNewFile] = useState("my_strategy.py");
  const [newClass, setNewClass] = useState("MyStrategy");

  useEffect(() => {
    let mounted = true;
    async function loadSource() {
      if (!selected?.editable || !selected.path) {
        setSource("");
        return;
      }
      try {
        const payload = await api.strategySource(selected.path);
        if (mounted) setSource(payload.source);
      } catch {
        if (mounted) setSource("");
      }
    }
    void loadSource();
    return () => {
      mounted = false;
    };
  }, [selected?.editable, selected?.path]);

  const saveSource = async () => {
    if (!selected?.path) return;
    await api.saveStrategySource(selected.path.split("/").at(-1) ?? selected.path, source);
    await actions.refreshStrategies();
  };

  const createTemplate = async () => {
    await api.createStrategyTemplate(newFile, newClass);
    await actions.refreshStrategies();
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
        </details>
        <div className="search-box">搜索策略名称</div>
        <div className="strategy-items">
          {state.strategies.map((strategy) => (
            <button
              key={strategy.id}
              className={`strategy-item ${strategy.id === selected?.id ? "active" : ""}`}
              onClick={() => actions.setSelectedStrategyId(strategy.id)}
            >
              <span>{strategy.name}</span>
              <small>{strategy.source === "builtin" ? "内置" : "自定义"}</small>
              {strategy.id === selected?.id ? <Star size={14} /> : null}
            </button>
          ))}
        </div>
        <div className="panel-title">策略参数</div>
        <ParameterForm parameters={selected?.parameters ?? []} values={state.strategyParams} onChange={actions.setStrategyParams} />
        <ToolbarButton icon={<Save size={16} />} variant="primary" onClick={actions.previewSignals}>
          预览信号
        </ToolbarButton>
        <div className="panel-title">策略源码</div>
        {selected?.editable ? (
          <>
            <textarea className="source-editor" value={source} onChange={(event) => setSource(event.currentTarget.value)} />
            <ToolbarButton icon={<Save size={16} />} onClick={saveSource}>
              保存源码
            </ToolbarButton>
          </>
        ) : (
          <p className="caption">内置策略不可直接编辑，可新建用户策略模板后修改。</p>
        )}
      </section>
      <main className="center-stage">
        <div className="command-row">
          <select value={state.settings.symbol} onChange={(event) => actions.setSettings({ ...state.settings, symbol: event.currentTarget.value })}>
            <option>{state.settings.symbol} 沪深A股</option>
          </select>
          <button className="tab-button active">日线</button>
          <button className="tab-button">周线</button>
          <button className="tab-button">月线</button>
          <span className="date-range">{state.settings.start_date} - {state.settings.end_date}</span>
        </div>
        <ChartPanel title="信号标记 · K线回测视图" option={priceOption(state.bars, state.signals?.signals ?? [])} height={360} />
        <ChartPanel title="成交量" option={volumeOption(state.bars)} height={130} />
        <section className="panel">
          <div className="tabs">
            <button className="active">回测结果</button>
            <button>交易明细</button>
            <button>持仓分析</button>
            <button>因子暴露</button>
          </div>
          <MetricStrip
            metrics={[
              { label: "信号数量", value: state.signals?.summary.signals ?? 0 },
              { label: "买入信号", value: state.signals?.summary.buys ?? 0, tone: "positive" },
              { label: "卖出信号", value: state.signals?.summary.sells ?? 0, tone: "negative" },
              { label: "最大回撤", value: `${state.backtest?.metrics.max_drawdown_pct.toFixed(2) ?? "0.00"}%` },
              { label: "累计收益", value: `${state.backtest?.metrics.total_return_pct.toFixed(2) ?? "0.00"}%`, tone: "positive" }
            ]}
          />
          <DataTable rows={(state.signals?.signals ?? []).slice(-12).reverse() as unknown as Record<string, unknown>[]} />
        </section>
      </main>
    </div>
  );
}
