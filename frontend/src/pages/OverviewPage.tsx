import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { equityOption, priceOption } from "./chartOptions";
import type { PageProps } from "./pageTypes";

export function OverviewPage({ state }: PageProps) {
  return (
    <div className="page-grid overview-grid">
      <section className="panel wide">
        <div className="panel-title">平台总览</div>
        <MetricStrip
          metrics={[
            { label: "K线数量", value: state.bars.length },
            { label: "最新交易日", value: state.bars.at(-1)?.trading_day ?? "-" },
            { label: "策略数量", value: state.strategies.length },
            { label: "纸面事件", value: state.paper?.events.length ?? 0 },
            { label: "AI观点", value: state.insight?.direction ?? "未生成" }
          ]}
        />
      </section>
      <ChartPanel title="行情概览" option={priceOption(state.bars, state.signals?.signals ?? [])} height={360} />
      <ChartPanel title="最近资金曲线" option={equityOption(state.backtest)} height={360} />
      <section className="panel">
        <div className="panel-title">数据健康</div>
        <DataTable
          rows={[
            { 项目: "CSV路径", 状态: state.settings.csv_path },
            { 项目: "股票", 状态: state.settings.symbol },
            { 项目: "交易所", 状态: state.settings.exchange },
            { 项目: "行数", 状态: state.bars.length }
          ]}
        />
      </section>
    </div>
  );
}
