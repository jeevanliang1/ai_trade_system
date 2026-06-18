# Chan recursive confirmation implementation plan

Date: 2026-06-19

## Scope

Implement the next Chan analysis slice in `src/ai_trade_system/research/chan_structure.py` and the related preview overlay models.

## Steps

1. Add failing tests.
   - Extended recursive pivot can grow to more than three components.
   - Divergence records include nearest recursive pivot context.
   - Pending divergence signal has `watch` tag and waiting reason before confirmation.
   - Later repair scan produces confirmation signal with the same divergence semantics.
   - Overlay exposes divergence pivot context fields.

2. Implement recursive pivot extension.
   - Replace fixed triplet-only loops with an extension builder for stroke and segment components.
   - Preserve deterministic output.
   - Keep existing fields stable so old callers continue to work.

3. Implement divergence context and confirmation semantics.
   - Add optional pivot fields to `ChanDivergence`.
   - Attach nearest recursive pivot by overlap or containment around the current segment.
   - Add helper for confirmation reason based on repair threshold or structural break.
   - Add `watch` tag and waiting reason to unconfirmed divergence signals.

4. Expose overlay fields.
   - Update backend dataclasses and `_chan_structure_overlay`.
   - Update frontend TypeScript type for `ChanDivergenceOverlay`.

5. Verify and sediment.
   - Run targeted tests, full tests, frontend tests/build, and `git diff --check`.
   - Run fixed-stock benchmark backtests and document in `docs/qa/`.
   - Browser-check React Strategy Workshop remains available.
   - Update `docs/context/pending-features.md`.
