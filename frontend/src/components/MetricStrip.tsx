type Metric = {
  label: string;
  value: string | number;
  delta?: string;
  tone?: "positive" | "negative" | "neutral";
};

export function MetricStrip({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="metric-strip">
      {metrics.map((metric) => (
        <div className="metric" key={metric.label}>
          <span>{metric.label}</span>
          <strong className={metric.tone ?? "neutral"}>{metric.value}</strong>
          {metric.delta ? <small>{metric.delta}</small> : null}
        </div>
      ))}
    </div>
  );
}
