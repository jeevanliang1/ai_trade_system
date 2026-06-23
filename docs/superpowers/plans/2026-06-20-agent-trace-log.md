# Agent Trace Log Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add append-only per-task Agent trace logs and expose them through backend, CLI, MCP, and React AI指挥台.

**Architecture:** `AgentStore` owns JSONL trace persistence under `data/agent/runs/<task_id>/events.jsonl`. `AgentOrchestrator` writes trace events at existing state transition points. API/CLI/MCP read from the same store, and React lazily loads trace events for a selected task card.

**Tech Stack:** Python dataclasses/JSONL/FastAPI, existing CLI argparse and MCP JSON-RPC, React + TypeScript + Vitest.

---

### Task 1: Backend Trace Persistence

**Files:**
- Modify: `src/ai_trade_system/agent/store.py`
- Test: `tests/test_agent_core.py`

- [ ] Write a failing test that creates an Agent task, reads `data/agent/runs/<task_id>/events.jsonl`, and expects `request_received`, `plan_selected`, `tool_started`, `tool_finished`, and `task_completed`.
- [ ] Run the single test and verify it fails because trace persistence is missing.
- [ ] Add `AgentStore.append_trace_event()` and `AgentStore.read_trace()`.
- [ ] Update `AgentOrchestrator` to emit trace events during create, plan, tool execution, confirmation, approval, block, complete, and failure paths.
- [ ] Run `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_core.py -q`.

### Task 2: API, CLI, And MCP Trace Lookup

**Files:**
- Modify: `src/ai_trade_system/api/app.py`
- Modify: `src/ai_trade_system/api/service.py`
- Modify: `src/ai_trade_system/cli.py`
- Modify: `src/ai_trade_system/agent/mcp_server.py`
- Test: `tests/test_api_routes.py`
- Test: `tests/test_agent_mcp.py`
- Test: `tests/test_agent_cli.py`

- [ ] Write failing tests for `GET /api/agent/tasks/{task_id}/trace`, MCP `get_agent_trace`, and CLI `agent trace <task_id> --json`.
- [ ] Run those tests and verify they fail because lookup interfaces are missing.
- [ ] Add service, route, CLI subcommand, and MCP tool that return `{ "task_id": task_id, "events": [...] }`.
- [ ] Run targeted Python tests for API, MCP, and CLI.

### Task 3: React Trace Viewer

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/AgentPage.tsx`
- Modify: `frontend/src/styles.css`
- Test: `frontend/src/pages/AgentPage.test.tsx`

- [ ] Write a failing frontend test that clicks a task's trace button, expects `api.agentTaskTrace(task_id)`, and sees trace event summary plus raw JSON.
- [ ] Run the test and verify it fails because the API method/UI is missing.
- [ ] Add trace event types and client method.
- [ ] Add a trace toggle section to `AgentTaskCard` with event rows and `<pre>` raw payload rendering.
- [ ] Run `npm test -- --run src/pages/AgentPage.test.tsx` from `frontend/`.

### Task 4: Documentation And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/runbooks/web-console.md`
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-20-agent-trace-log.md`

- [ ] Document trace paths and lookup commands.
- [ ] Move Agent Trace Log from pending to completed context.
- [ ] Record QA evidence, including a browser screenshot of the trace view.
- [ ] Run `AI_TRADE_LLM_PROVIDER=mock python -m pytest`.
- [ ] Run targeted frontend test and `npm run build`.
- [ ] Run `git diff --check`.
