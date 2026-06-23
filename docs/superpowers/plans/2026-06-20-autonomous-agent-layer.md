# Autonomous Agent Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repo-local autonomous Agent layer with Memory, Skill, Planner Policy, and Plan Preview management.

**Architecture:** Use JSON files under `data/agent/` for first-slice persistence. Add focused backend stores and API endpoints, then add a React `Agent治理` workspace that manages memories, skills, policy, and plan previews while reusing the existing tool registry and workbench UI patterns.

**Tech Stack:** Python dataclasses/FastAPI/local JSON persistence, existing `ai_trade_system.agent` modules, React + TypeScript + Vite, existing test suites.

---

### Task 1: Backend Stores And Defaults

**Files:**
- Create: `src/ai_trade_system/agent/governance.py`
- Test: `tests/test_agent_governance.py`

- [ ] Write failing tests for memory/skill/policy default loading and JSON persistence.
- [ ] Implement dataclasses and local JSON store methods.
- [ ] Verify stores seed default weekly-scan memory, `weekly_scan_share` skill, and policy.

### Task 2: Planner Preview Service

**Files:**
- Modify: `src/ai_trade_system/agent/governance.py`
- Test: `tests/test_agent_governance.py`

- [ ] Write failing tests for previewing the weekly scan share prompt.
- [ ] Implement keyword matching against enabled skills and memories.
- [ ] Normalize planned tools through the existing Agent tool registry.
- [ ] Return step reasons, permission levels, stop conditions, and ignored tools.

### Task 3: API Routes And Schemas

**Files:**
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `src/ai_trade_system/api/app.py`
- Test: `tests/test_api_routes.py`

- [ ] Write failing route tests for list/create/update/delete memories and skills.
- [ ] Write failing route tests for get/update planner policy and plan preview.
- [ ] Add Pydantic request/response models.
- [ ] Add service wrappers and FastAPI routes.

### Task 4: Frontend API, Types, Navigation

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/shell/AppShell.tsx`
- Create: `frontend/src/pages/AgentGovernancePage.tsx`
- Test: `frontend/src/pages/AgentGovernancePage.test.tsx`

- [ ] Write failing component test that the new page renders memory, skill, policy, and preview sections.
- [ ] Add TypeScript types and API client methods.
- [ ] Add `Agent治理` nav item and render the new page.
- [ ] Implement compact CRUD and plan preview UI.

### Task 5: Docs, QA, Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/runbooks/web-console.md`
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-20-autonomous-agent-layer.md`

- [ ] Document persistence choice and new page.
- [ ] Run Python tests.
- [ ] Run frontend tests/build for affected page.
- [ ] Capture browser screenshot of `Agent治理`.
- [ ] Update pending list and QA evidence.
