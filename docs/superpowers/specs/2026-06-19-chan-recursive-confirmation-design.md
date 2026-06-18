# Chan recursive confirmation design

Date: 2026-06-19

## Goal

Deepen `research.chan_structure` so the core analyzer exposes more useful Chan structure before downstream strategy tuning:

- segment-level structure remains the higher-level component above strokes;
- recursive pivots can extend beyond a fixed three-component window when later stroke/segment components keep overlapping the center zone;
- divergence records carry the pivot context they occur around;
- divergence signals distinguish watchable pending signals from later confirmation signals after repair or structural break.

## Non-goals

- No live trading behavior.
- No strategy parameter tuning in this slice.
- No attempt to implement a full formal Chan parser; this remains a deterministic, testable research scanner for daily-bar backtests.

## Behavioral Contract

1. `_build_recursive_pivots` should produce stroke-level and segment-level centers with `component_count >= 3`; when later components continue overlapping the current center zone, a pivot may extend to `component_count > 3`.
2. `ChanDivergence` should include nearest recursive pivot context where available: `pivot_level`, `pivot_start_index`, `pivot_end_index`, `pivot_low`, and `pivot_high`.
3. A base divergence signal that has not confirmed yet should remain watchable on the latest bar with a `watch` tag and plain-language waiting reason.
4. A confirmation signal should fire after price repair/break threshold or after the divergent segment has been structurally broken by the next opposite stroke.
5. API overlays should expose the added divergence pivot context for React chart layers and future visual annotations.

## Verification

- Add focused tests in `tests/test_research_signals.py` for extended recursive pivots, divergence pivot context, overlay fields, and pending-to-confirm signal semantics.
- Run targeted research tests first, then full `python -m pytest`.
- Because this changes strategy-affecting research signals, run fixed 中芯国际 and 五粮液 benchmarks for `ChanStructureStrategy`.
