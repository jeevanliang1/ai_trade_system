# Chan Watch Divergence Arming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bounded T1 divergence watch arming to `ChanStructureStrategy` so later same-direction T2/T3 or confirm signals can consume the watch setup.

**Architecture:** Keep `research.chan_structure` unchanged. Add a small strategy-local arming record in `src/ai_trade_system/strategies/popular.py`, update registry metadata for the new constructor parameter, and test via patched research signals for deterministic RED/GREEN behavior.

**Tech Stack:** Python dataclasses/deques, existing `ResearchSignal`, pytest monkeypatch, fixed local A-share backtest fixtures, React strategy registry rendering.

---

## File Structure

- Modify `src/ai_trade_system/strategies/popular.py`: add `ArmedChanWatch`, `watch_confirm_bars`, arming helpers, and confirmation consumption.
- Modify `src/ai_trade_system/strategy_registry.py`: add guidance for `watch_confirm_bars` and update Chan strategy description.
- Modify `tests/test_builtin_popular_strategies.py`: add TDD tests for arming, expiry, disabled mode, and validation.
- Create `docs/qa/2026-06-19-chan-watch-divergence-arming-qa.md`: record TDD, full verification, fixed benchmarks, and browser QA.
- Modify `docs/context/pending-features.md`: move this item into completed baseline and record the next Chan development item.

## Task 1: RED Tests

- [x] Add a helper `make_research_signal(..., tags=...)` so tests can produce watch-tagged T1 signals.
- [x] Add `test_chan_structure_strategy_arms_bottom_divergence_and_confirms_with_t2`:
  - patched scan emits `CHAN_STRUCT_BUY_T1_DIVERGENCE` with `("chan", "structure", "divergence", "watch")` on bar 2;
  - patched scan emits `CHAN_STRUCT_BUY_T2` on bar 4;
  - strategy uses `signal_mode="confirmation"`, `min_signal_score=30`, `watch_confirm_bars=5`;
  - expected output is one buy reason starting with `chan_structure:ARMED_CONFIRM:CHAN_STRUCT_BUY_T1_DIVERGENCE->CHAN_STRUCT_BUY_T2`.
- [x] Add equivalent sell test with an initial position and `CHAN_STRUCT_SELL_T3`.
- [x] Add expiry and disabled tests that expect no trades.
- [x] Add negative `watch_confirm_bars` validation test.
- [x] Run targeted tests and confirm they fail for missing constructor parameter or missing arming behavior.

## Task 2: Minimal Strategy Implementation

- [x] Add `ArmedChanWatch` dataclass.
- [x] Accept and validate `watch_confirm_bars`.
- [x] Track `self.bar_index` and `self.armed_watch`.
- [x] When same-bar candidate has `watch` and kind ends with `_T1_DIVERGENCE`, arm it and continue scanning candidates.
- [x] When a later same-direction confirmation candidate arrives and is allowed by armed rules, emit `ARMED_CONFIRM` signal and clear arming.
- [x] Expire arming when current index minus armed index exceeds `watch_confirm_bars`.

## Task 3: Metadata And QA

- [x] Add registry guidance for `watch_confirm_bars`.
- [x] Update pending features.
- [x] Run fixed benchmark script and write QA tables.

## Task 4: Final Verification And Commit

- [x] Run `PYTHONPATH=src python -m pytest`.
- [x] Run `cd frontend && npm test -- --run`.
- [x] Run `cd frontend && npm run build`.
- [x] Run `git diff --check`.
- [x] Capture browser screenshot of Strategy Workshop.
- [x] Commit all related changes.
