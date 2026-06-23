# AI Command Center Design

## Goal

Build AI as a first-class entry point for the trading system. A user can ask for research or operations from the React workbench, CLI, MCP, or OpenClaw/Weixin, and the system records every Agent task, tool call, confirmation gate, and result in a front-end-visible task timeline.

## Three Stages

### Stage 1: API Kernel And Command Center

- Add a local Agent task model with `task_id`, source, prompt, status, plan steps, tool calls, evidence, result summary, confirmation requests, and timestamps.
- Expose HTTP APIs for creating tasks, listing tasks, reading task details, listing Agent tools, and approving pending actions.
- Add a CLI wrapper that calls the same Agent kernel, so `ai-trade agent run "..."`
  produces the same persisted task record as the API.
- Add a React `AI指挥台` workspace that can submit tasks and display task status, steps, tool calls, evidence, results, and pending confirmations.

### Stage 2: MCP Tool Surface

- Add a dependency-light stdio MCP server entry that exposes Agent tools to OpenClaw, Codex, or other local agents.
- MCP tools should call the same Agent kernel used by HTTP and CLI:
  `create_agent_task`, `get_agent_task_status`, `list_agent_tasks`, `approve_agent_action`, and `list_agent_tools`.
- MCP is an entry surface only; it must not duplicate task orchestration logic.

### Stage 3: OpenClaw And Weixin-Oriented Integration

- Treat OpenClaw as an external information and desktop-capability proxy, not as the owner of trading decisions.
- Support task sources such as `openclaw` and `weixin`, so tasks triggered from chat can be audited in the React workbench.
- Add an OpenClaw research connector abstraction that can be configured later with a command or local gateway. When it is not configured, tasks should record a clear connector status instead of failing opaquely.
- Persist research reports under `data/agent/reports/` with source references, internal-system evidence, external-info status, risks, and recommended next steps.

## Permission Boundary

- Automatically allowed: read local data, list tools, summarize system state, run local research previews, inspect radar/automation status, and generate reports.
- Confirmation required: write or overwrite important local artifacts, change persistent configuration, run long batch maintenance, or ask OpenClaw to perform broad external collection.
- Always blocked until explicit future live-trading design: live orders, broker gateway actions, deleting data, or bypassing risk and paper/backtest rules.

## Architecture

```text
React / CLI / MCP / OpenClaw / Weixin
  -> Agent Gateway
    -> Agent Orchestrator
      -> Agent Store
      -> Tool Registry
      -> Existing API service functions
      -> OpenClaw connector
      -> Report writer
```

The Agent orchestrator owns task planning and auditing. Existing trading-system modules continue to own data loading, research signals, backtests, paper trading, automation, and risk evaluation.

## First-Phase Task Semantics

The first implementation should keep planning deterministic and conservative:

- Prompts about system status or automation call local status tools.
- Prompts about a symbol or research call internal research and record an OpenClaw connector step.
- Prompts about live trading or order placement stop at a confirmation/blocker state.
- Every task produces a concise `result_summary`, even if some tools are unavailable.

## Verification

- Backend tests cover task creation, tool listing, confirmation gating, report persistence, API routes, CLI output, and MCP JSON-RPC tool calls.
- Frontend tests cover the `AI指挥台` workspace, task submission, task status rendering, and pending-confirmation display.
- Browser acceptance captures React workbench screenshots with the AI command center visible.
