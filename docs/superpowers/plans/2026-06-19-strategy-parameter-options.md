# Strategy Parameter Options Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render enum-like strategy parameters from backend metadata as select and multi-select controls.

**Architecture:** Extend the strategy registry parameter metadata with `options` and `multiple`, let the existing FastAPI dataclass serialization expose those fields, and update the shared React `ParameterForm` to render single-select and compact checkbox multi-select controls while preserving string-valued strategy params.

**Tech Stack:** Python dataclasses/Pydantic, FastAPI service serialization, React + TypeScript + Testing Library, existing fixed A-share benchmark fixtures.

---

## File Structure

- Modify `src/ai_trade_system/strategy_registry.py`: add option metadata fields and populate enum-like Chan strategy parameters.
- Modify `src/ai_trade_system/api/schemas.py`: include option metadata in API view schemas.
- Modify `tests/test_strategy_registry.py`: assert option metadata from `inspect_strategy_parameters`.
- Modify `tests/test_api_routes.py`: assert `/api/strategies` serializes option metadata.
- Modify `frontend/src/types.ts`: add `options` and `multiple` to `StrategyParameter`.
- Modify `frontend/src/components/ParameterForm.tsx`: render metadata-backed single select and multi-select controls.
- Modify `frontend/src/components/ParameterForm.test.tsx`: add RED/GREEN tests for single and multi-select behavior.
- Create `docs/qa/2026-06-19-strategy-parameter-options-qa.md`: record TDD, verification, benchmark, and browser evidence.
- Modify `docs/context/pending-features.md`: move this feature to completed baseline and record the next recommended feature.

## Task 1: RED Tests

- [x] Add backend registry assertions:

```python
assert params["signal_mode"].options == ("all", "confirmation", "structure")
assert params["signal_mode"].multiple is False
assert params["allowed_point_types"].options == (
    "all",
    "first-buy",
    "first-sell",
    "second-buy",
    "second-sell",
    "third-buy",
    "third-sell",
)
assert params["allowed_point_types"].multiple is True
assert params["allowed_levels"].options == ("all", "segment", "stroke", "fractal")
assert params["allowed_levels"].multiple is True
```

- [x] Add API route test that finds `ChanStructureStrategy` in `/api/strategies` and asserts `signal_mode.options`, `allowed_point_types.multiple`, and `allowed_levels.options`.
- [x] Add React `ParameterForm` test for single-select metadata:

```tsx
const parameters = [{ name: "signal_mode", annotation: "str", default: "all", options: ["all", "confirmation", "structure"] }];
```

Changing the select to `confirmation` should publish `{ signal_mode: "confirmation" }`.

- [x] Add React `ParameterForm` test for multi-select metadata:

```tsx
const parameters = [{
  name: "allowed_point_types",
  annotation: "str",
  default: "all",
  options: ["all", "first-buy", "second-buy", "third-buy"],
  multiple: true
}];
```

Clicking `second-buy` and `third-buy` should publish `{ allowed_point_types: "second-buy,third-buy" }`; clicking `all` should publish `{ allowed_point_types: "all" }`.

- [x] Run targeted tests and confirm RED:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_structure_strategy_metadata_and_parameter_guidance \
  tests/test_api_routes.py::test_strategies_route_exposes_enum_parameter_options -q
cd frontend && npm test -- --run src/components/ParameterForm.test.tsx
```

## Task 2: Backend Metadata

- [x] Extend `StrategyParameter` and `ParameterGuidance` with:

```python
options: tuple[str, ...] = ()
multiple: bool = False
```

- [x] Copy `guidance.options` and `guidance.multiple` in `inspect_strategy_parameters(...)`.
- [x] Add option metadata to `signal_mode`, `allowed_point_types`, and `allowed_levels` guidance.
- [x] Extend `StrategyParameterView` with:

```python
options: list[str] = Field(default_factory=list)
multiple: bool = False
```

- [x] If needed, make `_serialize(...)` handle tuples as list-like values.
- [x] Run backend targeted tests and confirm GREEN.

## Task 3: React Controls

- [x] Add `options?: string[]` and `multiple?: boolean` to frontend `StrategyParameter`.
- [x] Keep current single-select behavior for `options` with no `multiple`.
- [x] Add a multi-select branch before the single-select branch.
- [x] Implement helpers:

```tsx
function selectedOptions(control: Control, value: unknown): string[]
function nextMultiValue(control: Control, currentValue: unknown, option: string, checked: boolean): string
```

- [x] Render checkbox options with stable labels, compact styling, and `aria-label={`${label} ${option}`}`.
- [x] Run frontend targeted test and confirm GREEN.

## Task 4: Benchmarks And QA

- [x] Run default `ChanStructureStrategy` fixed benchmarks on 中芯国际 and 五粮液.
- [x] Record benchmark rows and interpretation in `docs/qa/2026-06-19-strategy-parameter-options-qa.md`.
- [x] Update `docs/context/pending-features.md`: move enum parameter controls into completed baseline and set next recommended feature to `VolumeConfirmedMomentumStrategy` threshold/exit tuning.

## Task 5: Full Verification, Browser QA, Commit

- [x] Run `PYTHONPATH=src python -m pytest`.
- [x] Run `cd frontend && npm test -- --run`.
- [x] Run `cd frontend && npm run build`.
- [x] Run `git diff --check`.
- [x] Start `./scripts/run_app.sh`, select `缠论结构策略`, verify `信号模式` is a select and `买卖点类型过滤` / `结构层级过滤` render as checkbox groups, then capture a screenshot.
- [ ] Commit all related changes with a focused message.
