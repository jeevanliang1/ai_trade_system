# Workbench IA Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the React workbench page relationships and top-level actions easier to understand by separating navigation, configuration, and execution.

**Architecture:** Keep the existing React shell and route map. Reframe the side navigation into grouped workflow stages, replace the global backtest action with a contextual next-step navigation button, and narrow Strategy Workshop output to signal/research preview while leaving full backtest execution and result review to Backtest Center.

**Tech Stack:** React, TypeScript, Vite, Vitest, Testing Library, existing CSS.

---

### Task 1: Shell Navigation And Top Bar

**Files:**
- Modify: `frontend/src/shell/AppShell.tsx`
- Modify: `frontend/src/shell/AppShell.test.tsx`
- Modify: `frontend/src/shell/AppShell.tasks.test.tsx`
- Modify: `frontend/src/styles.css`

- [x] Add failing tests that prove navigation is grouped by workflow stage and that the top bar no longer exposes a direct global backtest run button.
- [x] Implement grouped side navigation using the existing page ids.
- [x] Replace the top bar action with a contextual next-step button that changes `activePage`.
- [x] Verify with `npm test -- AppShell.test.tsx AppShell.tasks.test.tsx --run`.

### Task 2: Strategy Workshop Scope Reduction

**Files:**
- Modify: `frontend/src/pages/StrategyPage.tsx`
- Modify: `frontend/src/pages/StrategyPage.test.tsx`

- [x] Add failing tests that Strategy Workshop no longer renders full backtest result tabs or backtest-derived comparison tables.
- [x] Keep strategy selection, parameters, signal preview, research preview, chart controls, and source editing.
- [x] Replace the old result-tab area with concise signal-preview metrics and a table of generated signals.
- [x] Verify with `npm test -- StrategyPage.test.tsx --run`.

### Task 3: Documentation And Verification

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/context/pending-features.md`

- [x] Record the durable rule that global shell controls should navigate or summarize context, not silently execute page-owned tasks.
- [x] Move the pending IA cleanup item into the implemented baseline once complete.
- [x] Run `PYTHONPATH=src python -m pytest`, `npm test -- --run`, `npm run build`, `./scripts/run_all.sh --check`, and `git diff --check`.
- [x] Capture desktop and mobile headless screenshots for user acceptance.
