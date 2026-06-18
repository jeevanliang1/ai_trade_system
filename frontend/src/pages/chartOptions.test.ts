import { drawdownOption, priceOption, volumeOption } from "./chartOptions";
import type { BacktestResponse, Bar, ResearchSignalChanStructure, SignalRow } from "../types";

const bars: Bar[] = [
  {
    symbol: "000001",
    exchange: "SZSE",
    trading_day: "2024-01-02",
    open_price: 10,
    close_price: 11,
    low_price: 9.8,
    high_price: 11.2,
    volume: 1000,
    turnover: 10500
  },
  {
    symbol: "000001",
    exchange: "SZSE",
    trading_day: "2024-01-03",
    open_price: 11,
    close_price: 10.5,
    low_price: 10.2,
    high_price: 11.1,
    volume: 1200,
    turnover: 12800
  }
];

test("priceOption renders A-share candlesticks with MA overlays", () => {
  const option = priceOption(bars);
  const series = option.series as Array<Record<string, unknown>>;
  const dataZoom = option.dataZoom as Array<Record<string, unknown>>;
  const candlestick = series[0] as {
    type: string;
    data: number[][];
    itemStyle: Record<string, string>;
    barWidth: number;
    barMinWidth: number;
  };

  expect(candlestick.type).toBe("candlestick");
  expect(candlestick.data[0]).toEqual([10, 11, 9.8, 11.2]);
  expect(candlestick.itemStyle.color).toBe("#ef4444");
  expect(candlestick.itemStyle.color0).toBe("#16a34a");
  expect(candlestick.barWidth).toBeGreaterThanOrEqual(4);
  expect(candlestick.barMinWidth).toBeGreaterThanOrEqual(2);
  expect(series.map((item) => item.name)).toContain("MA20");
  expect(series.map((item) => item.name)).toContain("MA60");
  expect(dataZoom[0].type).toBe("inside");
  expect(dataZoom[0].start).toBe(0);
  expect(option.animation).toBe(false);
});

test("priceOption renders buy and sell markers with tooltip detail payloads", () => {
  const signals: SignalRow[] = [
    {
      trading_day: "2024-01-02",
      action: "buy",
      symbol: "000001",
      price: 10.8,
      volume: 100,
      reason: "fast MA crossed above slow MA"
    },
    {
      trading_day: "2024-01-03",
      action: "sell",
      symbol: "000001",
      price: 10.4,
      volume: 100,
      reason: "fast MA crossed below slow MA"
    }
  ];

  const option = priceOption(bars, signals);
  const series = option.series as Array<Record<string, unknown>>;
  const buySeries = series.find((item) => item.name === "买入") as {
    data: Array<Record<string, unknown> & { value: [string, number] }>;
    symbol: string;
    symbolSize: number;
    itemStyle: Record<string, string>;
  };
  const sellSeries = series.find((item) => item.name === "卖出") as {
    data: Array<Record<string, unknown> & { value: [string, number] }>;
    symbol: string;
    symbolRotate: number;
    symbolSize: number;
    itemStyle: Record<string, string>;
  };

  expect(buySeries.symbol).toBe("triangle");
  expect(sellSeries.symbolRotate).toBe(180);
  expect(buySeries.symbolSize).toBeGreaterThanOrEqual(12);
  expect(sellSeries.symbolSize).toBeGreaterThanOrEqual(12);
  expect(buySeries.itemStyle.color).toBe("#facc15");
  expect(sellSeries.itemStyle.color).toBe("#a855f7");
  expect(buySeries.data[0].value).toEqual(["2024-01-02", expect.any(Number)]);
  expect(buySeries.data[0].value[1]).toBeLessThan(bars[0].low_price);
  expect(sellSeries.data[0].value).toEqual(["2024-01-03", expect.any(Number)]);
  expect(sellSeries.data[0].value[1]).toBeGreaterThan(bars[1].high_price);
  expect(buySeries.data[0]).toMatchObject({
    name: "买入 000001",
    tradePrice: 10.8,
    reason: "fast MA crossed above slow MA",
    volume: 100
  });
  expect(typeof buySeries.data[0].tooltip).toBe("object");
});

