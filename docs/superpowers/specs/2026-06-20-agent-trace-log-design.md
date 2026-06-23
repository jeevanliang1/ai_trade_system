# Agent Trace Log Design

Date: 2026-06-20

## Goal

Add an append-only trace log for every Agent request so a Weixin/OpenClaw/API/CLI/MCP task can be debugged from request receipt through planning, tool calls, confirmations, completion, and failures.

## Scope

- Persist per-task events at `data/agent/runs/<task_id>/events.jsonl`.
- Keep the existing task JSON and report JSON as state snapshots; trace JSONL is the chronological event stream.
- Expose trace lookup through FastAPI, CLI, MCP, and the React AI指挥台.
- Record enough raw details to diagnose local tool and OpenClaw failures without adding a database.

## Event Model

Each event is a JSON object with:

- `event_id`: monotonically increasing zero-padded id within a task run.
- `task_id`
- `type`: `request_received`, `plan_selected`, `tool_started`, `tool_finished`, `tool_failed`, `confirmation_requested`, `approval_recorded`, `task_completed`, `task_failed`, `task_blocked`.
- `created_at`: UTC timestamp.
- `tool_name`: optional.
- `status`: optional task or tool status.
- `summary`: short human-readable text.
- `payload`: bounded structured details such as context, planned tools, tool output, exception text, confirmations, report path, stdout/stderr summaries returned by connectors.

The first event is created when `AgentOrchestrator.create_task()` receives a task. Tool events wrap `_run_step()`. Confirmation and terminal events are written at the same points that currently update task state.

## Interfaces

- Backend store: `AgentStore.append_trace_event(task_id, type, ...)` and `AgentStore.read_trace(task_id)`.
- Orchestrator: writes trace events during create, plan, run, confirmation, approval, completion, failure, and block paths.
- API: `GET /api/agent/tasks/{task_id}/trace` returns `{ "task_id": "...", "events": [...] }`.
- CLI: `ai-trade agent trace <task_id> --json`.
- MCP: `get_agent_trace` tool with `task_id`.
- Frontend: each AI指挥台 task card has a trace toggle. When opened, it loads the trace, shows event timeline rows, and shows raw JSON output for selected events.

## Error Handling

Trace write failures should not fail trading-system tasks. The store keeps trace operations local and simple; if an append fails, the task still continues. API/CLI/MCP trace lookup should return an empty event list only when the task has no trace file yet; unknown task ids still follow current task lookup behavior where applicable.

## Testing

- Backend unit tests verify append-only trace files, chronological events, tool output payloads, and confirmation/approval events.
- API and MCP tests verify trace lookup routes/tools.
- Frontend tests verify the trace toggle calls the API and renders event summaries plus raw JSON.
- Full verification runs existing Python tests, targeted frontend tests, frontend build, and `git diff --check`.
