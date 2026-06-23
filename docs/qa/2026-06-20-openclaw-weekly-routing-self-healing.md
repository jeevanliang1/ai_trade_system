# OpenClaw Weekly Routing And Self-Healing QA

Date: 2026-06-20

## Scope

Implemented two improvements for the request “这周的股票扫描分析结论输出给我”:

- Added MCP tool `get_weekly_scan_report` with explicit natural-language semantics for OpenClaw tool selection.
- Broadened default Agent weekly Skill trigger terms and keyword fallback terms to cover “股票扫描 / 分析结论 / 输出给我”.
- Changed `automation.weekly_result` so missing or stale current-week results can automatically trigger weekly scanning before downstream Agent analysis.
- Added diagnostic fields `missing_reason`, `auto_run_attempted`, and `auto_ran_scan` to weekly-result tool output.

## Red/Green Evidence

Backend red tests:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_system_tools.py::test_weekly_result_tool_auto_runs_scan_when_current_week_result_is_missing tests/test_agent_mcp.py::test_mcp_initialize_and_list_tools -q
```

Initial result: failed because `automation.weekly_result` did not call weekly automation and MCP did not expose `get_weekly_scan_report`.

After implementation:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_system_tools.py::test_weekly_result_tool_auto_runs_scan_when_current_week_result_is_missing tests/test_agent_mcp.py::test_mcp_initialize_and_list_tools -q
```

Result: 2 passed.

Targeted Agent regression:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_governance.py tests/test_agent_system_tools.py tests/test_agent_mcp.py tests/test_agent_core.py -q
```

Result: 28 passed.

Final verification:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest
```

Result: 245 passed.

```bash
git diff --check
```

Result: passed.

## Notes

- Automatic weekly scanning does not bypass confirm-level external research. `research.batch_fundamental` still pauses for confirmation according to Planner Policy.
- No strategy logic changed; fixed-stock benchmark backtests were not triggered.
