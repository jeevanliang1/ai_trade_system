# Chan Strict Segment Rules Design

Date: 2026-06-19

## Goal

Replace the current overlapping three-stroke sliding-window segment builder with a stricter first-cut Chan segment split/break/rebuild model while preserving existing research preview, chart overlay, Signal Radar, and `ChanStructureStrategy` contracts.

## Context

The previous Chan core slice added `ChanSegment`, recursive pivots, and divergence/confirmation signals. Its segment builder is deliberately simple: every three consecutive strokes whose first and third strokes share direction becomes a segment. That creates useful observable structure, but it also creates overlapping segments such as `1-19`, `7-25`, `13-29`, which is not a realistic segment layer.

This slice keeps the analyzer pure Python and daily-bar only, but makes segment formation more stateful:

- A segment starts from a directional three-stroke structure.
- While later strokes continue in the same segment direction without a confirmed break, the segment extends instead of creating a new overlapping segment.
- An opposite-direction stroke confirms a break only when it violates the current segment's protected extreme.
- After a break, the broken segment is locked and the next candidate segment is rebuilt from the break stroke instead of from every sliding window.

## Scope

Backend analyzer:

- Modify `src/ai_trade_system/research/chan_structure.py`.
- Extend `ChanSegment` with enough metadata to prove stricter formation:
  - `start_stroke_index`
  - `end_stroke_index`
  - `break_stroke_index`
- Replace `_build_segments` internals with non-overlapping stateful construction.
- Keep `broken_by_next` for existing overlay compatibility.
- Update recursive pivot and divergence code only as needed to consume the stricter segment list.

Serialization and UI:

- Add the new segment metadata to `ChanSegmentOverlay`.
- Add the new fields to frontend `ChanSegmentOverlay` type.
- The existing `缠论线段` chart series can continue using start/end day and price. No new visual control is needed.

Strategy:

- `ChanStructureStrategy` still consumes `scan_chan_structure` without parameter changes.
- No threshold tuning in this slice.
- Existing divergence/confirmation signal names remain unchanged.

Verification:

- Add tests proving:
  - deep Chan samples now produce non-overlapping segment ranges;
  - at least one segment can be marked broken with a recorded break stroke;
  - recursive pivots still include segment-level pivots after stricter segment construction;
  - overlay serialization exposes break metadata.
- Run the fixed 中芯国际 and 五粮液 benchmark backtests and record comparable results.
- Browser QA is required only because the overlay payload/type changes, even though the visible chart control does not.

## First-Cut Rules

### Candidate Segment

A candidate segment is recognized from three consecutive strokes where the first and third strokes share direction. The segment direction is that shared direction.

### Protected Extreme

The protected extreme is the segment range that an opposite stroke must violate to break it:

- Up segment: protected low is the segment low.
- Down segment: protected high is the segment high.

### Extension

If a later stroke has the same direction as the active segment and makes progress in that direction, the active segment extends:

- Up segment extends when the stroke end price is above the current segment end price or its high is above the current segment high.
- Down segment extends when the stroke end price is below the current segment end price or its low is below the current segment low.

Range, end fractal, end stroke index, stroke count, and energy are recalculated after extension.

### Break And Rebuild

If a later opposite-direction stroke violates the protected extreme, the active segment is locked with:

- `broken_by_next=True`
- `break_stroke_index=<that stroke index>`

The builder then resumes scanning from the break stroke index. This gives the next segment a chance to form from the actual break/rebuild point rather than from overlapping windows inside the old segment.

### Compatibility

Existing callers may continue reading:

- `start`
- `end`
- `direction`
- `high`
- `low`
- `stroke_count`
- `energy`
- `broken_by_next`

New metadata is additive.

## Out Of Scope

- Full original Chan segment splitting edge cases.
- MACD area, volume divergence, or zero-axis rules.
- Multi-timeframe nested segment confirmation.
- Strategy threshold tuning.
- Live trading.

## Acceptance Criteria

- `scan_chan_structure(...).segments` no longer contains overlapping sliding-window starts on the deep synthetic sample.
- At least one synthetic break scenario produces `broken_by_next=True` and a non-null `break_stroke_index`.
- Segment-level recursive pivots still appear when the stricter segments overlap.
- Preview overlay and frontend types expose segment stroke indexes and break stroke indexes.
- Fixed benchmark backtests for 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` are recorded in QA docs.
