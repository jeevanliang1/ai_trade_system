# Chan Lower-Level Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add offensive lower-level discovery entries to `ChanMultiLevelReversalStrategy` and benchmark them against daily-only and conservative multi-level modes.

**Architecture:** Preserve the existing daily-loop strategy. Add an `entry_mode` enum that keeps old `daily_confirmed` behavior as default and adds `lower_level_discovery`, where confirm-level buy signals can open positions when daily background is not bearish and risk-level context does not block the trade.

**Tech Stack:** Python strategy core, CodeGraph-indexed source, pytest, existing backtest engine, managed A-share qfq fixtures, React/FastAPI screenshot workflow.

---

## File Structure

- Modify `src/ai_trade_system/strategies/popular.py`: add `CHAN_ENTRY_MODES`, validate `entry_mode`, split lower-level discovery buy logic into a helper.
- Modify `src/ai_trade_system/strategy_registry.py`: expose `entry_mode` enum options and Chinese guidance.
- Modify `tests/test_chan_multilevel_reversal_strategy.py`: add TDD coverage for discovery buys, daily bearish blocking, risk blocking, and invalid config.
- Modify `tests/test_strategy_registry.py`: assert `entry_mode` options are discoverable.
- Create `docs/qa/2026-06-21-chan-lower-level-discovery-qa.md`: record tests, 8-stock data coverage, benchmark results, decision, and screenshots.
- Modify `docs/context/pending-features.md`: mark discovery mode completion and keep next recommended data-source follow-up if still justified.

## Task 1: Add Failing Strategy Tests

- [ ] **Step 1: Add `entry_mode` validation and discovery tests**

Add tests to `tests/test_chan_multilevel_reversal_strategy.py`:

```python
with pytest.raises(ValueError, match="entry_mode"):
    ChanMultiLevelReversalStrategy("000001", entry_mode="bad")
```

Add a test where daily has no buy signal but `60m` emits `CHAN_STRUCT_BUY_CONFIRM`, risk `30m` is neutral, `entry_mode="lower_level_discovery"`, and the strategy emits a buy with `DISCOVERY_60M`.

Add a test where daily emits a high-score sell and `60m` emits a buy; the strategy emits no buy.

Add a test where risk `30m` emits a high-score sell and `60m` emits a buy; the strategy emits no buy.

- [ ] **Step 2: Verify RED**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected before implementation: failures because `entry_mode` is not accepted and discovery buys are not implemented.

## Task 2: Implement `entry_mode`

- [ ] **Step 1: Add constants and validation**

In `src/ai_trade_system/strategies/popular.py`, add:

```python
CHAN_ENTRY_MODES = ("daily_confirmed", "lower_level_discovery")
```

Add an `entry_mode: str = "daily_confirmed"` constructor parameter, validate it, and store `self.entry_mode`.

- [ ] **Step 2: Add lower-level discovery branch**

In `on_bar`, after daily buy handling determines that no daily buy exists, call a helper when `self.entry_mode == "lower_level_discovery"`.

The helper should:

```python
def _lower_level_discovery_buy(self, daily_sell, confirm_buy, risk_signal, confirm_result, bar):
    if daily_sell is not None or confirm_buy is None or risk_signal is not None:
        return self._time_exit_if_needed(bar)
    target_units = self._cap_target_units(confirm_buy, confirm_result, self._target_units_for_signal(confirm_buy))
    return self._emit_position_delta_or_time_exit(
        target_units,
        bar,
        confirm_buy.price,
        f"chan_multilevel:DISCOVERY_{_level_label(self.confirm_timeframe)}:{confirm_buy.kind}:{confirm_buy.reason}",
    )
```

- [ ] **Step 3: Verify GREEN**

Run:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Expected: all Chan multilevel tests pass.

## Task 3: Expose Registry Metadata

- [ ] **Step 1: Add registry guidance**

In `src/ai_trade_system/strategy_registry.py`, add `entry_mode` guidance with options:

```python
("daily_confirmed", "lower_level_discovery")
```

Use Chinese display text and explain that `lower_level_discovery` lets lower-level high-confidence buy points open exploratory positions before daily buy points.

- [ ] **Step 2: Add registry test assertion**

In `tests/test_strategy_registry.py`, extend the Chan multilevel metadata test to assert `entry_mode` includes both options.

- [ ] **Step 3: Verify registry tests**

Run:

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Expected: pass.

## Task 4: Benchmark Expanded 8-Stock Universe

- [ ] **Step 1: Ensure local fixtures**

Use managed qfq daily, `60m`, `30m`, and `15m` fixtures for:

```text
688981/SSE
000858/SZSE
601318/SSE
600901/SSE
600989/SSE
603986/SSE
688733/SSE
688072/SSE
```

If new symbols are missing, use `data_manager.update_stock_data` for `daily`, `60m`, `30m`, and `15m` over `20230619` to `20260619`.

- [ ] **Step 2: Run benchmark matrix**

Run daily baseline, conservative `daily_confirmed`, and offensive `lower_level_discovery` variants through `run_backtest` and `calculate_backtest_metrics`.

- [ ] **Step 3: Record QA**

Create `docs/qa/2026-06-21-chan-lower-level-discovery-qa.md` with coverage, aggregate metrics, per-symbol metrics, and interpretation.

## Task 5: Full Verification And Acceptance

- [ ] **Step 1: Run full verification**

Run:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
npm --prefix frontend test
npm --prefix frontend run build
```

- [ ] **Step 2: Capture screenshots**

Start `./scripts/run_app.sh`, capture React screenshots with `scripts/capture_app_screenshots.mjs`, and capture an interactive Strategy Workshop screenshot showing `entry_mode` options.

- [ ] **Step 3: Sedimentation audit**

Apply `docs/auto-sedimentation-skill.md`, keep pending features current, and include the sedimentation line in the final response.
