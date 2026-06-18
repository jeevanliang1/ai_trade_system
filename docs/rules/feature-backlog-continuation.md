# Feature Backlog Continuation Rule

When the user gives a persona, requirement, page to replicate, or feature set to build, decompose the request into concrete feature items before implementation and keep the durable pending list current.

## Trigger

Run this rule when a user asks for any of the following:

- A persona/role-driven product experience.
- A new requirement or feature set.
- A page, platform, screenshot, workflow, or functionality to replicate.
- A broad continuation request such as "继续", "下一步做什么", or "直接继续".

## Required Backlog File

Use `docs/context/pending-features.md` as the project backlog handoff.

That file must keep:

- The current feature decomposition.
- The remaining pending feature items.
- The next recommended feature to work on.
- Short context that lets a future AI continue without rediscovering the plan.

## Workflow

1. Before implementation, split the user request into small feature items and update `docs/context/pending-features.md`.
2. When a feature item is completed, remove it from the pending list before final response.
3. If new pending work is discovered during implementation, update the backlog before starting that new work.
4. After every meaningful update, record exactly one "Next recommended feature" in the backlog.
5. If the user later says "继续", asks what to do next, or asks for a recommendation, read `docs/context/pending-features.md` first and answer from the recorded next recommendation.
6. Do not treat this backlog as a replacement for tests, screenshots, or close-out sedimentation; it is an additional continuation handoff.

## Five-Feature Continuation Mode

When the user asks to continue completing the project with phrases such as "继续完成项目", default to a five-feature execution batch unless the user gives a different batch size or scope.

Required behavior:

- Pick the next feature from the current `docs/context/pending-features.md`, then update the pending list after that feature is completed before selecting the next one.
- Repeat until five meaningful feature items are completed in the same turn, or until the backlog is exhausted or a real blocker prevents safe progress.
- Keep each feature item at a meaningful product or engineering grain; do not split trivial sub-steps into separate features merely to reach five items.
- After each feature is implemented, run only the targeted verification needed for that feature, such as the directly affected backend test, frontend test, build slice, or browser interaction.
- Do not run the full project test suite after every individual feature in the batch.
- After all five features are implemented, run the broader project verification suite that is appropriate for the accumulated changes, then perform browser screenshot acceptance when a browser-renderable surface is affected.
- Each completed feature must be removed from `docs/context/pending-features.md`, and any newly discovered follow-up work must be added before selecting the next feature.
- The backlog must keep exactly one next recommended feature after every update, including the final batch close-out.

## Close-Out

Final responses after relevant work must mention whether the pending list changed and what the next recommended feature is.
