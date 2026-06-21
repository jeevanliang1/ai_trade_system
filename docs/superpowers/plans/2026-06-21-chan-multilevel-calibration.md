# Chan Multi-Level Calibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix partial minute-coverage semantics for `ChanMultiLevelReversalStrategy` and rerun fixed six-stock calibration benchmarks.

**Architecture:** Keep the daily backtest loop and existing lower-level context model. Add a small consumed-data predicate to the `30m` context so `minute_missing_policy="daily_only"` can distinguish "CSV has future bars" from "minute data was available at this cutoff", then benchmark parameter variants without changing defaults unless evidence is clear.

**Tech Stack:** Python strategy core, pytest, existing local qfq fixtures under `data/market/a_share/`, `docs/qa/` evidence files, React/FastAPI screenshot workflow.

---

## File Structure

- Modify `tests/test_chan_multilevel_reversal_strategy.py`: add partial minute-coverage tests for `daily_only` and `skip_entry`.
- Modify `src/ai_trade_system/strategies/popular.py`: add a consumed lower-level data predicate and use it in fallback gating.
- Create `docs/qa/2026-06-21-chan-multilevel-calibration-qa.md`: record tests, benchmark variants, chosen recommendation, and screenshot paths.
- Modify `docs/context/pending-features.md`: move this calibration pass from pending to implemented baseline or narrow the remaining follow-up.

## Task 1: Specify Partial Minute-Coverage Semantics

- [ ] **Step 1: Add a failing `daily_only` partial-coverage test**

Add a test that writes a `30m` CSV starting on `2024-01-02`, runs a daily bullish signal on `2024-01-01`, and expects a `DAILY_FALLBACK` buy when `minute_missing_policy="daily_only"`.

- [ ] **Step 2: Add a default-policy control test**

Add the same setup with `minute_missing_policy="skip_entry"` and assert no signal is emitted.

- [ ] **Step 3: Run the new tests**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected before implementation: the new `daily_only` partial-coverage test fails because the strategy sees that the `30m` CSV has data and refuses daily fallback.

## Task 2: Implement Missing-At-Cutoff Detection

- [ ] **Step 1: Add lower-level consumed-data state**

Add a property to `ChanLowerLevelContext`:

```python
@property
def has_consumed_data(self) -> bool:
    return self.next_index > 0
```

- [ ] **Step 2: Use the new predicate in fallback gating**

Change the buy fallback branch so `daily_only` falls back only when no `30m` bar has been consumed by the current cutoff:

```python
if confirm_buy is None:
    if self.minute_missing_policy != "daily_only" or self.confirm_context.has_consumed_data:
        return self._time_exit_if_needed(bar)
```

- [ ] **Step 3: Run targeted tests**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected after implementation: all multilevel strategy tests pass.

## Task 3: Run Calibration Benchmarks

- [ ] **Step 1: Run fixed six-stock benchmark variants**

Run a bounded sweep covering default, corrected `daily_only`, `confirm_only`, `confirm_then_risk`, score thresholds around `24/28/32`, and `minute_sell_mode` variants. Use the existing daily qfq fixtures and available `30m`/`15m` managed CSVs.

- [ ] **Step 2: Record comparable metrics**

Write `docs/qa/2026-06-21-chan-multilevel-calibration-qa.md` with parameter rows, per-symbol metrics, aggregate return, aggregate drawdown, trade count, and explicit minute coverage.

- [ ] **Step 3: Decide defaults conservatively**

Only update default strategy parameters if the sweep improves fixed-universe average return without materially worsening drawdown or relying on narrow partial-coverage artifacts. Otherwise record a recommended preset and keep defaults unchanged.

## Task 4: Verify And Close Out

- [ ] **Step 1: Run full backend and frontend verification**

Run:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
```

- [ ] **Step 2: Capture React acceptance screenshot**

Start `./scripts/run_app.sh` and capture the Strategy Workshop or default React surface with headless Chrome. Record the screenshot path in QA.

- [ ] **Step 3: Run sedimentation audit**

Read and apply `docs/auto-sedimentation-skill.md`, then ensure final response includes the required sedimentation line.
