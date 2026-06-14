import ReactECharts from "echarts-for-react";

type Props = {
  title: string;
  option: Record<string, unknown>;
  height?: number;
};

export function ChartPanel({ title, option, height = 300 }: Props) {
  return (
    <section className="panel chart-panel">
      <div className="panel-title">{title}</div>
      {typeof ResizeObserver === "undefined" ? (
        <div className="chart-fallback" style={{ height }}>
          图表区域
        </div>
      ) : (
        <ReactECharts key={chartRevision(option, height)} option={option} style={{ height }} notMerge />
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
