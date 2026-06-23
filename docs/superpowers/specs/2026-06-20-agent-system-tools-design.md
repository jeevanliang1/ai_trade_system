# Agent System Tools Design

## Goal

Extend the AI command center from an audited task receiver into a controlled system capability dispatcher. OpenClaw, Weixin, MCP, CLI, API, and React-created Agent tasks should be able to invoke existing trading-system abilities while every step remains visible in the React AI command center.

## Scope

First version implements synchronous, audited tool execution for:

- `data.update`: maintain local managed A-share CSV data for the task target.
- `research.fundamental`: request external/fundamental information through the OpenClaw connector boundary.
- `radar.scan`: run the existing research signal batch scanner.
- `backtest.run`: run the existing backtest service with the selected or default strategy.
- `risk.evaluate`: run deterministic risk guardrail evaluation.
- `paper.run`: run the existing paper trading replay service.

The feature does not add live trading, broker integration, order routing, or autonomous portfolio changes.

## Architecture

Add an Agent tool execution layer under `src/ai_trade_system/agent/`. The orchestrator continues to own task lifecycle, status, persistence, and reporting. Each tool adapter wraps an existing service-layer capability instead of duplicating business logic. Tool outputs are compact summaries plus structured payloads safe to persist in `data/agent/tasks/` and `data/agent/reports/`.

MCP remains the external entry surface. `create_agent_task` still creates one audited task, but the task plan can now include system tools inferred from the prompt or explicitly supplied through context. React keeps reading `/api/agent/tasks`; no separate realtime transport is required for this slice.

## Planning Rules

The planner should remain conservative and deterministic:

- Data words such as `更新数据`, `行情`, or `data.update` plan `data.update`.
- Fundamental words such as `基本面`, `信息面`, `新闻`, `公告`, or `research.fundamental` plan `research.fundamental`.
- Scan words such as `扫描`, `雷达`, or `radar.scan` plan `radar.scan`.
- Backtest words such as `回测` or `backtest.run` plan `backtest.run`.
- Risk words such as `风控`, `风险`, or `risk.evaluate` plan `risk.evaluate`.
- Paper words such as `纸面`, `模拟交易`, or `paper.run` plan `paper.run`.
- Every task starts with `system.snapshot` and ends with `agent.report`.
- Live trading and broker-order prompts stay blocked before any tool runs.

`context.tools` may explicitly request tools. Unknown requested tools should be ignored with an evidence entry rather than executed.

## Permission Boundary

Auto-run in this version:

- `system.snapshot`
- `data.update`
- `radar.scan`
- `backtest.run`
- `risk.evaluate`
- `paper.run`
- `agent.report`

Confirm or connector-dependent:

- `research.fundamental` uses the OpenClaw connector. If no command is configured, it records `not_configured`.

Blocked:

- Live trading, direct order placement, broker commission, or bypassing risk controls.

## Frontend

React AI command center should show all registered Agent tools, including the new system capabilities. Task cards already render step names, summaries, evidence, report path, and confirmations; the new step outputs should therefore become visible without a new page. Minor copy/layout updates may be added only if needed for readability.

## Testing

- Agent core tests cover tool listing, explicit tool planning, prompt-based planning, and persisted report content.
- MCP tests cover creating a task that runs at least one new system tool.
- API route tests cover `/api/agent/tools` exposing the expanded tool list.
- Frontend tests cover rendering the expanded tool list and new step names.
- Full verification should run `python -m pytest`, `cd frontend && npm test`, `cd frontend && npm run build`, and browser screenshot capture when the React surface is available.
