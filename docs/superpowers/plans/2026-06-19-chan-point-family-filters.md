# Chan Point-Family Filters Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add metadata-backed point-family and structure-level filters to `ChanStructureStrategy`.

**Architecture:** Keep the Chan analyzer unchanged and add filter parsing plus matching inside `src/ai_trade_system/strategies/popular.py`. Use existing `ResearchSignal.metadata` as the stable contract, expose Chinese guidance through `strategy_registry.py`, and verify behavior with patched deterministic research signals before running fixed-stock benchmarks.

**Tech Stack:** Python strategy classes, pytest monkeypatch, existing `ResearchSignal`, local A-share CSV fixtures, React + FastAPI strategy registry surface.

---

## File Structure

- Modify `tests/test_builtin_popular_strategies.py`: add metadata support to the test signal factory and failing tests for point, level, armed confirmation, and validation behavior.
- Modify `tests/test_strategy_registry.py`: assert defaults and Chinese guidance for the two new parameters.
- Modify `src/ai_trade_system/strategies/popular.py`: add allowed token constants, comma-list parser, constructor params, and signal metadata checks.
- Modify `src/ai_trade_system/strategy_registry.py`: add Chinese parameter guidance for `allowed_point_types` and `allowed_levels`.
- Create `docs/qa/2026-06-19-chan-point-family-filters-qa.md`: record RED/GREEN, full verification, benchmark tables, and browser evidence.
- Modify `docs/context/pending-features.md`: move the completed filter item into the baseline and keep exactly one next recommended feature.

## Task 1: RED Tests

- [x] Add `metadata: dict[str, object] | None = None` to `make_research_signal(...)` and pass `metadata=metadata or {}` into `ResearchSignal`.
- [x] Add `test_chan_structure_strategy_filters_allowed_point_types`:
  - patched scan emits a second-buy T2 and later third-buy T3;
  - strategy uses `allowed_point_types="third-buy"`;
  - expected output is only the third-buy trade.
- [x] Add `test_chan_structure_strategy_filters_allowed_levels`:
  - patched scan emits a segment-level first-buy confirmation and later stroke-level third-buy;
  - strategy uses `allowed_levels="stroke"`;
  - expected output is only the stroke-level T3 trade.
- [x] Add `test_chan_structure_strategy_armed_watch_respects_confirmation_filters`:
  - patched scan emits a T1 divergence watch and later second-buy confirmation;
  - strategy uses `allowed_point_types="third-buy"`;
  - expected output is no trade.
- [x] Add validation tests for `allowed_point_types="bad-token"` and `allowed_levels="bad-level"`.
- [x] Add registry assertions that defaults are `all` and Chinese guidance mentions accepted tokens.
- [x] Run targeted tests and confirm they fail for missing constructor parameters or missing registry guidance:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_filters_allowed_point_types \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_filters_allowed_levels \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_armed_watch_respects_confirmation_filters \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_allowed_point_types \
  tests/test_builtin_popular_strategies.py::test_chan_structure_strategy_rejects_unknown_allowed_levels \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_strategy_registry.py::test_chan_structure_strategy_registry_exposes_tuned_default_score \
  -q
```

## Task 2: Minimal Implementation

- [x] Add constants:

```python
CHAN_POINT_TYPES = {
    "first-buy",
    "first-sell",
    "second-buy",
    "second-sell",
    "third-buy",
    "third-sell",
}
CHAN_LEVELS = {"segment", "stroke", "fractal"}
```

- [x] Add constructor parameters after `signal_mode`:

```python
allowed_point_types: str = "all",
allowed_levels: str = "all",
```

- [x] Parse and store normalized filter sets:

```python
self.allowed_point_types = allowed_point_types
self.allowed_levels = allowed_levels
self.allowed_point_type_set = _parse_chan_filter_values(allowed_point_types, CHAN_POINT_TYPES, "allowed_point_types")
self.allowed_level_set = _parse_chan_filter_values(allowed_levels, CHAN_LEVELS, "allowed_levels")
```

- [x] Add `_signal_filters_allow(signal)` so non-`all` filters require matching `signal.metadata["point_type"]` and `signal.metadata["level"]`.
- [x] Apply `_signal_filters_allow(signal)` to direct candidate emission and armed-watch confirmation emission.
- [x] Do not apply the filter inside `_arm_watch(signal)`, because watch signals are setup state rather than trade emission.

## Task 3: Registry Guidance

- [x] Add `allowed_point_types` guidance:
  - display name `买卖点类型过滤`
  - description lists `all` and point-type tokens
  - increase/decrease copy states this is not numeric tuning.
- [x] Add `allowed_levels` guidance:
  - display name `结构层级过滤`
  - description lists `all`, `segment`, `stroke`, and `fractal`
  - increase/decrease copy states this is not numeric tuning.
- [x] Run the targeted tests again and confirm they pass.

## Task 4: Benchmarks And QA

- [x] Run fixed benchmarks for the default config and filter comparison configs on both persisted fixtures.
- [x] Record final equity, strategy return, benchmark return, excess return, max drawdown, trade count, win rate, and profit factor in `docs/qa/2026-06-19-chan-point-family-filters-qa.md`.
- [x] Update `docs/context/pending-features.md` by moving the completed filter feature into the baseline and setting the next recommended feature to enum/select controls for strategy parameters.

## Task 5: Final Verification And Commit

- [x] Run `PYTHONPATH=src python -m pytest`.
- [x] Run `cd frontend && npm test -- --run`.
- [x] Run `cd frontend && npm run build`.
- [x] Run `git diff --check`.
- [x] Start `./scripts/run_app.sh`, open `http://127.0.0.1:5173/`, verify the React workbench renders with strategy parameters available, and capture a screenshot.
- [x] Commit all related changes with a focused message.
