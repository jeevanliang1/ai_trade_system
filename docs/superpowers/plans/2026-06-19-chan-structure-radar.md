# Chan Structure Radar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Signal Radar `chan_structure` scoring mode backed by the existing Chan structure analyzer.

**Architecture:** Extend the existing `/api/research/signals/batch` branching model with a third scoring mode, then teach the React Signal Radar page to submit and render that mode. Keep `ChanStructureStrategy` trading behavior unchanged; this is an inspection/ranking workflow.

**Tech Stack:** Python 3, FastAPI/Pydantic, pytest, React/TypeScript/Vitest, existing `scan_chan_structure` analyzer.

---

## File Structure

- Modify `src/ai_trade_system/api/schemas.py`: add `chan_structure` to `ResearchSignalBatchRequest.score_mode`.
- Modify `src/ai_trade_system/api/service.py`: add Chan structure batch row scoring helpers and route branching.
- Modify `tests/test_api_routes.py`: add API RED/GREEN coverage for `score_mode="chan_structure"`.
- Modify `frontend/src/types.ts`: extend `ResearchSignalBatchScoreMode` and add optional `chan_structure` diagnostic type.
- Modify `frontend/src/pages/SignalRadarPage.tsx`: add mode option, title, diagnostics, and CSV columns.
- Modify `frontend/src/pages/SignalRadarPage.test.tsx`: add frontend RED/GREEN coverage.
- Modify `docs/context/pending-features.md`: remove completed Radar item and record next Chan follow-up.
- Create `docs/qa/2026-06-19-chan-structure-radar-qa.md`: record verification, browser screenshot, and fixed-stock benchmark evidence.

## Task 1: API RED Test

**Files:**
- Modify: `tests/test_api_routes.py`

- [ ] Add a helper near existing route tests to create a Chan-structure-friendly bar sequence:

```python
def _chan_structure_closes() -> list[float]:
    return [
        10.0,
        9.4,
        10.4,
        11.6,
        10.8,
        10.1,
        11.5,
        12.8,
        12.6,
        12.5,
        12.3,
        12.8,
    ] * 7
```

- [ ] Add `test_research_signals_batch_route_ranks_chan_structure_from_managed_csv`:

```python
def test_research_signals_batch_route_ranks_chan_structure_from_managed_csv(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    data_dir = tmp_path / "data"
    strong = StockInfo("688981", "中芯国际", "SSE")
    weak = StockInfo("000858", "五粮液", "SZSE")
    write_stock_catalog([weak, strong], data_dir / "a_share_stocks.csv")
    strong_path = _write_managed_bars(strong, _chan_structure_closes())
    weak_path = _write_managed_bars(weak, _momentum_closes(20.0, 20.8, 84))

    response = client.post(
        "/api/research/signals/batch",
        json={
            "settings": _settings_payload(),
            "query": "",
            "limit": 2,
            "min_bars": 60,
            "lookback": 84,
            "universe": "catalog",
            "score_mode": "chan_structure",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score_mode"] == "chan_structure"
    assert payload["available"] == 2
    assert payload["rows"][0]["code"] == "688981"
    assert payload["rows"][0]["csv_path"] == strong_path.as_posix()
    assert payload["rows"][1]["csv_path"] == weak_path.as_posix()
    assert payload["rows"][0]["score"]["chan_structure"]["stroke_count"] > 0
    assert payload["rows"][0]["score"]["chan_structure"]["pivot_count"] > 0
    assert payload["rows"][0]["latest_signal"]["kind"].startswith("CHAN_STRUCT_")
    assert payload["rows"][0]["score"]["total_score"] > abs(payload["rows"][1]["score"]["total_score"])
```

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_research_signals_batch_route_ranks_chan_structure_from_managed_csv -q
```

Expected: fail with validation error because `score_mode="chan_structure"` is not accepted.

## Task 2: API Implementation

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Test: `tests/test_api_routes.py`

- [ ] In `schemas.py`, extend the score mode literal:

```python
score_mode: Literal["research", "volume_momentum", "chan_structure"] = "research"
```

- [ ] In `service.py`, import:

```python
from ai_trade_system.research.chan_structure import scan_chan_structure
from ai_trade_system.research.dataframe import bars_to_frame
```

- [ ] Add a branch inside `batch_research_signals` after the volume momentum branch:

```python
if request.score_mode == "chan_structure":
    rows.append(_chan_structure_batch_row(base_row, bars, request, index))
    continue