test("priceOption renders Chan structure overlay series", () => {
  const chanStructure = {
    fractal_count: 2,
    stroke_count: 1,
    pivot_count: 1,
    latest_signal_kind: "CHAN_STRUCT_BUY_T3",
    latest_signal_title: "缠论三买",
    fractals: [
      { index: 0, trading_day: "2024-01-02", kind: "bottom", price: 9.8, high: 11.2, low: 9.8 },
      { index: 1, trading_day: "2024-01-03", kind: "top", price: 11.1, high: 11.1, low: 10.2 }
    ],
    strokes: [
      {
        direction: "up",
        start_index: 0,
        end_index: 1,
        start_day: "2024-01-02",
        end_day: "2024-01-03",
        start_price: 9.8,
        end_price: 11.1,
        high: 11.1,
        low: 9.8
      }
    ],
    segments: [
      {
        direction: "up",
        start_index: 0,
        end_index: 1,
        start_stroke_index: 0,
        end_stroke_index: 2,
        break_stroke_index: null,
        start_day: "2024-01-02",
        end_day: "2024-01-03",
        start_price: 9.8,
        end_price: 11.1,
        high: 11.1,
        low: 9.8,
        stroke_count: 3,
        energy: 0.65,
        broken_by_next: false
      }
    ],
    pivots: [{ start_index: 0, end_index: 1, start_day: "2024-01-02", end_day: "2024-01-03", low: 10.1, high: 10.8 }],
    recursive_pivots: [
      {
        level: "segment",
        start_index: 0,
        end_index: 1,
        start_day: "2024-01-02",
        end_day: "2024-01-03",
        low: 10.2,
        high: 10.7,
        direction: "up",
        component_count: 3
      }
    ],
    divergences: [
      {
        kind: "top",
        action: "sell",
        start_index: 0,
        end_index: 1,
        reference_start_index: 0,
        reference_end_index: 1,
        reference_energy: 0.8,
        current_energy: 0.65,
        price_extreme: 11.1,
        base_score: 48,
        macd_strength: 8,
        volume_strength: 5,
        confirmation_score: 66,
        macd_reference: 0.12,
        macd_current: 0.08,
        volume_reference: 2400,
        volume_current: 1200
      }
    ],
    signals: [
      {
        trading_day: "2024-01-03",
        symbol: "000001",
        exchange: "SZSE",
        kind: "CHAN_STRUCT_BUY_T3",
        action: "buy",
        price: 10.8,
        strength: 0.78,
        score: 44,
        title: "缠论三买",
        reason: "向上离开中枢后的回抽未跌回中枢上沿",
        tags: ["chan", "structure"]
      }
    ]
  } as unknown as ResearchSignalChanStructure;

  const option = (priceOption as (inputBars: Bar[], inputSignals: SignalRow[], structure: ResearchSignalChanStructure) => ReturnType<typeof priceOption>)(
    bars,
    [],
    chanStructure
  );
  const series = option.series as Array<Record<string, unknown>>;
  const pivotSeries = series.find((item) => item.name === "缠论中枢") as { markArea?: { data: unknown[] } };
  const recursivePivotSeries = series.find((item) => item.name === "递归中枢") as { markArea?: { data: unknown[] } };

  expect(series.map((item) => item.name)).toEqual(expect.arrayContaining(["顶分型", "底分型", "缠论笔", "缠论线段", "缠论中枢", "递归中枢", "结构买点"]));
  expect(pivotSeries.markArea?.data).toHaveLength(1);
  expect(recursivePivotSeries.markArea?.data).toHaveLength(1);
});

test("volumeOption renders visible volume bars from zero baseline", () => {
  const option = volumeOption(bars);
  const series = option.series as Array<Record<string, unknown>>;
  const yAxis = option.yAxis as Record<string, unknown>;

  expect(yAxis.min).toBe(0);
  expect(series[0].type).toBe("bar");
  expect(series[0].barWidth).toBeGreaterThanOrEqual(4);
  expect(option.animation).toBe(false);
});

test("price and volume options keep matching visible windows", () => {
  const longBars = Array.from({ length: 200 }, (_, index) => ({
    ...bars[0],
    trading_day: `2024-01-${String(index + 1).padStart(2, "0")}`,
    close_price: 10 + index
  }));

  const priceZoom = priceOption(longBars).dataZoom as Array<Record<string, unknown>>;
  const volumeZoom = volumeOption(longBars).dataZoom as Array<Record<string, unknown>>;

  expect(volumeZoom[0].start).toBe(priceZoom[0].start);
  expect(volumeZoom[0].end).toBe(priceZoom[0].end);
});

test("drawdownOption renders red underwater area with synchronized zoom", () => {
  const result: BacktestResponse = {
    bars: [],
    metrics: {
      final_equity: 100000,
      total_return_pct: 0,
      annualized_return_pct: 0,
      benchmark_return_pct: 0,
      excess_return_pct: 0,
      annual_volatility_pct: 0,
      sharpe_ratio: null,
      max_drawdown_pct: -3,
      trade_count: 0,
      win_rate_pct: null,
      profit_factor: null,
      exposure_pct: 0
    },
    equity_curve: [],
    drawdowns: [{ trading_day: "2024-01-02", equity: 100000, drawdown_pct: -3 }],
    trades: [],
    risk_status: { ok: true, warnings: [], enabled: true }
  };

  const option = drawdownOption(result);
  const dataZoom = option.dataZoom as Array<Record<string, unknown>>;
  const series = option.series as Array<Record<string, unknown>>;

  expect(option.animation).toBe(false);
  expect(dataZoom[0].type).toBe("inside");
  expect(series[0]).toMatchObject({ type: "line", name: "回撤" });
  expect(series[0].color).toBe("#dc2626");
});
