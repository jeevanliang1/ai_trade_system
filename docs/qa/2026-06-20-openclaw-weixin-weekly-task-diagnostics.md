# OpenClaw Weixin Weekly Task Diagnostics

Date: 2026-06-20

## Runtime Evidence

- Weixin channel was reachable and `openclaw-weixin` was running.
- `ai_trade_system` MCP server was configured, enabled, and healthy with 7 exposed tools.
- The latest Weixin request created `agt_1632c5cde061` and OpenClaw sent a Weixin outbound message at `2026-06-20 17:40:34 CST`.
- The task report showed the weekly scan result was available:
  - `run_id=weekly-2026-06-20T17:39:46`
  - `status=success`
  - `scanned=608`
  - `missing=0`
  - `top_count=10`
- The same task failed at `research.batch_fundamental`; every researched candidate returned `/bin/sh: python: command not found`.
- An earlier synchronous OpenClaw-launched CLI process was still running:
  - `python -m ai_trade_system.cli agent run ... --source weixin --json`
  - It was not the MCP async path and should not be killed automatically without operator intent.

## Root Cause

The OpenClaw connector accepted local commands such as:

```bash
AI_TRADE_OPENCLAW_RESEARCH_COMMAND=python scripts/openclaw_external_research.py
AI_TRADE_OPENCLAW_NOTIFY_COMMAND=python scripts/openclaw_notify_user.py
```

OpenClaw's shell environment did not provide a `python` executable, so connector subprocess calls failed even though the trading system itself was running inside a valid Python interpreter.

## Fix

- `OpenClawConnector` now normalizes commands whose first token is bare `python` to the current `sys.executable`.
- The normalization applies to both external research and completion notification commands.
- This preserves the documented simple `.env.local` form while avoiding dependence on OpenClaw shell `PATH`.

## Verification

Red check:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_openclaw.py -q
```

Initial result: 2 failed, both with `/bin/sh: python: No such file or directory`.

Green checks:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_openclaw.py -q
AI_TRADE_LLM_PROVIDER=mock python -m pytest
git diff --check
```

Results:

- `tests/test_agent_openclaw.py`: 4 passed.
- Full pytest suite: 249 passed.
- `git diff --check`: passed.

## Follow-Up

- Add cross-process locking or orphan detection for weekly automation tasks so direct CLI/process invocations cannot leave multiple `running` Agent tasks behind.
- Keep routing Weixin weekly scan requests through the `ai-trade-system` OpenClaw workspace skill and MCP tool path, not direct shell snippets.
- Browser screenshot acceptance was not run for this QA note because the fix only changes backend connector command normalization and runtime diagnostics.
