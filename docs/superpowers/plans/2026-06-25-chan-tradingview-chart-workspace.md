# Chan TradingView-Style Chart Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated `缠论图表` React workspace that renders K-line/volume data with Chan overlays, layer toggles, fullscreen expansion, drag/zoom/pan interaction, timeframe switching, and a structure inspector.

**Architecture:** Reuse the existing React platform state, `ChartPanel`, ECharts chart options, watchlist stock selection, `actions.loadData`, and `actions.previewResearchSignals`. Keep the MVP frontend-only over existing API contracts; backend route changes are not required unless implementation proves a real data contract gap.

**Tech Stack:** React 19, TypeScript, Vite, Vitest, Testing Library, ECharts, echarts-for-react, FastAPI existing endpoints.

---

## File Map

- Modify: `frontend/src/pages/chartOptions.ts`
  - Add a small layer-filter option to `priceOption` while keeping existing callers compatible.
- Modify: `frontend/src/pages/chartOptions.test.ts`
  - Pin layer-filter behavior for Chan overlay visibility.
- Create: `frontend/src/pages/ChanChartPage.tsx`
  - New page component for the dedicated Chan chart workspace.
- Create: `frontend/src/pages/ChanChartPage.test.tsx`
  - Unit tests for controls, layer toggles, fullscreen state, timeframe switching, and inspector rendering.
- Modify: `frontend/src/pages/pageTypes.ts`
  - Add a page action for timeframe changes if the page should not duplicate `managedCsvPath` logic.
- Modify: `frontend/src/shell/AppShell.tsx`
  - Add navigation item, page routing, and a focused `setTimeframe` action that updates the canonical managed CSV path and clears stale data.
- Modify: `frontend/src/shell/AppShell.test.tsx`
  - Assert the new navigation item is present and reachable.
- Modify: `frontend/src/styles.css`
  - Add dense chart-workspace layout, fullscreen CSS expansion, layer toolbar, and responsive behavior.
- Update after implementation: `docs/context/pending-features.md`
  - Remove the completed MVP pending item and set the next recommendation to manual drawing persistence, unless the implementation exposes a higher-priority chart follow-up.
- Create after browser QA: `docs/qa/2026-06-25-chan-chart-workspace-qa.md`
  - Record screenshots, commands, and any browser/runtime limitations.

---

## Task 1: Add Chart Layer Filtering

**Files:**
- Modify: `frontend/src/pages/chartOptions.test.ts`
- Modify: `frontend/src/pages/chartOptions.ts`

- [ ] **Step 1: Write the failing test**

Append this test to `frontend/src/pages/chartOptions.test.ts` after the existing Chan overlay test:

```typescript
test("priceOption can filter Chan overlay layers for a dedicated chart workspace", () => {
  const chanStructure = {
    fractal_count: 2,
    stroke_count: 1,
    pivot_count: 1,
    segment_count: 1,
    recursive_pivot_count: 1,
    divergence_count: 1,
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
        level: "segment",
        sequence_index: 0,
        lineage_id: "segment-0",
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
        volume_current: 1200,
        pivot_level: "segment",
        pivot_start_index: 0,
        pivot_end_index: 1,
        pivot_low: 10.1,
        pivot_high: 10.8
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

  const option = priceOption(bars, [], chanStructure, {
    layers: {
      fractals: false,
      strokes: true,
      segments: false,
      pivots: true,
      recursivePivots: false,
      divergences: false,
      structureSignals: true,
      movingAverages: true,
      tradeSignals: true
    }
  });
  const names = (option.series as Array<Record<string, unknown>>).map((series) => series.name);

  expect(names).toContain("K线");
  expect(names).toContain("MA20");
  expect(names).toContain("缠论笔");
  expect(names).toContain("缠论中枢");
  expect(names).toContain("结构买点");
  expect(names).not.toContain("顶分型");
  expect(names).not.toContain("底分型");
  expect(names).not.toContain("缠论线段");
  expect(names).not.toContain("递归中枢");
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd frontend && npm test -- src/pages/chartOptions.test.ts
```

Expected: FAIL with a TypeScript or assertion failure because `priceOption` does not accept the fourth layer-filter argument yet.

- [ ] **Step 3: Implement layer filtering**

Modify `frontend/src/pages/chartOptions.ts`:

