# Chan Multi-Level 60m Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Chan multi-level reversal judgment by adding longer `60m` confirmation support, persisting six-stock `60m` fixtures, and recording fixed benchmark evidence.

**Architecture:** Reuse the existing daily-loop strategy and managed-data paths. Extend the lower-level timeframe allowlists and registry enum metadata, keep cutoff-based lower-level consumption, then benchmark `60m + 30m` against the existing `30m + 15m` and daily Chan baselines.

**Tech Stack:** Python strategy core, `ai_trade_system.data_manager`, AKShare minute fetcher, pytest, existing benchmark fixtures, React/FastAPI screenshot workflow.

---

## File Structure

- Modify `src/ai_trade_system/strategies/popular.py`: extend confirm/risk timeframe allowlists and reason labels.
- Modify `tests/test_chan_multilevel_reversal_strategy.py`: add TDD coverage for `60m` confirmation and `30m` risk behavior.
- Modify `src/ai_trade_system/strategy_registry.py`: expose `60m` and `30m` enum options in parameter guidance.
- Modify `tests/test_strategy_registry.py`: assert new options are discoverable.
- Create `docs/qa/2026-06-21-chan-multilevel-60m-completion-qa.md`: record data update, benchmarks, verification, and screenshots.
- Modify `docs/context/pending-features.md`: mark the 60m completion pass and retain any remaining data-depth follow-up only if justified by QA.

## Task 1: Specify 60m Strategy Behavior

- [ ] **Step 1: Add failing strategy tests**

Add tests to `tests/test_chan_multilevel_reversal_strategy.py`:

```python
def test_chan_multilevel_daily_buy_can_be_confirmed_by_60m(monkeypatch, tmp_path):
    day = date(2024, 1, 1)
    confirm_path = tmp_path / "confirm-60m.csv"
    risk_path = tmp_path / "risk-30m.csv"
    write_bars_csv([make_minute_bar(0, "60m", 14, 0)], confirm_path)
    write_bars_csv([make_minute_bar(0, "30m", 14, 30)], risk_path)
    seen: list[tuple[str, object]] = []
    patch_multilevel_analyzers(
        monkeypatch,
        {
            "daily": [make_signal(day, "CHAN_STRUCT_BUY_T3", "buy", 42, "third-buy")],
            "60m": [make_signal(day, "CHAN_STRUCT_BUY_CONFIRM", "buy", 36, "first-buy")],
            "30m": [],
        },
        seen,
    )
    strategy = ChanMultiLevelReversalStrategy(
        "000001",
        min_bars=1,
        lookback=5,
        min_daily_score=20,
        min_confirm_score=20,
        confirm_timeframe="60m",
        risk_timeframe="30m",
        confirm_csv_path=str(confirm_path),
        risk_csv_path=str(risk_path),
        lower_level_policy="confirm_only",
    )

    signals = strategy.on_bar(make_daily_bar(0))

    assert [signal.action for signal in signals] == ["buy"]
    assert "CONFIRM_60M" in signals[0].reason
```

Add a second test where bearish `30m` risk blocks a `60m` confirmed buy under `confirm_then_risk`.

- [ ] **Step 2: Verify RED**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected before implementation: tests fail because `confirm_timeframe="60m"` and `risk_timeframe="30m"` are rejected or reason labels are still fixed to `30M/15M`.

## Task 2: Implement 60m And Dynamic Labels

- [ ] **Step 1: Extend allowlists**

Change constants in `src/ai_trade_system/strategies/popular.py`:

```python
CHAN_CONFIRM_TIMEFRAMES = {"60m", "30m"}
CHAN_RISK_TIMEFRAMES = {"30m", "15m"}
```

- [ ] **Step 2: Add label helper**

Add:

```python
def _level_label(timeframe: str) -> str:
    return timeframe.upper()
```

Use it in all `chan_multilevel:CONFIRM_*` and `chan_multilevel:RISK_*` reason strings instead of hard-coded `CONFIRM_30M` or `RISK_15M`.

- [ ] **Step 3: Verify GREEN**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected after implementation: all multilevel tests pass.

## Task 3: Expose Registry Options

- [ ] **Step 1: Update registry metadata**

In `src/ai_trade_system/strategy_registry.py`, update `ChanMultiLevelReversalStrategy` parameter options:

```python
"confirm_timeframe": ["60m", "30m"]
"risk_timeframe": ["30m", "15m"]
```

- [ ] **Step 2: Add registry test assertions**

Extend `tests/test_strategy_registry.py` to assert these options are returned.

- [ ] **Step 3: Verify registry tests**

Run:

```bash
python -m pytest tests/test_strategy_registry.py -q
```

Expected: registry tests pass and options include the new levels.

## Task 4: Persist 60m Fixtures

- [ ] **Step 1: Download six-stock 60m data**

Use `ai_trade_system.data_manager.update_stock_data()` or the CLI path to write managed `60m` qfq latest CSV files for the fixed six stocks over `20230619` to `20260619`.

- [ ] **Step 2: Record coverage**

Record status, row count, start timestamp, and end timestamp for `daily`, `60m`, `30m`, and `15m` in the QA doc.

## Task 5: Benchmark Complete Multi-Level Judgment

- [ ] **Step 1: Run benchmark matrix**

Run fixed six-stock benchmarks for daily baseline, current `30m+15m`, and new `60m+30m` variants.

- [ ] **Step 2: Record metrics**

Record final equity, return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor in `docs/qa/2026-06-21-chan-multilevel-60m-completion-qa.md`.

- [ ] **Step 3: Decide defaults conservatively**

Only update defaults if `60m` materially improves return without hiding coverage limits or worsening drawdown beyond the daily baseline. Otherwise keep defaults and document the best experimental preset.

## Task 6: Full Verification And Acceptance

- [ ] **Step 1: Run full verification**

Run:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
```

- [ ] **Step 2: Capture screenshots**

Start `./scripts/run_app.sh`, capture React platform screenshots, and record paths in QA.

- [ ] **Step 3: Run sedimentation audit**

Apply `docs/auto-sedimentation-skill.md` and include the required sedimentation line in the final response.
