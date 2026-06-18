# Strategy Parameter Options Design

## Goal

Expose enum-like strategy parameters through the strategy registry/API and render them as safe controls in React instead of free-text inputs.

## Context

`ChanStructureStrategy` now has string parameters that accept constrained token sets:

- `signal_mode`: `all`, `confirmation`, `structure`
- `allowed_point_types`: `all` or a comma-separated subset of Chan point-type tokens
- `allowed_levels`: `all` or a comma-separated subset of Chan structure levels

The registry already returns Chinese labels, descriptions, and tuning guidance, and the React `ParameterForm` already has a select branch for controls with `options`. The missing contract is that backend parameter metadata does not yet expose option lists or whether an option list is single-select or multi-select.

## Behavioral Contract

1. `StrategyParameter` gains:
   - `options: tuple[str, ...] = ()`
   - `multiple: bool = False`
2. `ParameterGuidance` gains the same metadata so existing name-based guidance can declare option lists without changing strategy constructors.
3. `inspect_strategy_parameters(...)` copies guidance options and multiplicity into every `StrategyParameter`.
4. FastAPI strategy responses include `options` and `multiple` for each parameter.
5. Frontend `StrategyParameter` type includes `options?: string[]` and `multiple?: boolean`.
6. `ParameterForm` behavior:
   - `options` plus `multiple=false` renders a native `<select>`.
   - `options` plus `multiple=true` renders a compact checkbox group.
   - Multi-select values remain strings so existing strategy constructors keep receiving `all` or comma-separated tokens.
   - Selecting `all` clears specific tokens.
   - Selecting a specific token removes `all`.
   - Clearing all specific tokens falls back to `all` when `all` is an available option.
7. The first enum metadata set covers:
   - `signal_mode`: single-select, `all`, `confirmation`, `structure`
   - `allowed_point_types`: multi-select, `all`, `first-buy`, `first-sell`, `second-buy`, `second-sell`, `third-buy`, `third-sell`
   - `allowed_levels`: multi-select, `all`, `segment`, `stroke`, `fractal`
8. Existing strategy parameter defaults and backend strategy construction behavior remain unchanged.

## Non-Goals

- Do not change `ChanStructureStrategy` trading logic, scoring, exits, filters, or defaults.
- Do not tune strategies in this slice.
- Do not add a generic custom-strategy annotation DSL for user-defined enum options.
- Do not introduce a third-party multiselect dependency.

## Verification

- TDD tests first fail because backend parameters do not expose `options/multiple` and React does not render metadata-backed multi-select controls.
- Backend tests cover registry metadata and `/api/strategies` serialization.
- Frontend tests cover single-select and multi-select parameter updates.
- Fixed 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` benchmark backtests are rerun with the default `ChanStructureStrategy` config to prove UI metadata changes do not alter strategy output.
- Full close-out verification:
  - `PYTHONPATH=src python -m pytest`
  - `cd frontend && npm test -- --run`
  - `cd frontend && npm run build`
  - `git diff --check`
  - React browser QA screenshot from `./scripts/run_app.sh`
