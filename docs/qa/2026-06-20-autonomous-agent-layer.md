# Autonomous Agent Layer QA

Date: 2026-06-20

## Scope

Implemented the first autonomous Agent governance slice:

- local JSON persistence for Memory, Skills, and Planner Policy under `data/agent/`
- backend `AgentGovernanceStore` and `AgentGovernanceService`
- FastAPI governance CRUD and plan preview routes
- React `Agent治理` workspace for Memory, Skills, Planner Policy, and Plan Preview
- `AgentOrchestrator` consumption of governance output so matched Skills drive real task plans and Planner Policy controls real tool confirmation/block permissions
- navigation integration in the default React workbench

No database was installed. Local files satisfy the current single-user, local-first persistence requirements and keep governance state transparent and easy to audit.

## Red/Green Evidence

Backend governance red test:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_governance.py -q
```

Initial result: import failure because `ai_trade_system.agent.governance` did not exist.

After implementation:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_governance.py -q
```

Result: 4 passed.

API route red test:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_api_routes.py::test_agent_governance_routes_manage_memory_skill_policy_and_preview -q
```

Initial result: 404 for `/api/agent/governance/memories`.

After implementation:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_api_routes.py::test_agent_governance_routes_manage_memory_skill_policy_and_preview -q
```

Result: 1 passed.

Frontend red test:

```bash
npm test -- --run src/pages/AgentGovernancePage.test.tsx
```

Initial result: failed to resolve `./AgentGovernancePage`.

After implementation:

```bash
npm test -- --run src/pages/AgentGovernancePage.test.tsx
```

Result: 1 passed.

Targeted regression:

```bash
npm test -- --run src/pages/AgentGovernancePage.test.tsx src/shell/AppShell.test.tsx src/shell/AppShell.tasks.test.tsx
```

Result: 3 files passed, 13 tests passed.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_governance.py tests/test_api_routes.py::test_agent_governance_routes_manage_memory_skill_policy_and_preview -q
```

Result: 5 passed.

Autonomous orchestration integration:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_core.py tests/test_agent_governance.py -q
```

Result: 15 passed.

Frontend build:

```bash
npm run build
```

Result: passed.

Final verification:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest
```

Result: 241 passed.

```bash
npm test -- --run src/pages/AgentGovernancePage.test.tsx src/shell/AppShell.test.tsx src/shell/AppShell.tasks.test.tsx
```

Result: 3 files passed, 13 tests passed.

```bash
npm run build
```

Result: passed.

```bash
git diff --check
```

Result: passed.

Browser acceptance:

```text
/tmp/ai_trade_system_agent_governance_preview.png
```

The screenshot shows `Agent治理`, default Memory, default `weekly_scan_share` Skill, Planner Policy, and plan preview steps:

```text
automation.weekly_result -> research.batch_fundamental -> share.weixin
```

## Notes

- Plan preview for “给我这周股票扫描结果并完成分享的最终结果” selects `weekly_scan_share`.
- Preview steps are `automation.weekly_result -> research.batch_fundamental -> share.weixin`.
- `research.batch_fundamental` remains confirm-level.
- Real Agent tasks now consume governance Skill and Planner Policy output; tests cover a custom Skill driving `risk.evaluate` and a policy override making `share.weixin` require confirmation.
- No strategy logic changed; fixed-stock benchmark backtests were not triggered.
