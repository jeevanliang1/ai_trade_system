# Autonomous Agent Layer Design

Date: 2026-06-20

## Goal

Upgrade the current AI Command Center from a tool-dispatch surface into a repo-local autonomous Agent layer that can manage memory, skills, and planner policy, then use those assets to explain how it will complete a user request before and during execution.

## Persistence Decision

Use local JSON files under `data/agent/` for the first implementation:

- `data/agent/memory.json`
- `data/agent/skills.json`
- `data/agent/policy.json`

This is enough for current single-user local operation, transparent diffs, easy backup, and deterministic tests. Do not install a database for this slice. Revisit SQLite only when the system needs concurrent writes, full-text search beyond simple tag/source filters, or large run-history queries.

## Backend Scope

Create three focused services:

- `AgentMemoryStore`: CRUD for structured memories with type, scope, tags, source, confidence, enabled state, and optional expiry.
- `AgentSkillStore`: CRUD for reusable task skills with trigger keywords, allowed tools, required confirmations, ordered steps, and output format.
- `AgentPolicyStore`: stores default planner settings, blocked intents, max step count, and per-tool permission overrides.

Create `AgentPlanPreviewService` to combine prompt, memory, skills, policy, and existing tool registry into a preview envelope:

- intent
- selected skill
- matched memories
- planned steps with reasons and permission levels
- stop conditions
- final output expectation

The preview service does not execute tools. It is an explainable planning layer that can later feed `AgentOrchestrator`.

## Frontend Scope

Add a new React workspace: `Agent治理`.

The page has four operating areas:

- Memory table and editor for enabling, editing, and creating memories.
- Skill table and editor for trigger terms, allowed tools, and step definitions.
- Planner policy panel for max steps, blocked intents, and tool permission overrides.
- Plan preview panel where a user enters a prompt and sees selected skill, matched memories, steps, reasons, and stop conditions.

Use the current workbench visual system: compact panels, tabs, toolbar buttons, status pills, dense tables, and no decorative landing-page treatment.

## Built-In Defaults

Seed the first-run JSON files with:

- Memory: weekly scan requests should reuse persisted automation weekly results rather than re-running scans.
- Skill: `weekly_scan_share`, mapping weekly scan/share prompts to `automation.weekly_result -> research.batch_fundamental -> share.weixin`.
- Policy: live-trading and broker-order intents are blocked; external research batch tools require confirmation; default max steps is 8.

## Safety Boundaries

- No live trading, broker order, or real account operation can be enabled by memory or skill edits.
- Unknown tools are ignored in previews and execution plans.
- Confirm-level tools remain confirm-level unless policy explicitly makes them stricter; this implementation must not allow policy to downgrade blocked live-trading behavior.
- Frontend edits are local configuration changes only; they do not execute research, backtests, paper trading, or sharing by themselves.

## Acceptance Criteria

- API can list, create, update, and delete memories.
- API can list, create, update, and delete skills.
- API can read and update planner policy.
- API can preview a plan for “给我这周股票扫描结果并完成分享的最终结果” and select `weekly_scan_share`.
- The preview includes the three expected steps and marks `research.batch_fundamental` as confirm-level.
- The React page exposes Memory, Skills, Planner Policy, and Plan Preview areas.
- Existing Agent task execution remains compatible with current tools and reports.
