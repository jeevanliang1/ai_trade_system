# Agent System Tools QA

Date: 2026-06-20

## Scope

AI Command Center now dispatches existing system abilities as Agent tools for OpenClaw/Weixin/MCP/API/CLI/React task sources:

- `data.update`
- `research.fundamental`
- `radar.scan`
- `backtest.run`
- `risk.evaluate`
- `paper.run`

The work did not change strategy logic or add a strategy, so fixed-stock strategy benchmark backtests were not required.

## Verification

- `PYTHONPATH=src python -m pytest`
  - Result: 219 passed.
- `cd frontend && npm test`
  - Result: 20 files passed, 97 tests passed.
- `cd frontend && npm run build`
  - Result: TypeScript and Vite production build passed.
- `openclaw mcp probe ai_trade_system`
  - Result: `ai_trade_system: 5 tools`.
- Direct MCP `list_agent_tools`
  - Result: returned `system.snapshot`, `data.update`, `research.fundamental`, `radar.scan`, `backtest.run`, `risk.evaluate`, `paper.run`, and `agent.report`.

## Browser Acceptance

Headless Chrome opened the React platform, clicked `AI指挥台`, waited for the expanded tool list, and captured:

- `docs/qa/screenshots/2026-06-20-agent-system-tools_desktop_1440.png`
- `docs/qa/screenshots/2026-06-20-agent-system-tools_mobile_390.png`

Both PNGs were dimension-checked:

- Desktop: 1440x1024
- Mobile: 390x844

## Notes

A direct MCP create-task smoke with `backtest.run` and `risk.evaluate` correctly recorded a failed `backtest.run` step when the expected managed CSV was absent, then continued to `risk.evaluate` and `agent.report`. The generated smoke task files were removed afterward to avoid polluting `data/agent/`.
