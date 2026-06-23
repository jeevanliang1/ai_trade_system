import type { BacktestResponse, Bar, ChanFractalOverlay, ResearchSignal, ResearchSignalChanStructure, SignalRow } from "../types";

export function priceOption(bars: Bar[], signals: SignalRow[] = [], chanStructure: ResearchSignalChanStructure | null = null) {
  const start = visibleRangeStart(bars.length);
  const barsByDay = new Map(bars.flatMap((bar) => [[bar.trading_day, bar], [bar.timestamp ?? bar.trading_day, bar]]));
  const markerOffset = signalMarkerOffset(bars);
  const xValues = bars.map((bar) => barX(bar));
  return {
    animation: false,
    legend: { top: 0, right: 8, textStyle: { color: "#667085" } },
    grid: { left: 42, right: 18, top: 24, bottom: 28 },
    tooltip: { trigger: "axis" },
    dataZoom: [
      { type: "inside", start, end: 100 },
      { type: "slider", show: false, start, end: 100 }
    ],
    xAxis: { type: "category", data: xValues, axisLabel: { color: "#667085" } },
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
        data: signals.filter((row) => row.action === "buy").map((row) => signalMarker(row, "买入", "buy", barsByDay.get(row.trading_day), markerOffset)),
        symbol: "triangle",
        symbolSize: 13,
        z: 5,
        itemStyle: { color: "#facc15", borderColor: "#854d0e", borderWidth: 1 }
      },
      {
        type: "scatter",
        name: "卖出",
        data: signals.filter((row) => row.action === "sell").map((row) => signalMarker(row, "卖出", "sell", barsByDay.get(row.trading_day), markerOffset)),
        symbol: "triangle",
        symbolRotate: 180,
        symbolSize: 13,
        z: 5,
        itemStyle: { color: "#a855f7", borderColor: "#581c87", borderWidth: 1 }
      },
      ...chanStructureSeries(chanStructure, barsByDay, markerOffset)
    ]
  };
}

function barX(bar: Bar): string {
  return bar.timestamp ?? bar.trading_day;
}

function chanStructureSeries(chanStructure: ResearchSignalChanStructure | null, barsByDay: Map<string, Bar>, markerOffset: number) {
  if (!chanStructure) return [];
  const fractals = chanStructure.fractals ?? [];
  const strokes = chanStructure.strokes ?? [];
  const pivots = chanStructure.pivots ?? [];
  const segments = chanStructure.segments ?? [];
  const recursivePivots = chanStructure.recursive_pivots ?? [];
  const segmentLevelPivots = recursivePivots.filter((pivot) => pivot.level === "segment");
  const structureSignals = chanStructure.signals ?? [];
  return [
    {
      type: "scatter",
      name: "顶分型",
      data: fractals.filter((fractal) => fractal.kind === "top").map((fractal) => fractalMarker(fractal, "顶分型")),
      symbol: "triangle",
      symbolRotate: 180,
      symbolSize: 10,
      z: 6,
      itemStyle: { color: "#f97316", borderColor: "#9a3412", borderWidth: 1 }
    },
    {
      type: "scatter",
      name: "底分型",
      data: fractals.filter((fractal) => fractal.kind === "bottom").map((fractal) => fractalMarker(fractal, "底分型")),
      symbol: "triangle",
      symbolSize: 10,
      z: 6,
      itemStyle: { color: "#0ea5e9", borderColor: "#075985", borderWidth: 1 }
    },
    {
      type: "line",
      name: "缠论笔",
      data: strokes.flatMap((stroke) => [
        [stroke.start_day, stroke.start_price],
        [stroke.end_day, stroke.end_price],
        null
      ]),
      showSymbol: false,
      connectNulls: false,
      z: 4,
      lineStyle: { width: 1.4, color: "#475467", type: "dashed" }
    },
    {
      type: "line",
      name: "缠论线段",
      data: segments.flatMap((segment) => [
        [segment.start_day, segment.start_price],
        [segment.end_day, segment.end_price],
        null
      ]),
      showSymbol: false,
      connectNulls: false,
      z: 5,
      lineStyle: { width: 2, color: "#0f766e" }
    },
    {
      type: "line",
      name: "缠论中枢",
      data: [],
      showSymbol: false,
      markArea: {
        silent: true,
        itemStyle: { color: "rgba(22, 119, 255, 0.1)", borderColor: "rgba(22, 119, 255, 0.35)", borderWidth: 1 },
        data: pivots.map((pivot) => [
          { name: "中枢", xAxis: pivot.start_day, yAxis: pivot.low },
          { xAxis: pivot.end_day, yAxis: pivot.high }
        ])
      }
    },
    {
      type: "line",
      name: "递归中枢",
      data: [],
      showSymbol: false,
      markArea: {
        silent: true,
        itemStyle: { color: "rgba(15, 118, 110, 0.12)", borderColor: "rgba(15, 118, 110, 0.42)", borderWidth: 1 },
        data: (segmentLevelPivots.length > 0 ? segmentLevelPivots : recursivePivots).map((pivot) => [
          { name: "递归中枢", xAxis: pivot.start_day, yAxis: pivot.low },
          { xAxis: pivot.end_day, yAxis: pivot.high }
        ])
      }
    },
    {
      type: "scatter",
      name: "结构买点",
      data: structureSignals
        .filter((signal) => signal.action === "buy")
        .map((signal) => structureSignalMarker(signal, "结构买点", "buy", barsByDay.get(signal.trading_day), markerOffset)),
      symbol: "diamond",
      symbolSize: 13,
      z: 7,
      itemStyle: { color: "#22c55e", borderColor: "#166534", borderWidth: 1 }
    },
    {
      type: "scatter",
      name: "结构卖点",
      data: structureSignals
        .filter((signal) => signal.action === "sell")
        .map((signal) => structureSignalMarker(signal, "结构卖点", "sell", barsByDay.get(signal.trading_day), markerOffset)),
      symbol: "diamond",
      symbolSize: 13,
      z: 7,
      itemStyle: { color: "#ef4444", borderColor: "#991b1b", borderWidth: 1 }
    }
  ];
}

