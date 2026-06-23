# Automation Run History Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show recent automation run history and failure diagnostics in the `自动任务` React workspace without reading JSON/JSONL files.

**Architecture:** Reuse the existing automation `runs.jsonl` store and `AutomationStatus` API payload. Add compact recent-run and diagnostics fields to the status response, then render them in `AutomationPage`.

**Tech Stack:** Python dataclasses and JSONL store, FastAPI service serialization, React + TypeScript + Vitest.

---

## Tasks

### Task 1: Backend Status Payload

- [ ] Write failing tests that expect `/api/automation/status` and `AutomationService.status()` to include `recent_runs` and `diagnostics`.
- [ ] Implement `AutomationStatus.recent_runs` and `AutomationStatus.diagnostics`.
- [ ] Add service helpers that return the newest run records first and derive failure/missing-data diagnostics.
- [ ] Run targeted pytest.

### Task 2: Frontend Workspace

- [ ] Write failing `AutomationPage` tests for recent run history and failure diagnostics.
- [ ] Extend `AutomationStatus` TypeScript types.
- [ ] Render a compact diagnostics panel and recent-run list in the automation workspace.
- [ ] Run targeted frontend tests.

### Task 3: Verification And Sedimentation

- [ ] Run full Python and frontend verification.
- [ ] Capture desktop and mobile screenshots of `自动任务`.
- [ ] Update docs, QA notes, and `pending-features.md`.
