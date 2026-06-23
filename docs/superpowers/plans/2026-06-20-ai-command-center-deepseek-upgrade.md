# AI Command Center DeepSeek Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect DeepSeek as the first real AI backend and upgrade AI Command Center execution to background, resumable, auditable Agent tasks.

**Architecture:** Add a small OpenAI-compatible DeepSeek REST client, route AI Researcher and Agent planner through it when configured, refactor Agent tasks so confirm-level tools pause/resume, and expose FastAPI task creation through a background queue. React continues to poll persisted task state.

**Tech Stack:** Python `requests`, FastAPI, dataclasses, pytest, React/Vitest, local `.env.local` config.

---

### Task 1: DeepSeek Client And Local Config

**Files:**
- Create: `src/ai_trade_system/config.py`
- Create: `src/ai_trade_system/deepseek.py`
- Modify: `.gitignore`
- Create: `.env.example`
- Test: `tests/test_deepseek.py`

- [ ] Write failing tests for `.env.local` loading and JSON chat request shape.
- [ ] Implement a no-SDK DeepSeek REST client using `requests`.
- [ ] Ensure API keys are never included in returned errors or summaries.

### Task 2: DeepSeek AI Research Provider

**Files:**
- Modify: `src/ai_trade_system/llm.py`
- Modify: `src/ai_trade_system/api/service.py`
- Test: `tests/test_llm.py`

- [ ] Write failing tests for DeepSeek JSON-to-`LLMInsight` mapping.
- [ ] Add provider selection from `AI_TRADE_LLM_PROVIDER`.
- [ ] Keep Mock provider fallback when DeepSeek is not configured or fails.

### Task 3: Resumable Agent Orchestrator

**Files:**
- Modify: `src/ai_trade_system/agent/models.py`
- Modify: `src/ai_trade_system/agent/tools.py`
- Modify: `src/ai_trade_system/agent/orchestrator.py`
- Test: `tests/test_agent_core.py`

- [ ] Write failing tests for confirm-level tool pause and approved resume.
- [ ] Add `queued` status and tool-scoped confirmations.
- [ ] Refactor execution so already completed steps are skipped during resume.

### Task 4: DeepSeek Planner

**Files:**
- Create: `src/ai_trade_system/agent/planner.py`
- Modify: `src/ai_trade_system/agent/orchestrator.py`
- Test: `tests/test_agent_core.py`

- [ ] Write failing tests that a fake DeepSeek planner can choose `data.update`, `radar.scan`, `backtest.run`, `risk.evaluate`, and `paper.run`.
- [ ] Normalize the model plan against the tool registry.
- [ ] Preserve keyword planner fallback when DeepSeek is not configured.

### Task 5: FastAPI Background Queue And UI State

**Files:**
- Create: `src/ai_trade_system/agent/queue.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/AgentPage.tsx`
- Test: `tests/test_api_routes.py`
- Test: `frontend/src/pages/AgentPage.test.tsx`

- [ ] Write failing tests that API-created tasks return before completion and can later be listed.
- [ ] Add a daemon-thread queue for API/MCP-created task execution.
- [ ] Resume approved tasks through the same queue.
- [ ] Render queued/running/waiting states and confirmation action clearly.

### Task 6: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/runbooks/web-console.md`
- Modify: `docs/architecture.md`
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-20-ai-command-center-deepseek-upgrade.md`

- [ ] Document DeepSeek env vars and OpenClaw MCP registration.
- [ ] Record tests/build/browser screenshots.
- [ ] Keep strategy benchmark marked not applicable because no strategy logic changes.