```typescript
export type PriceOptionLayers = {
  movingAverages?: boolean;
  tradeSignals?: boolean;
  fractals?: boolean;
  strokes?: boolean;
  segments?: boolean;
  pivots?: boolean;
  recursivePivots?: boolean;
  divergences?: boolean;
  structureSignals?: boolean;
};

export type PriceOptionConfig = {
  layers?: PriceOptionLayers;
};

const DEFAULT_PRICE_LAYERS: Required<PriceOptionLayers> = {
  movingAverages: true,
  tradeSignals: true,
  fractals: true,
  strokes: true,
  segments: true,
  pivots: true,
  recursivePivots: true,
  divergences: true,
  structureSignals: true
};
```

Change the function signature:

```typescript
export function priceOption(
  bars: Bar[],
  signals: SignalRow[] = [],
  chanStructure: ResearchSignalChanStructure | null = null,
  config: PriceOptionConfig = {}
) {
  const layers = { ...DEFAULT_PRICE_LAYERS, ...(config.layers ?? {}) };
```

Build `series` as an array and push optional layers:

```typescript
  const series: Array<Record<string, unknown>> = [
    {
      type: "candlestick",
      name: "K线",
      data: bars.map((bar) => [bar.open_price, bar.close_price, bar.low_price, bar.high_price]),
      barWidth: 4,
      barMinWidth: 2,
      barMaxWidth: 8,
      itemStyle: { color: "#ef4444", color0: "#16a34a", borderColor: "#ef4444", borderColor0: "#16a34a", borderWidth: 1 }
    }
  ];
  if (layers.movingAverages) {
    series.push(
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
      }
    );
  }
  if (layers.tradeSignals) {
    series.push(
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
      }
    );
  }
  series.push(...chanStructureSeries(chanStructure, barsByDay, markerOffset, layers));
```

Return `series` instead of the inline array.

Change `chanStructureSeries` signature:

```typescript
function chanStructureSeries(
  chanStructure: ResearchSignalChanStructure | null,
  barsByDay: Map<string, Bar>,
  markerOffset: number,
  layers: Required<PriceOptionLayers> = DEFAULT_PRICE_LAYERS
) {
```

Build the current Chan series array, then filter by series names:

```typescript
  const series = [
    /* existing Chan series objects */
  ];
  return series.filter((item) => {
    if ((item.name === "顶分型" || item.name === "底分型") && !layers.fractals) return false;
    if (item.name === "缠论笔" && !layers.strokes) return false;
    if (item.name === "缠论线段" && !layers.segments) return false;
    if (item.name === "缠论中枢" && !layers.pivots) return false;
    if (item.name === "递归中枢" && !layers.recursivePivots) return false;
    if (item.name === "结构买点" && !layers.structureSignals) return false;
    if (item.name === "结构卖点" && !layers.structureSignals) return false;
    return true;
  });
```

If divergence rendering already exists in the local file, include it in the filter. If it is not present, leave the `divergences` flag unused until the page task exposes the current available overlay set.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd frontend && npm test -- src/pages/chartOptions.test.ts
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/chartOptions.ts frontend/src/pages/chartOptions.test.ts
git commit -m "feat: add chart layer filters"
```

---

## Task 2: Build the Chan Chart Page

**Files:**
- Create: `frontend/src/pages/ChanChartPage.test.tsx`
- Create: `frontend/src/pages/ChanChartPage.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/pages/ChanChartPage.test.tsx`:

```typescript
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { ChanChartPage } from "./ChanChartPage";
import type { PageProps } from "./pageTypes";

vi.mock("../components/ChartPanel", () => ({
  ChartPanel: ({ title, toolbar }: { title: string; toolbar?: React.ReactNode }) => (
    <section aria-label={`${title} 图表`}>
      <div>{title}</div>
      {toolbar}
    </section>
  )
}));

const actions: PageProps["actions"] = {
  setSettings: vi.fn(),
  selectStock: vi.fn(),
  setWatchlist: vi.fn(),
  updateWatchlistData: vi.fn(),
  setSelectedStrategyId: vi.fn(),
  setStrategyParams: vi.fn(),
  setPortfolio: vi.fn(),
  refreshStrategies: vi.fn(),
  loadData: vi.fn(),
  demoData: vi.fn(),
  downloadData: vi.fn(),
  previewSignals: vi.fn(),
  previewPortfolio: vi.fn(),
  previewResearchSignals: vi.fn(),
  runBacktest: vi.fn(),
  researchAI: vi.fn(),
  runPaper: vi.fn(),
  loadPaperEvents: vi.fn(),
  evaluateRisk: vi.fn(),
  startRealtimeMonitor: vi.fn(),
  stopRealtimeMonitor: vi.fn(),
  refreshRealtimeMonitor: vi.fn()
};

