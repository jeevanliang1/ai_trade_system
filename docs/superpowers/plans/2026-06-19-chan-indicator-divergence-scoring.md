# Chan Indicator Divergence Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MACD and volume-backed divergence strength plus dynamic confirmation scoring to the Chan structure analyzer.

**Architecture:** Keep `scan_chan_structure` as the single public entrypoint. Add a small internal indicator context, enrich `ChanDivergence`, serialize the added fields through the existing overlay path, and keep all strategy/API consumers on the existing result shape.

**Tech Stack:** Python dataclasses, pandas input frames, existing pure-Python research analyzer, pytest, TypeScript types and Vitest fixtures.

---

### Task 1: Failing Analyzer Tests

**Files:**
- Modify: `tests/test_research_signals.py`

- [ ] **Step 1: Write failing tests**

Add tests that build deterministic Chan bars with changing volume and assert:

```python
result = scan_chan_structure(bars_to_frame(bars), min_stroke_bars=4, min_rebound_pct=0.02)
buy_divergence = next(divergence for divergence in result.divergences if divergence.action == "buy")
assert buy_divergence.macd_strength > 0
assert buy_divergence.volume_strength > 0
assert buy_divergence.confirmation_score > abs(buy_divergence.base_score)
assert any(signal.kind == "CHAN_STRUCT_BUY_CONFIRM" and abs(signal.score) > 52.0 for signal in result.signals)
```

Add an overlay assertion:

```python
overlay = _chan_structure_overlay(result)
assert overlay.divergences[0].macd_strength == result.divergences[0].macd_strength
assert overlay.divergences[0].volume_strength == result.divergences[0].volume_strength
assert overlay.divergences[0].confirmation_score == result.divergences[0].confirmation_score
```

- [ ] **Step 2: Verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py::test_chan_structure_scores_divergence_with_macd_and_volume_evidence tests/test_research_signals.py::test_chan_structure_overlay_exposes_indicator_divergence_evidence -q
```

Expected: fail because `ChanDivergence` and `ChanDivergenceOverlay` do not yet expose the new fields.

### Task 2: Analyzer Implementation

**Files:**
- Modify: `src/ai_trade_system/research/chan_structure.py`
- Modify: `src/ai_trade_system/research/models.py`
- Modify: `src/ai_trade_system/research/service.py`

- [ ] **Step 1: Add indicator evidence fields**

Extend `ChanDivergence` with:

```python
base_score: float
macd_strength: float
volume_strength: float
confirmation_score: float
macd_reference: float
macd_current: float
volume_reference: float
volume_current: float
```

Extend `ChanDivergenceOverlay` with the same numeric fields.

- [ ] **Step 2: Compute indicator context**

Add a private context builder that calculates EMA12, EMA26, MACD histogram, and rolling volume values from `frame["close"]` and `frame["volume"]`, keyed by row index. Use no third-party dependency beyond pandas already present.

- [ ] **Step 3: Enrich divergence detection**

Pass the indicator context to `_detect_divergences`. For each structural divergence, calculate:

```python
energy_component = min(28.0, max(0.0, (1 - current_energy / reference_energy) * 50.0))
macd_component = min(18.0, max(0.0, (1 - current_macd / reference_macd) * 30.0))
volume_component = min(12.0, max(0.0, (1 - current_volume / reference_volume) * 20.0))
base_score = round(30.0 + energy_component + macd_component + volume_component, 2)
confirmation_score = round(base_score + price_component + break_component, 2)
```

Use buy polarity for down-segment histogram pressure and sell polarity for up-segment histogram pressure.

- [ ] **Step 4: Generate dynamic signals**

Update `_divergence_signals` to use positive dynamic scores for buy signals and negative dynamic scores for sell signals. Include MACD and volume evidence in the reason text.

- [ ] **Step 5: Verify GREEN**

Run the RED command again. Expected: both tests pass.

### Task 3: Frontend Contract

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/chartOptions.test.ts`

- [ ] **Step 1: Fix overlay types**

Ensure `ChanSegmentOverlay` contains `start_stroke_index`, `end_stroke_index`, and `break_stroke_index`, and `ChanStrokeOverlay` does not.

Extend `ChanDivergenceOverlay` with:

```typescript
base_score: number;
macd_strength: number;
volume_strength: number;
confirmation_score: number;
macd_reference: number;
macd_current: number;
volume_reference: number;
volume_current: number;
```

- [ ] **Step 2: Update chart fixture**

Add the new divergence evidence fields to the Chan overlay fixture used by chart option tests.

- [ ] **Step 3: Verify frontend tests**

Run:

```bash
cd frontend && npm test -- --run src/pages/chartOptions.test.ts
```

Expected: chart option tests pass.

### Task 4: Regression, Benchmarks, QA, and Commit

**Files:**
- Create: `docs/qa/2026-06-19-chan-indicator-divergence-scoring-qa.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Run targeted and full verification**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_research_signals.py tests/test_builtin_popular_strategies.py tests/test_api_routes.py -q
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

- [ ] **Step 2: Run fixed benchmark backtests**

Run the project backtest path for `ChanStructureStrategy` against:

```text
data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv
data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv
```

Record rows, date range, final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor.

- [ ] **Step 3: Run browser QA**

Start:

```bash
./scripts/run_app.sh
```

Open `http://127.0.0.1:5173/`, verify Strategy Workshop renders, toggle `显示缠论结构`, check console warnings/errors, and save a screenshot.

- [ ] **Step 4: Update docs and commit**

Update `docs/context/pending-features.md`, create the QA note, run `git diff --check`, then commit:

```bash
git add docs/context/pending-features.md docs/qa/2026-06-19-chan-indicator-divergence-scoring-qa.md frontend/src/pages/chartOptions.test.ts frontend/src/types.ts src/ai_trade_system/research/chan_structure.py src/ai_trade_system/research/models.py src/ai_trade_system/research/service.py tests/test_research_signals.py
git commit -m "feat: score chan divergence with indicators"
```
