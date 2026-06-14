import type { BacktestResponse, Bar, SignalRow } from "../types";

export function priceOption(bars: Bar[], signals: SignalRow[] = []) {
  const rows = signals;
  const start = visibleRangeStart(bars.length);
  return {
    animation: false,
    legend: { top: 0, right: 8, textStyle: { color: "#667085" } },
    grid: { left: 42, right: 18, top: 24, bottom: 28 },
    tooltip: { trigger: "axis" },
    dataZoom: [
      { type: "inside", start, end: 100 },
      { type: "slider", show: false, start, end: 100 }
    ],
    xAxis: { type: "category", data: bars.map((bar) => bar.trading_day), axisLabel: { color: "#667085" } },
    yAxis: { type: "value", scale: true, axisLabel: { color: "#667085" }, splitLine: { lineStyle: { color: "#edf1f7" } } },
    series: [
      {
        type: "candlestick",
        name: "K线",
        data: bars.map((bar) => [bar.open_price, bar.close_price, bar.low_price, bar.high_price]),
        barWidth: 4,
        barMinWidth: 2,
        barMaxWidth: 8,
        itemStyle: { color: "#ef4444", color0: "#16a34a", borderColor: "#ef4444", borderColor0: "#16a34a", borderWidth: 1 }
      },
      {
        type: "line",
        name: "MA20",
        data: movingAverage(bars, 20),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: "#2563eb" }
      },
      {
        type: "line",
        name: "MA60",
        data: movingAverage(bars, 60),
        smooth: true,
        showSymbol: false,
        lineStyle: { width: 1.2, color: "#d97706" }
      },
      {
        type: "scatter",
        name: "买入",
        data: rows.filter((row) => row.action === "buy").map((row) => [row.trading_day, row.price]),
        symbol: "triangle",
        symbolSize: 9,
        itemStyle: { color: "#059669" }
      },
      {
        type: "scatter",
        name: "卖出",
        data: rows.filter((row) => row.action === "sell").map((row) => [row.trading_day, row.price]),
        symbol: "triangle",
        symbolRotate: 180,
        symbolSize: 9,
        itemStyle: { color: "#dc2626" }
      }
    ]
  };
}

function movingAverage(bars: Bar[], window: number) {
  return bars.map((_, index) => {
    if (index + 1 < window) return null;
    const slice = bars.slice(index + 1 - window, index + 1);
    const sum = slice.reduce((total, bar) => total + bar.close_price, 0);
    return Number((sum / window).toFixed(2));
  });
}

export function volumeOption(bars: Bar[]) {
  const start = visibleRangeStart(bars.length);
  return {
    animation: false,
    grid: { left: 42, right: 18, top: 16, bottom: 24 },
    tooltip: { trigger: "axis" },
    dataZoom: [
      { type: "inside", start, end: 100 },
      { type: "slider", show: false, start, end: 100 }
    ],
    xAxis: { type: "category", data: bars.map((bar) => bar.trading_day), axisLabel: { show: false } },
    yAxis: { type: "value", min: 0, splitLine: { lineStyle: { color: "#edf1f7" } } },
    series: [{ type: "bar", data: bars.map((bar) => bar.volume), barWidth: 4, barMinWidth: 2, barMaxWidth: 8, itemStyle: { color: "#64748b", opacity: 0.72 } }]
  };
}

function visibleRangeStart(length: number) {
  if (length <= 140) return 0;
  return Math.round((1 - 140 / length) * 100);
}

export function equityOption(result: BacktestResponse | null) {
  const equity = result?.equity_curve ?? [];
  return {
    grid: { left: 42, right: 18, top: 18, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: equity.map((point) => point.trading_day), axisLabel: { color: "#667085" } },
    yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: "#edf1f7" } } },
    series: [{ type: "line", name: "权益", smooth: true, data: equity.map((point) => point.equity), color: "#2563eb" }]
  };
}

export function drawdownOption(result: BacktestResponse | null) {
  const drawdowns = result?.drawdowns ?? [];
  return {
    grid: { left: 42, right: 18, top: 18, bottom: 24 },
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: drawdowns.map((point) => point.trading_day), axisLabel: { color: "#667085" } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#edf1f7" } } },
    series: [{ type: "line", name: "回撤", areaStyle: {}, data: drawdowns.map((point) => point.drawdown_pct), color: "#ef4444" }]
  };
}
