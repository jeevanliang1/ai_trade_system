# Auto Sedimentation Close-Out Rule

Every accepted or explicitly requested task must run a sedimentation audit before the final response.

Sedimentation audit is part of task close-out, equivalent in importance to testing and committing when those apply. It is not optional cleanup.

Rules that affect future AI default behavior must be synchronized to the root `AGENTS.md` in concise form.

Broad product work triggered by a persona, requirement, replicated page, or feature set must keep `docs/context/pending-features.md` current. Completed items must be removed from the pending list, new pending items must be added before work starts, and exactly one next recommended feature must be recorded for future "continue" or "what next" prompts.

Every task close-out should include a headless Chrome screenshot for user acceptance when a browser-renderable project surface is available. If no screenshot can be captured, the final response must say why, using an explicit not-applicable or blocker note.

The final response must report the sedimentation result using one of these forms:

- `沉淀：已更新 ...`
- `沉淀：无需新增文档，原因是 ...`
