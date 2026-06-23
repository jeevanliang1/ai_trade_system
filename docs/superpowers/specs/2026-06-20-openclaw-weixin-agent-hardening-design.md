# OpenClaw Weixin Agent Hardening Design

Date: 2026-06-20

## Goal

Make the Weixin weekly-scan Agent path reliable after the first successful end-to-end run by tightening output shape, task hygiene, and MCP duplicate handling.

## Scope

- Keep the existing `AgentOrchestrator`, `AgentTaskQueue`, `AgentStore`, and `AgentMcpServer` architecture.
- Do not add live trading behavior or broker integration.
- Do not add a database; keep local JSON and append-only trace files as the source of truth.
- Do not change strategy logic or weekly radar scoring.

## Design

### Weixin Share Output

`share.weixin` should produce a Weixin-sized executive summary rather than embedding every full external research report. It will:

- Include weekly run metadata and counts.
- Show only researched candidates in detail by default.
- Use compact research snippets derived from the first useful lines of each external research summary.
- Mention unresearched scan-only candidates separately.
- Include the final research-only risk boundary.
- Return metadata such as `researched_item_count`, `scan_only_item_count`, and `full_report_hint` so notification and UI callers can inspect the full report path.

### Orphan Task Hygiene

Tasks that stay `queued` or `running` without active in-process queue ownership should be marked `failed` with a clear stale/orphan summary when they exceed a conservative age threshold. This is a local status hygiene operation and should append a trace event for auditability.

### MCP Idempotency

MCP task creation should support a short-term idempotency key so repeated Weixin prompts do not create duplicate queued tasks. The key is derived from source, normalized prompt, and stable context fields unless an explicit `idempotency_key` is passed. If a non-terminal matching task exists within the idempotency window, MCP returns that existing task and marks routing as deduplicated.

## Acceptance

- `share.weixin` output is short enough for Weixin-style delivery and does not include raw long reports.
- Weekly scan tasks still pause for `research.batch_fundamental` confirmation.
- Repeated MCP weekly requests reuse an existing queued/running/waiting task inside the dedupe window.
- Stale queued/running tasks can be marked failed with an `orphan_task_marked` trace event.
- Full Python tests pass.
