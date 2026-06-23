# OpenClaw Async Completion Notification QA

Date: 2026-06-20

## Scope

- Make OpenClaw/Weixin long-running MCP tasks return immediately with a `task_id`.
- Notify OpenClaw after the Agent task reaches `waiting_confirmation`, `completed`, `failed`, or `blocked`.
- Prefer the full `share.weixin` message when sending completion content; fall back to task status summary.
- Keep notification failures out of the main task status and preserve them in trace events.

## Red Evidence

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_queue.py::test_agent_queue_returns_queued_task_before_background_run_finishes \
  tests/test_agent_mcp.py::test_mcp_weekly_scan_report_tool_creates_routed_agent_task \
  tests/test_agent_openclaw.py::test_openclaw_connector_sends_task_notification_command -q
```

Initial result: 3 failed.

- Queue returned immediately but did not notify after background completion.
- MCP weekly route did not describe `async_notify` delivery.
- OpenClaw connector did not expose `notify_command`.

Second red check for share text:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_openclaw.py::test_openclaw_connector_sends_task_notification_command -q
```

Initial result: 1 failed because notification content used only `result_summary` instead of `share.weixin.output.message`.

## Green Evidence

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_queue.py::test_agent_queue_returns_queued_task_before_background_run_finishes \
  tests/test_agent_mcp.py::test_mcp_weekly_scan_report_tool_creates_routed_agent_task \
  tests/test_agent_openclaw.py -q
```

Result: 4 passed.

Full regression:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest
```

Result: 247 passed.

Diff and MCP checks:

```bash
git diff --check
openclaw mcp reload && openclaw mcp probe ai_trade_system
```

Result: diff check passed; MCP probe reported `ai_trade_system: 7 tools`.

## Notes

- `AI_TRADE_OPENCLAW_NOTIFY_COMMAND=python scripts/openclaw_notify_user.py` receives task notification JSON on stdin.
- The script calls `openclaw agent --deliver` and can pass `reply_channel`, `reply_to`, `reply_account`, `session_id`, and `session_key` if OpenClaw includes them in MCP arguments.
- Browser screenshot acceptance was not re-run because this change only affects backend/MCP/CLI notification behavior and docs, not React UI layout.
