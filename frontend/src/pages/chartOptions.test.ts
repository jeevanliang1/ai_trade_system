import { priceOption, volumeOption } from "./chartOptions";
import type { Bar } from "../types";

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

test("volumeOption renders visible volume bars from zero baseline", () => {
  const option = volumeOption(bars);
  const series = option.series as Array<Record<string, unknown>>;
  const yAxis = option.yAxis as Record<string, unknown>;

  expect(yAxis.min).toBe(0);
  expect(series[0].type).toBe("bar");
  expect(series[0].barWidth).toBeGreaterThanOrEqual(4);
  expect(option.animation).toBe(false);
});
