# Agent Trace Log QA

Date: 2026-06-20

## Scope

Implemented append-only Agent trace logs for AI指挥台/OpenClaw/Weixin/API/CLI/MCP tasks:

- per-task JSONL events at `data/agent/runs/<task_id>/events.jsonl`
- orchestrator trace events for request, plan, tools, confirmations, approvals, completion, failure, and block paths
- API route `GET /api/agent/tasks/{task_id}/trace`
- CLI command `ai-trade agent trace <task_id> --json`
- MCP tool `get_agent_trace`
- React AI指挥台 task-card execution-log viewer with event summaries and raw JSON payloads

## Red/Green Evidence

Backend trace persistence red test:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_core.py::test_agent_task_writes_append_only_trace_events tests/test_agent_core.py::test_agent_trace_records_confirmation_and_approval -q
```

Initial result: failed because `AgentStore.read_trace` did not exist.

After implementation:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_core.py -q
```

Result: 13 passed.

API/CLI/MCP red tests:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_api_routes.py::test_agent_routes_create_list_show_and_approve_tasks tests/test_agent_mcp.py::test_mcp_initialize_and_list_tools tests/test_agent_mcp.py::test_mcp_create_and_read_agent_task tests/test_agent_cli.py::test_agent_cli_tools_and_task_lifecycle -q
```

Initial result: failed because `/trace`, `get_agent_trace`, and `agent trace` were missing. The same run exposed a task JSON concurrent read/write race; `AgentStore.save_task` now writes task snapshots atomically via temp-file replace.

After implementation:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_api_routes.py::test_agent_routes_create_list_show_and_approve_tasks tests/test_agent_mcp.py::test_mcp_initialize_and_list_tools tests/test_agent_mcp.py::test_mcp_create_and_read_agent_task tests/test_agent_cli.py::test_agent_cli_tools_and_task_lifecycle -q
```

Result: 4 passed.

Frontend red test:

```bash
npm test -- --run src/pages/AgentPage.test.tsx
```

Initial result: failed because the task card had no `执行日志` button.

After implementation:

```bash
npm test -- --run src/pages/AgentPage.test.tsx
```

Result: 1 file passed, 5 tests passed.

Final verification:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest
```

Result: 243 passed.

```bash
npm test -- --run src/pages/AgentPage.test.tsx src/shell/AppShell.test.tsx src/shell/AppShell.tasks.test.tsx
```

Result: 3 files passed, 17 tests passed.

```bash
npm run build
```

Result: passed.

```bash
git diff --check
```

Result: passed.

Browser acceptance:

```text
docs/qa/screenshots/2026-06-20-agent-trace-log_desktop_1440.png
```

The screenshot shows AI指挥台 with a completed Weixin-sourced task, the `执行日志` button opened, and trace events with raw JSON payloads visible.

## Notes

- Trace logs are append-only event streams and do not replace task snapshots or final reports.
- Trace write failures are swallowed by the orchestrator so observability cannot break task execution.
- No strategy logic changed; fixed-stock benchmark backtests were not triggered.
