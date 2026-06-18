# Chan Confirmation T3 Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let `ChanStructureStrategy` confirmation mode trade Chan T3 pivot-retest confirmation signals without admitting lower-confidence T2 repairs.

**Architecture:** The research analyzer already emits T3 signals and the strategy already routes by signal kind. This slice changes the confirmation signal-kind set and user-facing registry copy, with tests proving T3 is allowed and T2 remains excluded.

**Tech Stack:** Python strategy classes, pytest with monkeypatch, existing strategy registry metadata, fixed local A-share backtest fixtures.

---

## File Structure

- Modify `src/ai_trade_system/strategies/popular.py`: add `CHAN_STRUCT_BUY_T3` and `CHAN_STRUCT_SELL_T3` to confirmation-mode allowed kinds.
- Modify `src/ai_trade_system/strategy_registry.py`: clarify Chan strategy description and `signal_mode` parameter guidance.
- Modify `tests/test_builtin_popular_strategies.py`: add TDD tests for T3 confirmation-mode entry/exit and preserve T2 exclusion.
- Create `docs/qa/2026-06-19-chan-confirmation-t3-consumption-qa.md`: record tests, benchmark results, and browser QA.
- Modify `docs/context/pending-features.md`: move this slice into completed baseline and record next Chan follow-up.

## Task 1: T3 Confirmation-Mode RED Tests

- [ ] Add a test where patched `scan_chan_structure` returns `CHAN_STRUCT_BUY_T3` on bar 2 and `CHAN_STRUCT_SELL_T3` on bar 4.
- [ ] Instantiate `ChanStructureStrategy(signal_mode="confirmation", min_signal_score=30)`.
- [ ] Assert expected signals are `["buy", "sell"]` with T3 reasons.
- [ ] Run the test and confirm it fails because current confirmation mode excludes T3.

## Task 2: Minimal Strategy Change

- [ ] Add `CHAN_STRUCT_BUY_T3` and `CHAN_STRUCT_SELL_T3` to `CHAN_CONFIRMATION_SIGNAL_KINDS`.
- [ ] Re-run the new test and existing signal-mode tests.
- [ ] Confirm T2-only test still returns no confirmation-mode signals.

## Task 3: Metadata And Sedimentation

- [ ] Update Chan strategy description and `signal_mode` guidance to explain confirmation mode includes divergence confirmation and T3 pivot retest signals.
- [ ] Update `docs/context/pending-features.md`.
- [ ] Create QA record with fixed benchmark results.

## Task 4: Verification And Commit

- [ ] Run `PYTHONPATH=src python -m pytest`.
- [ ] Run `cd frontend && npm test -- --run`.
- [ ] Run `cd frontend && npm run build`.
- [ ] Run fixed benchmark backtests on the two persisted fixtures.
- [ ] Capture browser screenshot of Strategy Workshop.
- [ ] Commit all related changes.