function fractalMarker(fractal: ChanFractalOverlay, label: string) {
  return {
    name: `${label} ${fractal.trading_day}`,
    value: [fractal.trading_day, fractal.price],
    high: fractal.high,
    low: fractal.low,
    tooltip: {
      formatter: [`${label}`, `日期：${fractal.trading_day}`, `价格：${fractal.price}`].join("<br/>")
    }
  };
}

function structureSignalMarker(signal: ResearchSignal, label: string, action: SignalRow["action"], bar: Bar | undefined, offset: number) {
  const markerPrice = bar ? signalMarkerPrice(bar, action, offset) : signal.price;
  return {
    name: `${label} ${signal.title}`,
    value: [signal.trading_day, markerPrice],
    tradePrice: signal.price,
    strength: signal.strength,
    score: signal.score,
    reason: signal.reason,
    tooltip: {
      formatter: [
        `${label} ${signal.title}`,
        `日期：${signal.trading_day}`,
        `价格：${signal.price}`,
        `强度：${Math.round(signal.strength * 100)}%`,
        `原因：${signal.reason}`
      ].join("<br/>")
    }
  };
}

function signalMarker(row: SignalRow, label: string, action: SignalRow["action"], bar: Bar | undefined, offset: number) {
  const markerPrice = bar ? signalMarkerPrice(bar, action, offset) : row.price;
  return {
    name: `${label} ${row.symbol}`,
    value: [row.trading_day, markerPrice],
    stockSymbol: row.symbol,
    tradePrice: row.price,
    volume: row.volume,
    reason: row.reason,
    tooltip: {
      formatter: [
        `${label} ${row.symbol}`,
        `日期：${row.trading_day}`,
        `价格：${row.price}`,
        `数量：${row.volume}`,
        `原因：${row.reason}`
      ].join("<br/>")
    }
  };
}

function signalMarkerPrice(bar: Bar, action: SignalRow["action"], offset: number) {
  return Number((action === "buy" ? bar.low_price - offset : bar.high_price + offset).toFixed(4));
}

function signalMarkerOffset(bars: Bar[]) {
  if (bars.length === 0) return 0;
  const lows = bars.map((bar) => bar.low_price);
  const highs = bars.map((bar) => bar.high_price);
  const range = Math.max(...highs) - Math.min(...lows);
  return Math.max(range * 0.018, 0.01);
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
  const start = visibleRangeStart(drawdowns.length);
  return {
    animation: false,
    grid: { left: 42, right: 18, top: 18, bottom: 24 },
    tooltip: { trigger: "axis" },
    dataZoom: [
      { type: "inside", start, end: 100 },
      { type: "slider", show: false, start, end: 100 }
    ],
    xAxis: { type: "category", data: drawdowns.map((point) => point.trading_day), axisLabel: { color: "#667085" } },
    yAxis: { type: "value", splitLine: { lineStyle: { color: "#edf1f7" } }, axisLabel: { formatter: "{value}%" } },
    series: [
      {
        type: "line",
        name: "回撤",
        smooth: true,
        showSymbol: false,
        areaStyle: { color: "rgba(220, 38, 38, 0.14)" },
        data: drawdowns.map((point) => point.drawdown_pct),
        color: "#dc2626"
      }
    ]
  };
}