```

- [ ] Add helper functions:

```python
def _chan_structure_batch_row(base_row: dict[str, Any], bars: list[Bar], request: ResearchSignalBatchRequest, order: int) -> dict[str, Any]:
    score, latest_signal, blockers, diagnostics, preview = _chan_structure_score(bars, request.min_bars, request.lookback)
    return {
        **base_row,
        "status": "scanned",
        "score": score,
        "latest_signal": latest_signal,
        "preview": preview,
        "momentum": None,
        "blockers": blockers,
        "_order": order,
    }
```

```python
def _chan_structure_score(
    bars: list[Bar],
    min_bars: int,
    lookback: int,
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    if len(bars) < min_bars:
        diagnostics = {
            "fractal_count": 0,
            "stroke_count": 0,
            "pivot_count": 0,
            "latest_signal_kind": None,
            "latest_signal_title": None,
        }
        blockers = [{"code": "INSUFFICIENT_BARS", "message": f"至少需要 {min_bars} 根K线，当前 {len(bars)} 根"}]
        score = _chan_structure_score_payload(0.0, "neutral", 0.0, "缠论结构样本不足", diagnostics)
        preview = {"bars": len(bars), "signals": [], "score": score, "blockers": blockers, "chan_structure": diagnostics}
        return score, None, blockers, diagnostics, preview

    result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=5, min_rebound_pct=0.03, lookback=lookback)
    latest_signal = _serialize(result.signals[-1]) if result.signals else None
    total_score = result.chan_score
    direction = "bullish" if total_score > 0 else "bearish" if total_score < 0 else "neutral"
    confidence = round(min(1.0, max(0.0, 0.35 + abs(total_score) / 100.0)), 4)
    diagnostics = {
        "fractal_count": len(result.fractals),
        "stroke_count": len(result.strokes),
        "pivot_count": len(result.pivots),
        "latest_signal_kind": latest_signal["kind"] if latest_signal else None,
        "latest_signal_title": latest_signal["title"] if latest_signal else None,
    }
    summary = (
        f"分型 {diagnostics['fractal_count']} 个，笔 {diagnostics['stroke_count']} 条，"
        f"中枢 {diagnostics['pivot_count']} 个，"
        f"{diagnostics['latest_signal_title'] or '暂无结构触发'}"
    )
    score = _chan_structure_score_payload(total_score, direction, confidence, summary, diagnostics)
    blockers = [] if latest_signal else [{"code": "NO_CHAN_STRUCTURE_SIGNAL", "message": summary}]
    preview = {
        "symbol": bars[-1].symbol,
        "exchange": bars[-1].exchange,
        "bars": len(bars),
        "signals": [_serialize(signal) for signal in result.signals],
        "score": score,
        "blockers": blockers,
        "chan_structure": diagnostics,
    }
    return score, latest_signal, blockers, diagnostics, preview
```

```python
def _chan_structure_score_payload(total_score: float, direction: str, confidence: float, summary: str, diagnostics: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_score": total_score,
        "direction": direction,
        "confidence": confidence,
        "chan_score": total_score,
        "rsi_score": 0,
        "summary": summary,
        "chan_structure": diagnostics,
    }
```

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py::test_research_signals_batch_route_ranks_chan_structure_from_managed_csv -q
```

Expected: pass.

