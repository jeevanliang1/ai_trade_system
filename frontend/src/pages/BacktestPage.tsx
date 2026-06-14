import { Play } from "lucide-react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { SegmentedControl } from "../components/SegmentedControl";
import { ToolbarButton } from "../components/ToolbarButton";
import type { BacktestResponse } from "../types";
import { drawdownOption, equityOption, priceOption } from "./chartOptions";
import type { PageProps } from "./pageTypes";
import { useState } from "react";

export function BacktestPage({ state, actions }: PageProps) {
  const [mode, setMode] = useState<"single" | "portfolio">("single");
  return (
    <div className="page-grid">
      <section className="panel side-panel">
        <div className="panel-title">回测设置</div>
        <SegmentedControl
          value={mode}
          onChange={setMode}
          options={[
            { label: "单策略", value: "single" },
            { label: "组合策略", value: "portfolio" }
          ]}
        />
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
        <ToolbarButton icon={<Play size={16} />} variant="success" onClick={() => actions.runBacktest(mode)}>
          运行回测
        </ToolbarButton>
      </section>
      <BacktestResultPanel result={state.backtest} />
    </div>
  );
}

export function BacktestResultPanel({ result }: { result: BacktestResponse | null }) {
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
      <ChartPanel title="资金曲线" option={equityOption(result)} height={260} />
      <ChartPanel title="回撤曲线" option={drawdownOption(result)} height={220} />
      <ChartPanel title="买卖点" option={priceOption(result?.bars ?? [])} height={320} />
      <section className="panel">
        <div className="panel-title">交易明细</div>
        <DataTable rows={(result?.trades ?? []) as unknown as Record<string, unknown>[]} />
      </section>
    </section>
  );
}
