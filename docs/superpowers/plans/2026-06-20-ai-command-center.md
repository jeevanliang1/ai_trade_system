# AI Command Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the three-stage AI command center so React, CLI, MCP, and OpenClaw/Weixin-originated requests all enter one audited Agent task system.

**Architecture:** Add a local `ai_trade_system.agent` package with a task store, tool registry, orchestrator, report writer, OpenClaw connector abstraction, and MCP stdio adapter. FastAPI, CLI, and React call that shared package instead of duplicating orchestration logic.

**Tech Stack:** Python dataclasses/JSON storage, FastAPI/Pydantic routes, argparse CLI, dependency-light JSON-RPC MCP stdio server, React + TypeScript + Vite.

---

## File Structure

- Create `src/ai_trade_system/agent/models.py` for task, step, tool-call, confirmation, report, and status dataclasses.
- Create `src/ai_trade_system/agent/store.py` for JSON task/report persistence under `data/agent/`.
- Create `src/ai_trade_system/agent/tools.py` for the Agent tool registry and local tool execution wrappers.
- Create `src/ai_trade_system/agent/openclaw.py` for the configurable external-research connector.
- Create `src/ai_trade_system/agent/orchestrator.py` for task planning, permission gating, tool execution, report generation, and store updates.
- Create `src/ai_trade_system/agent/mcp_server.py` for stdio JSON-RPC MCP tool calls.
- Modify `src/ai_trade_system/api/schemas.py`, `src/ai_trade_system/api/service.py`, and `src/ai_trade_system/api/app.py` to expose Agent HTTP APIs.
- Modify `src/ai_trade_system/cli.py` to add `agent` commands.
- Modify `frontend/src/types.ts`, `frontend/src/api/client.ts`, `frontend/src/pages/pageTypes.ts`, `frontend/src/pages/AgentPage.tsx`, `frontend/src/shell/AppShell.tsx`, and `frontend/src/styles.css` for the command-center UI.
- Add backend tests in `tests/test_agent_core.py`, `tests/test_agent_mcp.py`, `tests/test_agent_cli.py`, and API route coverage in `tests/test_api_routes.py`.
- Add frontend tests in `frontend/src/pages/AgentPage.test.tsx` and `frontend/src/shell/AppShell.tasks.test.tsx`.
- Update `README.md`, `docs/architecture.md`, `docs/runbooks/web-console.md`, `docs/context/pending-features.md`, and QA evidence docs.

## Tasks

### Task 1: Backend Agent Core

- [ ] Write failing tests in `tests/test_agent_core.py` for creating a research task, blocking live-trading prompts behind confirmation, listing tools, and persisting a report.
- [ ] Run `python -m pytest tests/test_agent_core.py -q` and verify the tests fail because `ai_trade_system.agent` does not exist.
- [ ] Implement `models.py`, `store.py`, `tools.py`, `openclaw.py`, and `orchestrator.py`.
- [ ] Re-run `python -m pytest tests/test_agent_core.py -q` and verify the tests pass.

### Task 2: HTTP API

- [ ] Add failing route tests to `tests/test_api_routes.py` for `GET /api/agent/tools`, `POST /api/agent/tasks`, `GET /api/agent/tasks`, `GET /api/agent/tasks/{task_id}`, and `POST /api/agent/tasks/{task_id}/approve`.
- [ ] Run the targeted route tests and verify they fail with missing routes.
- [ ] Add Agent request/response schemas and FastAPI/service route functions.
- [ ] Re-run the targeted route tests and verify they pass.

### Task 3: CLI Entry

- [ ] Add failing CLI tests in `tests/test_agent_cli.py` for `ai-trade agent tools`, `ai-trade agent run "..." --source cli --json`, `ai-trade agent list --json`, and `ai-trade agent show TASK_ID --json`.
- [ ] Run `python -m pytest tests/test_agent_cli.py -q` and verify missing command failures.
- [ ] Modify `src/ai_trade_system/cli.py` to call the shared Agent orchestrator/store.
- [ ] Re-run `python -m pytest tests/test_agent_cli.py -q` and verify the tests pass.

### Task 4: MCP Surface

- [ ] Add failing tests in `tests/test_agent_mcp.py` for JSON-RPC `initialize`, `tools/list`, and `tools/call` with `create_agent_task` and `get_agent_task_status`.
- [ ] Run `python -m pytest tests/test_agent_mcp.py -q` and verify missing MCP handler failures.
- [ ] Implement `src/ai_trade_system/agent/mcp_server.py` and add `ai-trade agent mcp` CLI entry.
- [ ] Re-run `python -m pytest tests/test_agent_mcp.py -q` and verify the tests pass.

### Task 5: React Command Center

- [ ] Add failing frontend tests for `AgentPage` rendering task cards, submitting a prompt, showing tool calls, and showing pending confirmation state.
- [ ] Run `cd frontend && npm test -- AgentPage.test.tsx AppShell.tasks.test.tsx` and verify missing UI/API behavior failures.
- [ ] Add Agent types/API client methods/page props, create `AgentPage.tsx`, wire navigation as `AI指挥台`, and style the task timeline.
- [ ] Re-run the targeted frontend tests and verify they pass.

### Task 6: Documentation And Acceptance

- [ ] Update README, architecture, and web console runbook with Agent entrypoints, OpenClaw boundary, MCP command, and front-end status visibility.
- [ ] Update `docs/context/pending-features.md` by removing completed Agent items and recording the next recommended feature.
- [ ] Run backend targeted tests, frontend tests/build, and browser screenshot capture.
- [ ] Record QA evidence and screenshot paths under `docs/qa/`.
