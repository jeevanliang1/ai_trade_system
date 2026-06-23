# OpenClaw Weixin Agent Hardening QA

Date: 2026-06-20

## Scope

- Compact `share.weixin` output for Weixin delivery.
- Separate deep-researched candidates from scan-only candidates.
- Backfill the final Agent report path into share output before notification.
- Mark stale `queued`/`running` tasks as failed with `orphan_task_marked` trace evidence.
- Reuse recent duplicate MCP requests through `idempotency_key`.

## Red Evidence

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_system_tools.py::test_weixin_share_tool_prepares_compact_weekly_report_message -q
```

Initial result: failed because `share.weixin` had no `researched_item_count` and embedded long research text directly.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_queue.py::test_agent_queue_marks_stale_queued_tasks_as_failed \
  tests/test_agent_queue.py::test_agent_queue_does_not_mark_recent_or_active_tasks_as_stale -q
```

Initial result: failed because `AgentTaskQueue.cleanup_stale_tasks` did not exist.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_mcp.py::test_mcp_weekly_scan_report_reuses_recent_duplicate_task -q
```

Initial result: failed because duplicate weekly MCP calls created two different task ids.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_core.py::test_agent_report_backfills_report_path_into_share_output -q
```

Initial result: failed because `share.weixin` output did not include the final report path.

## Targeted Green Evidence

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_core.py \
  tests/test_agent_queue.py \
  tests/test_agent_mcp.py \
  tests/test_agent_system_tools.py \
  tests/test_agent_openclaw.py -q
```

Result: 34 passed.

## Notes

- This change does not alter strategy logic or radar scoring.
- Browser screenshot acceptance is not required for this backend/MCP behavior change; the React UI will show the new persisted statuses and trace events through existing task/trace APIs.
