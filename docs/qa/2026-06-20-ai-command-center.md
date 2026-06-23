# AI Command Center QA

## Scope

Implemented the three-stage AI command center:

- Stage 1: shared Agent task kernel, FastAPI task/tool/approval APIs, CLI entry, and React `AI指挥台` status surface.
- Stage 2: dependency-light stdio MCP JSON-RPC server exposing Agent task tools.
- Stage 3: OpenClaw/Weixin-oriented source tracking, configurable OpenClaw external-research connector boundary, live-trading blocker, and persisted Agent reports.

This work does not change strategy logic, so the fixed-stock strategy benchmark rule is not triggered.

## Verification

```bash
python -m pytest tests/test_agent_core.py tests/test_agent_cli.py tests/test_agent_mcp.py tests/test_api_routes.py::test_agent_routes_create_list_show_and_approve_tasks -q
```

Result: `10 passed in 0.92s`.

```bash
cd frontend && npm test -- AgentPage.test.tsx AppShell.tasks.test.tsx
```

Result: `2 passed`, `13 passed` tests.

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite production build completed.

```bash
python -m pytest
```

Result: `214 passed in 5.22s`.

```bash
cd frontend && npm test
```

Result: `20 passed`, `96 passed` tests.

## Browser Acceptance

Started the React + FastAPI platform with:

```bash
./scripts/run_app.sh
```

Seeded a sample `weixin` Agent task through `/api/agent/tasks`, navigated to `AI指挥台`, and captured:

- `docs/qa/screenshots/2026-06-20-ai-command-center_desktop_1440.png`
- `docs/qa/screenshots/2026-06-20-ai-command-center_mobile_390.png`

Visual check:

- Desktop shows the active `AI指挥台` nav item, task prompt controls, Agent tool permissions, a persisted `weixin` task, OpenClaw `not_configured` evidence, report path, and right-side AI/risk inspector.
- Mobile shows the responsive shell with grouped navigation and the Agent command panel without horizontal overflow.

## Notes

- `openclaw.external_research` records `not_configured` until `AI_TRADE_OPENCLAW_RESEARCH_COMMAND` is set.
- Live-trading/downstream broker intents are blocked by the Agent kernel before tool execution.
