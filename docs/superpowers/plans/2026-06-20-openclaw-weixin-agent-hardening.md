# OpenClaw Weixin Agent Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the OpenClaw/Weixin Agent path with concise share output, orphan task hygiene, and MCP idempotency.

**Architecture:** Reuse the current Agent boundary. `AgentSystemToolExecutor` shapes Weixin output, `AgentStore` owns task hygiene and duplicate lookup, and `AgentMcpServer` applies idempotency before queue submission.

**Tech Stack:** Python 3.13, pytest, local JSON persistence, stdio MCP.

---

### Task 1: Concise Weixin Share Output

**Files:**
- Modify: `src/ai_trade_system/agent/system_tools.py`
- Test: `tests/test_agent_system_tools.py`

- [ ] Write failing tests that assert `share.weixin` summarizes researched candidates, does not include full long research bodies, and separates scan-only candidates.
- [ ] Run `AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_system_tools.py::test_weixin_share_tool_prepares_compact_weekly_report_message -q` and confirm failure.
- [ ] Implement compact snippet helpers and metadata in `_weixin_share`.
- [ ] Run targeted `tests/test_agent_system_tools.py`.

### Task 2: Orphan Task Hygiene

**Files:**
- Modify: `src/ai_trade_system/agent/store.py`
- Modify: `src/ai_trade_system/agent/queue.py`
- Test: `tests/test_agent_queue.py`

- [ ] Write failing tests for marking stale queued/running tasks as failed with trace evidence.
- [ ] Run targeted queue tests and confirm failure.
- [ ] Add `AgentStore.mark_stale_incomplete_tasks(...)`.
- [ ] Call stale cleanup from `AgentTaskQueue.submit` and expose a queue cleanup helper.
- [ ] Run targeted queue tests.

### Task 3: MCP Idempotency

**Files:**
- Modify: `src/ai_trade_system/agent/store.py`
- Modify: `src/ai_trade_system/agent/mcp_server.py`
- Test: `tests/test_agent_mcp.py`

- [ ] Write failing tests showing duplicate weekly MCP requests return the same queued task and routing metadata marks `deduplicated=true`.
- [ ] Run targeted MCP test and confirm failure.
- [ ] Add stable idempotency key derivation and existing-task lookup.
- [ ] Preserve explicit `idempotency_key` if provided.
- [ ] Run targeted MCP tests.

### Task 4: Docs And Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/runbooks/web-console.md`
- Modify: `docs/context/pending-features.md`
- Create: `docs/qa/2026-06-20-openclaw-weixin-agent-hardening.md`

- [ ] Update docs to describe concise Weixin output, stale task cleanup, and MCP idempotency.
- [ ] Run `AI_TRADE_LLM_PROVIDER=mock python -m pytest`.
- [ ] Run `git diff --check`.
- [ ] Run `openclaw mcp reload && openclaw mcp probe ai_trade_system`.
