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

## Close-Out

Final responses after relevant work must mention whether the pending list changed and what the next recommended feature is.