- [ ] Run:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py -q
```

Expected: all API route tests pass.

## Task 3: Frontend RED Test

**Files:**
- Modify: `frontend/src/pages/SignalRadarPage.test.tsx`

- [ ] Add `test("SignalRadarPage submits chan structure score mode and renders diagnostics", ...)`:

```tsx
test("SignalRadarPage submits chan structure score mode and renders diagnostics", async () => {
  const user = userEvent.setup();
  vi.mocked(api.batchResearchSignals).mockResolvedValue({
    query: "",
    universe: "catalog",
    score_mode: "chan_structure",
    scanned: 1,
    available: 1,
    missing: 0,
    rows: [
      {
        rank: 1,
        code: "688981",
        name: "中芯国际",
        exchange: "SSE",
        csv_path: "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv",
        status: "scanned",
        score: {
          total_score: 44,
          direction: "bullish",
          confidence: 0.79,
          chan_score: 44,
          rsi_score: 0,
          summary: "分型 7 个，笔 4 条，中枢 2 个，缠论三买",
          chan_structure: {
            fractal_count: 7,
            stroke_count: 4,
            pivot_count: 2,
            latest_signal_kind: "CHAN_STRUCT_BUY_T3",
            latest_signal_title: "缠论三买"
          }
        },
        latest_signal: {
          trading_day: "2026-06-18",
          symbol: "688981",
          exchange: "SSE",
          kind: "CHAN_STRUCT_BUY_T3",
          action: "buy",
          price: 130.5,
          strength: 0.78,
          score: 44,
          title: "缠论三买",
          reason: "向上离开中枢后的回抽未跌回中枢上沿",
          tags: ["chan", "structure", "third-buy"]
        },
        preview: null,
        momentum: null,
        blockers: []
      }
    ]
  });

  render(<SignalRadarPage {...makeProps()} />);

  await user.selectOptions(screen.getByLabelText("评分模式"), "chan_structure");
  await user.click(screen.getByRole("button", { name: "批量扫描" }));

  expect(api.batchResearchSignals).toHaveBeenCalledWith(makeProps().state.settings, expect.objectContaining({ score_mode: "chan_structure" }));
  expect(await screen.findByText("缠论结构排行")).toBeVisible();
  expect(screen.getAllByText(/分型 7/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/笔 4/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/中枢 2/).length).toBeGreaterThan(0);
  expect(screen.getAllByText("缠论三买").length).toBeGreaterThan(0);
});
```

- [ ] Run:

```bash
cd frontend && npm test -- SignalRadarPage.test.tsx
```

Expected: fail because `chan_structure` is not a valid option and diagnostics are not rendered.

## Task 4: Frontend Implementation

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/SignalRadarPage.tsx`
- Test: `frontend/src/pages/SignalRadarPage.test.tsx`

- [ ] In `types.ts`, add:

```typescript
export type ResearchSignalChanStructure = {
  fractal_count: number;
  stroke_count: number;
  pivot_count: number;
  latest_signal_kind: string | null;
  latest_signal_title: string | null;
};
```

- [ ] Extend score and batch mode types:

```typescript
chan_structure?: ResearchSignalChanStructure | null;
```

```typescript
export type ResearchSignalBatchScoreMode = "research" | "volume_momentum" | "chan_structure";
```

- [ ] Add a select option in `SignalRadarPage.tsx`:

```tsx
<option value="chan_structure">缠论结构</option>
```

- [ ] Render diagnostics in `RadarResultCard` when `row.score?.chan_structure` exists:

```tsx
{row.score?.chan_structure ? (
  <div className="radar-score-line">
    <span>分型 {row.score.chan_structure.fractal_count}</span>
    <span>笔 {row.score.chan_structure.stroke_count}</span>
    <span>中枢 {row.score.chan_structure.pivot_count}</span>
  </div>
) : null}
```

- [ ] Add table columns when any row has `score?.chan_structure`, and add CSV columns `fractal_count`, `stroke_count`, `pivot_count`, `structure_signal`.
- [ ] Update `scoreModeTitle`:

```typescript
if (mode === "chan_structure") return "缠论结构";
```

- [ ] Run:

```bash
cd frontend && npm test -- SignalRadarPage.test.tsx
```

Expected: Signal Radar page tests pass.

## Task 5: Full Verification, Benchmarks, Docs, Browser QA

**Files:**
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-19-chan-structure-radar-qa.md`

- [ ] Remove the completed Signal Radar `chan_structure` item from pending.
- [ ] Keep the next recommended feature as Chan structure visualization overlays.
- [ ] Run:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test && npm run build
```

- [ ] Run fixed benchmark backtests on:
  - `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
  - `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`
- [ ] Start `./scripts/run_app.sh`.
- [ ] Browser QA flow:
  - Open `http://localhost:5173`.
  - Navigate to Signal Radar.
  - Select scoring mode `缠论结构`.
  - Select universe `当前标的` or `仅本地CSV`.
  - Click `批量扫描`.
  - Verify page title, nonblank content, no framework overlay, empty warn/error console, and visible structure diagnostics.
  - Save screenshot under `/tmp/ai_trade_system_chan_structure_radar.png`.
- [ ] Record commands, benchmark table, browser evidence, and screenshot path in QA doc.
- [ ] Commit implementation:

```bash
git add src frontend docs tests
git commit -m "feat: add chan structure radar scoring"
```
