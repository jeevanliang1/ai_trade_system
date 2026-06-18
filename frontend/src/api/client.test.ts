import { ApiError, api, apiRequest } from "./client";
import type { PlatformSettings } from "../types";

beforeEach(() => {
  vi.restoreAllMocks();
});

test("apiRequest raises an ApiError with backend detail", async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 400,
    json: async () => ({ detail: "path must stay under data" })
  }) as unknown as typeof fetch;

  await expect(apiRequest("/api/data/load")).rejects.toEqual(new ApiError(400, "path must stay under data"));
});

test("paperEvents fetches the encoded paper event log path", async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ events: [], orders: [], equity: [], summary: null })
  }) as unknown as typeof fetch;

  await api.paperEvents("logs/paper events.jsonl");

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/paper/events?path=logs%2Fpaper%20events.jsonl",
    expect.objectContaining({
      headers: expect.objectContaining({ "Content-Type": "application/json" })
    })
  );
});

test("previewResearchSignals posts settings with default research windows", async () => {
  const settings: PlatformSettings = {
    symbol: "000001",
    exchange: "SZSE",
    start_date: "20240101",
    end_date: "20241231",
    adjust: "qfq",
    csv_path: "data/000001_daily.csv",
    log_path: "logs/paper_events.jsonl",
    initial_cash: 100000,
    commission_rate: 0.0003,
    slippage: 0.01,
    max_order_cash: 50000,
    max_drawdown_pct: 20,
    min_cash_balance: 0,
    max_position_shares: 50000,
    risk_enabled: true,
    stop_loss_mode: "fixed_pct"
  };
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ symbol: "000001", exchange: "SZSE", start: null, end: null, bars: 0, signals: [], blockers: [], score: {} })
  }) as unknown as typeof fetch;

  await api.previewResearchSignals(settings);

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/research/signals/preview",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ settings, min_bars: 60, lookback: 120 })
    })
  );
});

test("batchResearchSignals posts batch scan options", async () => {
  const settings: PlatformSettings = {
    symbol: "000001",
    exchange: "SZSE",
    start_date: "20240101",
    end_date: "20241231",
    adjust: "qfq",
    csv_path: "data/000001_daily.csv",
    log_path: "logs/paper_events.jsonl",
    initial_cash: 100000,
    commission_rate: 0.0003,
    slippage: 0.01,
    max_order_cash: 50000,
    max_drawdown_pct: 20,
    min_cash_balance: 0,
    max_position_shares: 50000,
    risk_enabled: true,
    stop_loss_mode: "fixed_pct"
  };
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ query: "平安", universe: "catalog", scanned: 0, available: 0, missing: 0, rows: [] })
  }) as unknown as typeof fetch;

  await api.batchResearchSignals(settings, { query: "平安", limit: 8, min_bars: 40, lookback: 80, universe: "local_csv" });

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/research/signals/batch",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ settings, query: "平安", limit: 8, min_bars: 40, lookback: 80, universe: "local_csv" })
    })
  );
});
