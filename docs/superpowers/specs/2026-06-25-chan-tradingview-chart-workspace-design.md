# Chan TradingView-Style Chart Workspace Design

Date: 2026-06-25

## Goal

Add a dedicated React workspace for Chan chart inspection that feels closer to a TradingView-style analysis panel while staying inside the current React + FastAPI + ECharts stack.

The workspace should let a user pick an A-share stock, switch K-line timeframe, inspect price/volume, and visually review Chan structure overlays: fractals, strokes, segments, pivots/centers, recursive pivots, divergences, and buy/sell points. It is a research and review surface only. It must not introduce live trading behavior or broker execution.

## Current Context

The repository already has the main building blocks:

- React + TypeScript + Vite is the default browser surface.
- `ChartPanel` wraps ECharts and supports grouped chart zoom.
- `priceOption` renders A-share candlesticks, MA20/MA60, buy/sell markers, and Chan structure overlay series.
- `volumeOption` renders a linked volume panel.
- `ResearchSignalPreview` already carries `chan_structure` overlay data for fractals, strokes, pivots, segments, recursive pivots, divergences, and structure signals.
- `/api/research/signals/preview` loads the selected CSV and returns the Chan/RSI preview payload.
- Shared platform settings already include `symbol`, `exchange`, `csv_path`, `adjust`, and `timeframe`.
- Managed A-share market data lives under `data/market/a_share/{exchange}/{code}/{code}_{exchange}_{timeframe}_{adjust}_latest.csv`.

The new feature should reuse these pieces instead of introducing a separate charting subsystem.

## Recommended Approach

Build a new navigation item and page: `缠论图表`.

This is preferred over expanding Strategy Workshop because Strategy Workshop is for selecting strategies, editing parameters, and generating previews. A TradingView-style chart is a repeated inspection workflow; it needs more screen space, richer chart controls, and an inspector that should not compete with strategy editing controls.

Use ECharts for the MVP. It already supports candlesticks, mark areas, scatter markers, linked zoom, inside drag/pan, and fullscreen-friendly resizing. Importing a new chart library can be considered later only if ECharts becomes the limiting factor.

## Scope

Frontend:

- Add a `缠论图表` workspace to the React navigation, likely in the `策略` or `验证` group.
- Add a `ChanChartPage` or similarly named page that receives the existing `PlatformState` and `PlatformActions`.
- Reuse shared stock selection behavior. Stock-aware controls must use the existing `selectStock` action so symbol, exchange, timeframe, CSV path, and stale results stay synchronized.
- Add a timeframe segmented control for `daily`, `60m`, `30m`, `15m`, `5m`, and `1m`.
- Add page-owned actions for:
  - loading the selected timeframe CSV through existing `actions.loadData`.
  - generating Chan structure through existing `actions.previewResearchSignals`.
  - optionally triggering `actions.downloadData` when local data is missing.
- Render a large price chart and a linked volume chart.
- Provide layer toggles for:
  - K-line and moving averages.
  - strategy buy/sell markers when present.
  - Chan fractals.
  - Chan strokes.
  - Chan segments.
  - Chan pivots/centers.
  - recursive pivots.
  - divergences.
  - Chan buy/sell points.
- Support fullscreen mode for the chart area. Fullscreen should preserve controls needed to exit, switch layers, reset view, and see compact structure status.
- Support drag/zoom/pan through ECharts `dataZoom` inside interaction and linked price/volume groups.
- Add a right-side structure inspector with:
  - selected stock, timeframe, data range, and bar count.
  - structure counts: fractals, strokes, segments, pivots, recursive pivots, divergences.
  - latest Chan signal title/kind/action/score when available.
  - blocker messages when preview cannot generate reliable structure.
  - a compact recent buy/sell point list.

Backend:

- Reuse `/api/data/load`, `/api/data/download`, and `/api/research/signals/preview` for the first implementation.
- Do not add a new endpoint unless the page needs a combined payload after the first frontend slice proves duplication or race issues.
- Keep all data access inside the existing safe `data/` path and managed data conventions.
- Do not change Chan strategy defaults or trading behavior.

Styles and interaction:

- Keep the surface dense and tool-like, matching the existing operational workbench.
- Avoid decorative marketing layout. The first viewport should be the usable chart workspace.
- Use icon buttons for fullscreen, reset, fit view, and layer visibility where icons are clear.
- Ensure fullscreen and normal layouts fit without text overlap on desktop and narrow mobile widths.

## Data Flow

1. User selects a stock through the shared stock selector.
2. User selects a timeframe in the Chan chart page.
3. The page updates platform settings through existing actions, deriving the canonical managed CSV path for the selected stock/timeframe/adjust combination.
4. The page loads bars with `actions.loadData`; if no local CSV exists, it shows a clear missing-data state with a data download action.
5. The page calls `actions.previewResearchSignals` to populate `state.researchSignals`.
6. The chart builds layer-filtered options from `state.bars`, optional `state.signals`, and `state.researchSignals.chan_structure`.
7. The inspector reads the same preview payload and shows structure counts, latest signals, blockers, and recent point rows.

## Error Handling

- Missing CSV: show a page-level blocker that names the expected local CSV path and offers the existing data download/load path. Do not silently fall back to unrelated `data/{code}_daily.csv` defaults.
- Insufficient bars: keep the chart visible if bars exist, but show the preview blockers and zero/partial structure counts.
- Preview API failure: keep loaded K-line data on screen, show an inline error, and let the user rerun analysis.
- Timeframe switch: clear stale Chan preview and strategy signal overlays until the new timeframe data and preview are loaded.
- Fullscreen failure: if the browser fullscreen API is unavailable, use a CSS-expanded mode inside the app shell.

## Out Of Scope

- Manual user-drawn trendlines or persistent drawing objects.
- Multi-chart tiled layout.
- User-created indicator templates.
- TradingView account sync or external chart embedding.
- Broker-grade realtime tick streaming.
- Live trading, broker order placement, or any execution shortcut.
- Changing `ChanStructureStrategy` or `ChanMultiLevelReversalStrategy` behavior.

## Acceptance Criteria

- The React app has a visible `缠论图表` workspace reachable from navigation.
- The page can load the selected stock/timeframe and render a large candlestick chart plus volume panel.
- The page can generate and display Chan overlays for fractals, strokes, segments, pivots/centers, recursive pivots, divergences, and buy/sell points when preview data is available.
- Layer toggles change the visible overlay set without requiring a page reload.
- Timeframe switching updates settings, CSV path, bars, and stale analysis state consistently.
- The chart supports mouse wheel zoom and drag/pan through ECharts inside data zoom.
- Fullscreen mode expands the chart workspace and provides a clear exit control.
- The structure inspector shows counts, latest signal, blockers, and recent buy/sell points.
- Frontend tests cover navigation presence, timeframe switching, layer toggles, fullscreen state, and inspector rendering.
- Existing chart option tests continue to cover Chan overlay series.
- Backend route tests remain green because the MVP reuses existing API contracts.
- Browser acceptance captures desktop and mobile screenshots of the new workspace after real app content is visible.

## Implementation Notes

- Prefer extracting a reusable chart option helper only when layer filtering becomes too large for the page.
- Existing `priceOption` can be extended with a layer/filter argument, but current callers must remain compatible.
- `ChartPanel` may need an explicit resize trigger or key revision when entering/exiting fullscreen.
- The page should not introduce decorative or inactive controls. Every visible control should either work or be shown as read-only state.
- If current `actions.previewResearchSignals` is too global for page-local stale-state handling, add a small action or state field only after confirming the issue in implementation.
