# AI Command Center DeepSeek Upgrade QA

## Scope

Implemented the AI command center upgrade from the synchronous keyword-planned MVP to a DeepSeek-configurable, background, resumable Agent execution path.

Covered behavior:

- Local `.env.local` / environment configuration for `AI_TRADE_LLM_PROVIDER=deepseek`, `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, and `DEEPSEEK_MODEL`.
- DeepSeek-compatible chat client, JSON response parsing, and `AI Researcher` LLM provider selection.
- Agent planner fallback order: requested tools, DeepSeek plan, then deterministic keyword plan.
- Background Agent task queue for FastAPI and MCP task creation.
- Confirm-level tool pause/resume flow for `research.fundamental`.
- CLI and MCP approval continuation.
- React `AI指挥台` status labels, tool confirmation actions, queued/waiting/completed states, and narrow-width layout hardening.

This work does not change strategy logic, so the fixed-stock strategy benchmark rule is not triggered.

## Verification

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest
```

Result: `228 passed in 7.88s`.

```bash
npm test
```

Run from `frontend/`.

Result: `20 passed`, `98 passed` tests.

```bash
npm run build
```

Run from `frontend/`.

Result: TypeScript and Vite production build completed.

```bash
git diff --check
```

Result: no whitespace errors.

```bash
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | PYTHONPATH=src python -m ai_trade_system.cli agent mcp
```

Result: MCP initialize returned `serverInfo.name=ai-trade-system-agent`; tools list exposed `create_agent_task`, `get_agent_task_status`, `list_agent_tasks`, `approve_agent_action`, and `list_agent_tools`.

Live DeepSeek smoke test:

- Local `.env.local` exists and is ignored by git.
- `load_deepseek_config()` returned `configured=true`, `base_url=https://api.deepseek.com`, and `model=deepseek-v4-flash`.
- `DeepSeekClient.chat_json()` returned `status=ok`, `data={"ok": true, "provider": "deepseek"}`, and `usage.total_tokens=95`.
- `provider_from_env()` and API `bootstrap()["limits"]["provider"]` both returned `DeepSeekLLMProvider`.
- Regression guard: `tests/test_agent_planner.py` verifies the Agent planner does not call DeepSeek when `AI_TRADE_LLM_PROVIDER=mock`, even if a local DeepSeek key exists.

## Browser Acceptance

Started the React + FastAPI platform with:

```bash
./scripts/run_app.sh
```

Validated `http://127.0.0.1:5173/` with the in-app Browser:

- Desktop 1440x1024: `AI指挥台` rendered the command panel, Agent tools, a waiting `research.fundamental` confirmation, and `确认` / `拒绝` actions.
- Mobile 390x844: `AI指挥台` rendered without horizontal overflow after the responsive CSS fix.
- Interaction proof: clicked `确认` on task `agt_f595f761f26b`; the task changed from `等待确认` to `已完成`, added `research.fundamental` and `agent.report` completed steps, and wrote `reports/agt_f595f761f26b.json`.
- Browser console check: no `warn` or `error` entries during the tested flow.

Screenshots:

- `docs/qa/screenshots/2026-06-20-ai-command-center-deepseek-upgrade_desktop_1440.png`
- `docs/qa/screenshots/2026-06-20-ai-command-center-deepseek-upgrade_mobile_390.png`
- `docs/qa/screenshots/2026-06-20-ai-command-center-deepseek-upgrade_approved_mobile_390.png`

## Notes

- The live DeepSeek call was run with the local ignored `.env.local`; no secret value is documented here.
- Unit tests cover DeepSeek request shape, Authorization header usage, JSON response parsing, provider mapping, and error redaction with fake HTTP transport.
- If `AI_TRADE_OPENCLAW_RESEARCH_COMMAND` is unset, `research.fundamental` records the OpenClaw external-research status as `not_configured` while preserving the audited Agent report.
