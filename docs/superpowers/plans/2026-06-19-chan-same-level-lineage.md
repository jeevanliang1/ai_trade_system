# Chan Same-Level Lineage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable same-level segment identity and explicit buy/sell point lineage metadata to Chan structure analysis outputs.

**Architecture:** Keep the core analyzer in `src/ai_trade_system/research/chan_structure.py`, extend the shared `ResearchSignal` and overlay dataclasses in `research/models.py`, and update `research/service.py` plus frontend TypeScript types to pass the new fields through. Tests are added before production code and fixed benchmark backtests remain the acceptance standard.

**Tech Stack:** Python dataclasses, pytest, existing FastAPI dataclass serialization, React TypeScript type definitions, local fixed CSV backtests.

---

## File Structure

- Modify `src/ai_trade_system/research/models.py`: add `metadata` to `ResearchSignal`; add same-level fields to `ChanSegmentOverlay`.
- Modify `src/ai_trade_system/research/chan_structure.py`: assign segment `sequence_index` and `lineage_id`; populate metadata and reason suffixes for T1/T2/T3/confirm signals.
- Modify `src/ai_trade_system/research/service.py`: pass segment identity into overlay payload.
- Modify `frontend/src/types.ts`: expose `ResearchSignal.metadata` and segment identity fields.
- Modify `tests/test_research_signals.py`: add RED tests for metadata, lineage, and overlay fields.
- Create `docs/qa/2026-06-19-chan-same-level-lineage-qa.md`: record TDD, verification, fixed benchmarks, browser QA.
- Modify `docs/context/pending-features.md`: move the completed lineage slice to baseline and record the next strategy-development item.

## Task 1: RED Tests

- [x] Add `test_chan_structure_segments_carry_same_level_sequence_and_lineage`.
- [x] Add `test_chan_structure_divergence_signals_carry_hierarchy_metadata`.
- [x] Add `test_chan_structure_second_and_third_points_carry_pivot_lineage`.
- [x] Extend overlay test to assert `level`, `sequence_index`, and `lineage_id`.
- [x] Run targeted tests and confirm they fail because metadata/lineage fields are missing.

## Task 2: Research Models And Overlay

- [x] Add `metadata: dict[str, object] = field(default_factory=dict)` to `ResearchSignal`.
- [x] Add `level`, `sequence_index`, and `lineage_id` to `ChanSegmentOverlay`.
- [x] Add matching fields to frontend `ResearchSignal` and `ChanSegmentOverlay` types.
- [x] Update `_chan_structure_overlay` to emit the new segment fields.

## Task 3: Analyzer Metadata

- [x] Add same-level identity fields to `ChanSegment`.
- [x] Assign deterministic segment identity in `_build_segments`.
- [x] Add helpers for segment lineage, pivot metadata, and readable metadata suffixes.
- [x] Populate metadata/reason/tags for T1 divergence watch and confirmation signals.
- [x] Populate metadata/reason/tags for T2 and T3 signals.
- [x] Run targeted tests and keep them green.

## Task 4: QA, Benchmarks, Browser, Commit

- [x] Run fixed benchmark backtests on persisted 中芯国际 and 五粮液 fixtures.
- [x] Write QA record with benchmark tables and interpretation.
- [x] Update pending features and next recommended feature.
- [x] Run `PYTHONPATH=src python -m pytest`.
- [x] Run `cd frontend && npm test -- --run`.
- [x] Run `cd frontend && npm run build`.
- [x] Run `git diff --check`.
- [x] Capture React browser QA screenshot.
- [x] Commit all related changes.