function makeProps(overrides: Partial<PageProps["state"]> = {}): PageProps {
  return {
    actions,
    state: {
      settings: {
        symbol: "000001",
        exchange: "SZSE",
        start_date: "20240101",
        end_date: "20241231",
        adjust: "qfq",
        timeframe: "daily",
        csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_daily_qfq_latest.csv",
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
      },
      watchlist: [{ code: "000001", name: "平安银行", exchange: "SZSE" }],
      managedData: [],
      strategies: [],
      portfolioPresets: [],
      selectedStrategyId: "",
      strategyParams: {},
      bars: [
        {
          symbol: "000001",
          exchange: "SZSE",
          trading_day: "2024-01-02",
          timeframe: "daily",
          open_price: 10,
          high_price: 11,
          low_price: 9,
          close_price: 10.5,
          volume: 1000,
          turnover: 10500
        }
      ],
      dataSummary: null,
      signals: null,
      researchSignals: {
        symbol: "000001",
        exchange: "SZSE",
        start: "2024-01-02",
        end: "2024-01-02",
        bars: 1,
        signals: [
          {
            trading_day: "2024-01-02",
            symbol: "000001",
            exchange: "SZSE",
            kind: "CHAN_STRUCT_BUY_T3",
            action: "buy",
            price: 10.5,
            strength: 0.8,
            score: 44,
            title: "缠论三买",
            reason: "回抽未跌回中枢",
            tags: ["chan"]
          }
        ],
        score: {
          total_score: 44,
          direction: "bullish",
          confidence: 0.7,
          chan_score: 44,
          rsi_score: 0,
          summary: "缠论三买触发",
          chan_structure: null
        },
        blockers: [],
        chan_structure: {
          fractal_count: 2,
          stroke_count: 1,
          pivot_count: 1,
          segment_count: 1,
          recursive_pivot_count: 1,
          divergence_count: 1,
          latest_signal_kind: "CHAN_STRUCT_BUY_T3",
          latest_signal_title: "缠论三买",
          signals: [
            {
              trading_day: "2024-01-02",
              symbol: "000001",
              exchange: "SZSE",
              kind: "CHAN_STRUCT_BUY_T3",
              action: "buy",
              price: 10.5,
              strength: 0.8,
              score: 44,
              title: "缠论三买",
              reason: "回抽未跌回中枢",
              tags: ["chan"]
            }
          ]
        }
      },
      portfolio: { mode: "weighted_vote", allocations: [] },
      backtest: null,
      insight: null,
      aiPrompt: null,
      riskStatus: { ok: true, warnings: [], enabled: true },
      paper: null,
      realtime: null,
      message: "准备就绪",
      busy: false,
      activeBacktestMode: null,
      activePaperMode: null,
      ...overrides
    }
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

test("renders the dedicated Chan chart workspace with charts and inspector", () => {
  render(<ChanChartPage {...makeProps()} />);

  expect(screen.getByText("缠论图表")).toBeInTheDocument();
  expect(screen.getByLabelText("缠论价格 图表")).toBeInTheDocument();
  expect(screen.getByLabelText("缠论成交量 图表")).toBeInTheDocument();
  expect(screen.getByText("分型 2")).toBeInTheDocument();
  expect(screen.getByText("笔 1")).toBeInTheDocument();
  expect(screen.getByText("线段 1")).toBeInTheDocument();
  expect(screen.getByText("中枢 1")).toBeInTheDocument();
  expect(screen.getByText("最近买卖点")).toBeInTheDocument();
  expect(screen.getByText("缠论三买")).toBeInTheDocument();
});

test("layer toggles and fullscreen controls are interactive", async () => {
  const user = userEvent.setup();
  render(<ChanChartPage {...makeProps()} />);

  await user.click(screen.getByLabelText("显示缠论笔"));
  expect(screen.getByLabelText("显示缠论笔")).not.toBeChecked();

  await user.click(screen.getByRole("button", { name: "全屏图表" }));
  expect(screen.getByRole("region", { name: "缠论图表工作区" })).toHaveClass("fullscreen");
  expect(screen.getByRole("button", { name: "退出全屏" })).toBeInTheDocument();
});

test("timeframe switching updates settings through the page action", async () => {
  const user = userEvent.setup();
  render(<ChanChartPage {...makeProps()} />);

  await user.click(screen.getByRole("button", { name: "60m" }));

  expect(actions.setSettings).toHaveBeenCalledWith(expect.objectContaining({
    timeframe: "60m",
    csv_path: "data/market/a_share/SZSE/000001/000001_SZSE_60m_qfq_latest.csv"
  }));
});

test("analysis buttons call existing load and preview actions", async () => {
  const user = userEvent.setup();
  render(<ChanChartPage {...makeProps()} />);

  await user.click(screen.getByRole("button", { name: "加载K线" }));
  await user.click(screen.getByRole("button", { name: "生成缠论结构" }));

  expect(actions.loadData).toHaveBeenCalled();
  expect(actions.previewResearchSignals).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd frontend && npm test -- src/pages/ChanChartPage.test.tsx
```

Expected: FAIL because `ChanChartPage` does not exist.

- [ ] **Step 3: Implement the page**

Create `frontend/src/pages/ChanChartPage.tsx`:

```typescript
import { Download, Expand, Eye, LocateFixed, Maximize2, RefreshCw, RotateCcw } from "lucide-react";
import { useMemo, useState } from "react";

import { ChartPanel } from "../components/ChartPanel";
import { DataTable } from "../components/DataTable";
import { MetricStrip } from "../components/MetricStrip";
import { StockQuickSelect } from "../components/StockQuickSelect";
import { ToolbarButton } from "../components/ToolbarButton";
import type { PlatformSettings, ResearchSignal } from "../types";
import { priceOption, type PriceOptionLayers, volumeOption } from "./chartOptions";
import type { PageProps } from "./pageTypes";

const TIMEFRAMES = ["daily", "60m", "30m", "15m", "5m", "1m"];
const CHAN_CHART_GROUP = "chan-chart-price-volume";

const DEFAULT_LAYERS: Required<PriceOptionLayers> = {
  movingAverages: true,
  tradeSignals: true,
  fractals: true,
  strokes: true,
  segments: true,
  pivots: true,
  recursivePivots: true,
  divergences: true,
  structureSignals: true
};

export function ChanChartPage({ state, actions }: PageProps) {
  const [layers, setLayers] = useState<Required<PriceOptionLayers>>(DEFAULT_LAYERS);
  const [fullscreen, setFullscreen] = useState(false);
  const chanStructure = state.researchSignals?.chan_structure ?? null;
  const recentPoints = useMemo(() => (chanStructure?.signals ?? []).slice(-8).reverse(), [chanStructure]);
  const price = useMemo(
    () => priceOption(state.bars, state.signals?.signals ?? [], chanStructure, { layers }),
    [state.bars, state.signals, chanStructure, layers]
  );
  const volume = useMemo(() => volumeOption(state.bars), [state.bars]);

  const switchTimeframe = (timeframe: string) => {
    actions.setSettings({
      ...state.settings,
      timeframe,
      csv_path: managedCsvPath(state.settings, timeframe)
    });
  };

  const toggleLayer = (key: keyof PriceOptionLayers) => {
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  };

  return (
    <section className={fullscreen ? "chan-chart-page fullscreen" : "chan-chart-page"} role="region" aria-label="缠论图表工作区">
      <div className="chan-chart-header">
        <div>
          <div className="panel-title">缠论图表</div>
          <p className="caption">K线结构复盘 · 线段/中枢/买卖点</p>
        </div>
        <div className="chan-chart-actions">
          <StockQuickSelect label="缠论图表自选股票" value={state.settings} stocks={state.watchlist} onSelect={actions.selectStock} compact />
          <ToolbarButton icon={<RefreshCw size={15} />} disabled={state.busy} onClick={actions.loadData}>
            加载K线
          </ToolbarButton>
          <ToolbarButton icon={<Eye size={15} />} variant="primary" disabled={state.busy} onClick={actions.previewResearchSignals}>
            生成缠论结构
          </ToolbarButton>
          <ToolbarButton icon={<Download size={15} />} disabled={state.busy} onClick={actions.downloadData}>
            下载数据
          </ToolbarButton>
        </div>
      </div>
      <div className="chan-chart-timeframes" aria-label="K线级别">
        {TIMEFRAMES.map((timeframe) => (
          <button key={timeframe} type="button" className={state.settings.timeframe === timeframe ? "selected" : ""} onClick={() => switchTimeframe(timeframe)}>
            {timeframe}
          </button>
        ))}
      </div>
      <div className="chan-chart-layout">
        <main className="chan-chart-main">
          <ChartPanel
            title="缠论价格"
            option={price}
            height={fullscreen ? 620 : 460}
            group={CHAN_CHART_GROUP}
            toolbar={
              <>
                <button aria-label="重置视图" className="icon-button" onClick={() => setLayers(DEFAULT_LAYERS)}>
                  <RotateCcw size={14} />
                </button>
                <button aria-label="适配视图" className="icon-button" onClick={() => setLayers((current) => ({ ...current }))}>
                  <LocateFixed size={14} />
                </button>
                <button aria-label={fullscreen ? "退出全屏" : "全屏图表"} className="icon-button" onClick={() => setFullscreen((current) => !current)}>
                  {fullscreen ? <Maximize2 size={14} /> : <Expand size={14} />}
                </button>
              </>
            }
          />
          <ChartPanel title="缠论成交量" option={volume} height={fullscreen ? 180 : 140} group={CHAN_CHART_GROUP} />
          <LayerToggles layers={layers} onToggle={toggleLayer} />
        </main>
        <aside className="chan-chart-inspector">
          <MetricStrip
            metrics={[
              { label: "K线", value: state.bars.length },
              { label: "周期", value: state.settings.timeframe },
              { label: "最新收盘", value: state.bars.at(-1)?.close_price.toFixed(2) ?? "-" },
              { label: "综合分", value: state.researchSignals?.score.total_score.toFixed(1) ?? "-" }
            ]}
          />
          <div className="structure-summary" aria-label="缠论结构摘要">
            <span className="legend-chip">分型 {chanStructure?.fractal_count ?? 0}</span>
            <span className="legend-chip">笔 {chanStructure?.stroke_count ?? 0}</span>
            <span className="legend-chip">线段 {chanStructure?.segment_count ?? 0}</span>
            <span className="legend-chip">中枢 {chanStructure?.pivot_count ?? 0}</span>
            <span className="legend-chip">递归 {chanStructure?.recursive_pivot_count ?? 0}</span>
            <span className="legend-chip">背驰 {chanStructure?.divergence_count ?? 0}</span>
          </div>
          {state.researchSignals?.blockers.length ? (
            <div className="parameter-errors" role="alert">
              {state.researchSignals.blockers.map((blocker) => (
                <span key={blocker.code}>{blocker.message}</span>
              ))}
            </div>
          ) : null}
          <div className="panel-title">最近买卖点</div>
          <DataTable rows={pointRows(recentPoints)} columns={["日期", "方向", "类型", "价格", "分数", "原因"]} emptyText="生成缠论结构后显示买卖点" />
        </aside>
      </div>
    </section>
  );
}

function LayerToggles({ layers, onToggle }: { layers: Required<PriceOptionLayers>; onToggle: (key: keyof PriceOptionLayers) => void }) {
  const items: Array<[keyof PriceOptionLayers, string]> = [
    ["movingAverages", "均线"],
    ["tradeSignals", "策略信号"],
    ["fractals", "分型"],
    ["strokes", "缠论笔"],
    ["segments", "线段"],
    ["pivots", "中枢"],
    ["recursivePivots", "递归中枢"],
    ["divergences", "背驰"],
    ["structureSignals", "买卖点"]
  ];
  return (
    <div className="chan-layer-toolbar" aria-label="缠论图层">
      {items.map(([key, label]) => (
        <label key={key} className="chart-check">
          <input type="checkbox" aria-label={`显示${label}`} checked={layers[key]} onChange={() => onToggle(key)} />
          {label}
        </label>
      ))}
    </div>
  );
}

function pointRows(points: ResearchSignal[]): Record<string, unknown>[] {
  return points.map((point) => ({
    日期: point.trading_day,
    方向: point.action,
    类型: point.title,
    价格: point.price,
    分数: point.score,
    原因: point.reason
  }));
}

function managedCsvPath(settings: PlatformSettings, timeframe: string): string {
  const adjust = (settings.adjust || "qfq").toLowerCase();
  return `data/market/a_share/${settings.exchange}/${settings.symbol}/${settings.symbol}_${settings.exchange}_${timeframe}_${adjust}_latest.csv`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd frontend && npm test -- src/pages/ChanChartPage.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ChanChartPage.tsx frontend/src/pages/ChanChartPage.test.tsx
git commit -m "feat: add chan chart page"
```

---

## Task 3: Wire Navigation and App State

**Files:**
- Modify: `frontend/src/shell/AppShell.test.tsx`
- Modify: `frontend/src/shell/AppShell.tsx`

- [ ] **Step 1: Write the failing test**

Update `frontend/src/shell/AppShell.test.tsx`:

```typescript
expect(NAV_ITEMS).toHaveLength(15);
expect(NAV_ITEMS.map((item) => item.id)).toContain("chan-chart");
```

Add navigation behavior near the existing page switch assertions:

```typescript
await user.click(screen.getByRole("button", { name: "缠论图表" }));
expect(screen.getByRole("button", { name: "缠论图表" })).toHaveClass("active");
expect(screen.getByRole("region", { name: "缠论图表工作区" })).toBeInTheDocument();
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd frontend && npm test -- src/shell/AppShell.test.tsx
```

Expected: FAIL because nav id/page route does not exist.

- [ ] **Step 3: Implement navigation**

Modify imports in `frontend/src/shell/AppShell.tsx`:

```typescript
import { ChartCandlestick } from "lucide-react";
import { ChanChartPage } from "../pages/ChanChartPage";
```

Add the nav item in `NAV_GROUPS`, preferably under `策略` before `策略工坊`:

```typescript
{ id: "chan-chart", label: "缠论图表", icon: ChartCandlestick },
```

Add the page route:

```typescript
"chan-chart": <ChanChartPage {...pageProps} />,
```

Add next-step behavior:

```typescript
if (page === "data") return { label: "去缠论图表", page: "chan-chart" };
if (page === "chan-chart") return { label: "去策略工坊", page: "strategies" };
```

Keep `applySettings` as the stale-state clearing boundary. Do not add duplicate global state unless Task 2 proves it is required.

- [ ] **Step 4: Run the test to verify it passes**

Run:

```bash
cd frontend && npm test -- src/shell/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/shell/AppShell.tsx frontend/src/shell/AppShell.test.tsx
git commit -m "feat: route chan chart workspace"
```

---

## Task 4: Add Workspace Styling and Responsive Fullscreen

**Files:**
- Modify: `frontend/src/pages/ChanChartPage.test.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Add class/state assertions to the page test**

Extend the fullscreen test in `frontend/src/pages/ChanChartPage.test.tsx`:

```typescript
expect(screen.getByRole("region", { name: "缠论图表工作区" })).toHaveClass("chan-chart-page");
await user.click(screen.getByRole("button", { name: "全屏图表" }));
expect(screen.getByRole("region", { name: "缠论图表工作区" })).toHaveClass("fullscreen");
```

- [ ] **Step 2: Run the test to verify current state**

Run:

```bash
cd frontend && npm test -- src/pages/ChanChartPage.test.tsx
```

Expected: PASS if Task 2 already added classes. If it fails, adjust Task 2 implementation before styling.

- [ ] **Step 3: Add CSS**

Append focused styles to `frontend/src/styles.css` near related chart/page styles:

```css
.chan-chart-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.chan-chart-page.fullscreen {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: #f8fafc;
  padding: 14px;
  overflow: auto;
}

.chan-chart-header,
.chan-chart-actions,
.chan-chart-timeframes,
.chan-layer-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.chan-chart-header {
  justify-content: space-between;
}

.chan-chart-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 340px);
  gap: 12px;
  align-items: start;
}

.chan-chart-main,
.chan-chart-inspector {
  min-width: 0;
}

.chan-chart-inspector {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chan-chart-timeframes button {
  border: 1px solid #d0d5dd;
  background: #ffffff;
  color: #344054;
  border-radius: 6px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}

.chan-chart-timeframes button.selected {
  border-color: #2563eb;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 700;
}

.chan-layer-toolbar {
  padding: 8px 10px;
  border: 1px solid #e4e7ec;
  background: #ffffff;
  border-radius: 8px;
}

@media (max-width: 980px) {
  .chan-chart-layout {
    grid-template-columns: 1fr;
  }

  .chan-chart-header {
    align-items: flex-start;
  }
}
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/styles.css frontend/src/pages/ChanChartPage.test.tsx
git commit -m "style: polish chan chart workspace"
```

---

## Task 5: Verification, QA, and Pending-List Closeout

**Files:**
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-25-chan-chart-workspace-qa.md`
- Optional create: `docs/qa/screenshots/2026-06-25-chan-chart-workspace-desktop.png`
- Optional create: `docs/qa/screenshots/2026-06-25-chan-chart-workspace-mobile.png`

- [ ] **Step 1: Run targeted frontend tests**

Run:

```bash
cd frontend && npm test -- src/pages/chartOptions.test.ts src/pages/ChanChartPage.test.tsx src/shell/AppShell.test.tsx
```

Expected: PASS.

- [ ] **Step 2: Run frontend build**

Run:

```bash
cd frontend && npm run build
```

Expected: PASS.

- [ ] **Step 3: Run backend/API regression tests**

Run:

```bash
python -m pytest tests/test_api_routes.py
```

Expected: PASS. Backend contracts should remain unchanged.

- [ ] **Step 4: Run browser acceptance**

Start the app if needed:

```bash
./scripts/run_app.sh
```

Then capture screenshots with the existing workflow:

```bash
node scripts/capture_app_screenshots.mjs
```

If the script only captures default routes, manually navigate to `缠论图表` with the browser tool or Playwright and save:

```text
docs/qa/screenshots/2026-06-25-chan-chart-workspace-desktop.png
docs/qa/screenshots/2026-06-25-chan-chart-workspace-mobile.png
```

Expected: desktop screenshot shows the new workspace, large K-line chart, volume panel, layer toggles, and inspector. Mobile screenshot shows no horizontal overflow and no text overlap.

- [ ] **Step 5: Update pending features**

Edit `docs/context/pending-features.md`:

- Remove `Chan TradingView-style chart workspace MVP` from `Pending` after the feature is verified.
- Add an implemented baseline bullet summarizing the completed workspace.
- Set `Next Recommended Feature` to a follow-up such as manual drawing persistence or keep the existing next strategy item if no chart follow-up is immediately needed.

- [ ] **Step 6: Write QA note**

Create `docs/qa/2026-06-25-chan-chart-workspace-qa.md`:

```markdown
# Chan Chart Workspace QA

Date: 2026-06-25

## Scope

Verified the first `缠论图表` React workspace with K-line, volume, Chan overlays, layer toggles, fullscreen expansion, timeframe switching, and structure inspector.

## Commands

- `cd frontend && npm test -- src/pages/chartOptions.test.ts src/pages/ChanChartPage.test.tsx src/shell/AppShell.test.tsx`
- `cd frontend && npm run build`
- `python -m pytest tests/test_api_routes.py`

## Browser Acceptance

- Desktop screenshot: `docs/qa/screenshots/2026-06-25-chan-chart-workspace-desktop.png`
- Mobile screenshot: `docs/qa/screenshots/2026-06-25-chan-chart-workspace-mobile.png`

## Notes

- The workspace reuses `/api/research/signals/preview`; no backend route was added.
- The surface is research-only and does not introduce live trading or broker execution.
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/chartOptions.ts frontend/src/pages/chartOptions.test.ts frontend/src/pages/ChanChartPage.tsx frontend/src/pages/ChanChartPage.test.tsx frontend/src/shell/AppShell.tsx frontend/src/shell/AppShell.test.tsx frontend/src/styles.css docs/context/pending-features.md docs/qa/2026-06-25-chan-chart-workspace-qa.md docs/qa/screenshots/2026-06-25-chan-chart-workspace-desktop.png docs/qa/screenshots/2026-06-25-chan-chart-workspace-mobile.png
git commit -m "feat: add chan chart workspace"
```

If screenshot capture is blocked by browser policy or environment tooling, commit the QA note with the exact blocker instead of screenshot paths.

---

## Self-Review

- Spec coverage: The plan covers the dedicated workspace, K-line/volume charts, Chan overlays, layer toggles, fullscreen, drag/zoom/pan via ECharts dataZoom, timeframe switching, inspector, tests, and browser screenshots.
- Backend scope: The plan intentionally reuses existing API contracts and adds no backend endpoint unless implementation proves a real gap.
- Out-of-scope guard: No step introduces live trading, broker execution, manual drawing persistence, multi-chart layouts, or strategy default changes.
- Placeholder scan: No task contains unfinished markers or unspecified test commands.
- Type consistency: `PriceOptionLayers`, `ChanChartPage`, and `chan-chart` are introduced before use in later tasks.
