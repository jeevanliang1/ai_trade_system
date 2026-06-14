import ReactECharts from "echarts-for-react";
import * as echarts from "echarts";
import type { ReactNode } from "react";

type Props = {
  title: string;
  option: Record<string, unknown>;
  height?: number;
  toolbar?: ReactNode;
  group?: string;
};

export function ChartPanel({ title, option, height = 300, toolbar, group }: Props) {
  const connectChart = (chart: { group?: string }) => {
    if (!group) return;
    chart.group = group;
    echarts.connect(group);
  };

  return (
    <section className="panel chart-panel" aria-label={`${title} 图表`} data-chart-group={group}>
      <div className="panel-title chart-title-row">
        <span>{title}</span>
        {toolbar ? <div className="chart-toolbar">{toolbar}</div> : null}
      </div>
      {typeof ResizeObserver === "undefined" ? (
        <div className="chart-fallback" style={{ height }}>
          图表区域
        </div>
      ) : (
        <ReactECharts key={chartRevision(option, height)} option={option} style={{ height }} notMerge onChartReady={connectChart} />
      )}
    </section>
  );
}

function chartRevision(option: Record<string, unknown>, height: number) {
  const xAxis = option.xAxis as { data?: unknown[] } | undefined;
  const series = option.series as Array<{ data?: unknown[] }> | undefined;
  const xCount = Array.isArray(xAxis?.data) ? xAxis.data.length : 0;
  const seriesCounts = Array.isArray(series) ? series.map((item) => (Array.isArray(item.data) ? item.data.length : 0)).join(",") : "";
  return `${height}:${xCount}:${seriesCounts}`;
}
