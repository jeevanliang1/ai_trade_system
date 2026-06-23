# Agent System Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make existing trading-system capabilities callable as audited Agent tools from OpenClaw, Weixin, MCP, CLI, API, and React.

**Architecture:** Add a focused Agent tool execution module that adapts existing `api.service` functions into safe task steps. Keep `AgentOrchestrator` responsible for planning, persistence, and reporting. Keep MCP/API/React surfaces on the same task model.

**Tech Stack:** Python dataclasses/JSON persistence, FastAPI service layer, dependency-light MCP JSON-RPC, React + TypeScript + Vite.

---

## Files

- Modify `src/ai_trade_system/agent/tools.py`: expand tool specs and add deterministic tool matching helpers.
- Create `src/ai_trade_system/agent/system_tools.py`: wrappers for `data.update`, `research.fundamental`, `radar.scan`, `backtest.run`, `risk.evaluate`, and `paper.run`.
- Modify `src/ai_trade_system/agent/orchestrator.py`: plan requested tools, execute system tool adapters, include outputs in reports.
- Modify `src/ai_trade_system/agent/mcp_server.py`: keep MCP structured outputs compatible with expanded tasks.
- Modify `frontend/src/pages/AgentPage.tsx`: render expanded tool list and step outputs if needed.
- Modify `frontend/src/pages/AgentPage.test.tsx`: cover new tools/steps.
- Modify `tests/test_agent_core.py`, `tests/test_agent_mcp.py`, and `tests/test_api_routes.py`: add failing tests first, then implementation.
- Update `README.md`, `docs/architecture.md`, `docs/runbooks/web-console.md`, `docs/context/pending-features.md`, and QA docs.

## Tasks

### Task 1: Planning And Tool Registry

- [ ] Write failing tests that expect the six new tool specs and prompt/context planning.
- [ ] Run targeted pytest and confirm the tests fail because tools are missing.
- [ ] Add tool specs and deterministic matching.
- [ ] Run targeted pytest and confirm green.

### Task 2: System Tool Execution

- [ ] Write failing tests with a fake executor/service boundary showing `data.update`, `radar.scan`, `backtest.run`, `risk.evaluate`, and `paper.run` steps execute and persist summaries.
- [ ] Run targeted pytest and confirm failure.
- [ ] Implement `agent/system_tools.py` wrappers using existing service functions and compact outputs.
- [ ] Wire `AgentOrchestrator` to execute those wrappers.
- [ ] Run targeted pytest and confirm green.

### Task 3: MCP/API/Frontend Visibility

- [ ] Write failing MCP/API/frontend tests for expanded tools and task step rendering.
- [ ] Run targeted tests and confirm failure.
- [ ] Update MCP/API/frontend types or rendering only where needed.
- [ ] Run targeted tests and confirm green.

### Task 4: Documentation And Acceptance

- [ ] Update README, architecture, web console runbook, pending-features, and QA notes.
- [ ] Run `python -m pytest`.
- [ ] Run `cd frontend && npm test`.
- [ ] Run `cd frontend && npm run build`.
- [ ] Capture React AI command center screenshots through the existing headless workflow.
