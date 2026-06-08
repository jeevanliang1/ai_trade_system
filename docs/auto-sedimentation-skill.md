---
name: auto-sedimentation
description: Use after accepted project changes, user corrections, recurring workflow discoveries, PRD/rule updates, or task wrap-up to decide what project knowledge should be captured under docs/ and how to keep AGENTS.md, PRD, rules, skills, QA, and runbooks current without creating documentation noise.
---

# Auto Sedimentation

## Purpose

Turn useful work-session knowledge into durable project memory. Capture only information that will help future humans or AI agents make better decisions in this repository.

## When To Run

Run this workflow at every task wrap-up. It is a close-out gate, not optional cleanup. If nothing needs to be captured, explicitly state that conclusion in the final response.

Capture knowledge when:
- The user accepted or corrected a project rule, workflow, naming convention, product constraint, or verification expectation.
- A repeated workflow became reusable.
- A product requirement changed, a PRD gap was resolved, or a new acceptance criterion appeared.
- A technical decision was made with meaningful tradeoffs.
- A test, validation pattern, failure mode, or risk should be remembered.
- A future conversation would need compact handoff context.

Do not capture:
- Temporary debugging chatter.
- Secrets or credentials.
- One-off implementation details already obvious from code.
- Vague lessons without action value.

## Classification

| Type | Primary location |
| --- | --- |
| Future AI/team rule | `docs/rules/` and concise bullet in `AGENTS.md` |
| Product requirement | `docs/prd/` |
| Reusable AI workflow | `docs/skills/` |
| Decision record | `docs/decisions/YYYY-MM-DD-topic.md` |
| Prompt/template | `docs/prompts/` |
| Verification knowledge | `docs/qa/` |
| Operational procedure | `docs/runbooks/` |
| Stable project context | `docs/context/` |
| New-conversation handoff | `docs/context/` or `docs/prompts/` |

## Workflow

1. Check whether the new information is durable, reusable, and not already captured.
2. Choose one primary location.
3. Update the smallest useful existing document; create a new focused file only when needed.
4. If it changes future AI behavior, update `AGENTS.md`.
5. If it changes product behavior, update the active PRD/status file.
6. Run lightweight verification, such as checking files exist and markdown is non-empty.
7. Commit the sedimentation change separately if this repo requires commit discipline.
8. In the final response, include: `沉淀：已更新 ...` or `沉淀：无需新增文档，原因是 ...`。
