# Weekly Scan Share Agent Tools QA

Date: 2026-06-20

## Scope

Implemented three Agent tools for OpenClaw/Weixin weekly scan reporting:

- `automation.weekly_result`: reads `data/automation/star_radar_top10.json` and returns ranked weekly automation candidates.
- `research.batch_fundamental`: confirm-level batch external research for weekly candidates through the OpenClaw connector.
- `share.weixin`: prepares a Weixin-ready final response from weekly scan and batch research outputs without independently sending an outbound message.

The prompt "给我这周股票扫描结果并完成分享的最终结果" now plans as:

```text
system.snapshot -> automation.weekly_result -> research.batch_fundamental -> share.weixin -> agent.report
```

`research.batch_fundamental` pauses at `waiting_confirmation`; after approval, the task resumes from the next unfinished step.

## Verification

Red tests were added first and failed because the tools were not registered or implemented:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_system_tools.py::test_weekly_result_tool_reads_current_week_automation_top \
  tests/test_agent_system_tools.py::test_batch_fundamental_tool_researches_weekly_candidates_with_openclaw \
  tests/test_agent_system_tools.py::test_weixin_share_tool_prepares_final_weekly_report_message \
  tests/test_agent_core.py::test_agent_tools_are_listed_with_permission_levels \
  tests/test_agent_core.py::test_prompt_keywords_plan_weekly_scan_research_and_share -q
```

Initial result: 5 failed.

After implementation:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_system_tools.py::test_weekly_result_tool_reads_current_week_automation_top \
  tests/test_agent_system_tools.py::test_batch_fundamental_tool_researches_weekly_candidates_with_openclaw \
  tests/test_agent_system_tools.py::test_weixin_share_tool_prepares_final_weekly_report_message \
  tests/test_agent_core.py::test_agent_tools_are_listed_with_permission_levels \
  tests/test_agent_core.py::test_prompt_keywords_plan_weekly_scan_research_and_share -q
```

Result: 5 passed.

Agent regression:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest \
  tests/test_agent_system_tools.py \
  tests/test_agent_core.py \
  tests/test_agent_planner.py \
  tests/test_agent_mcp.py -q
```

Result: 19 passed.

Browser acceptance:

```bash
./scripts/run_app.sh
# Headless Chrome navigated to AI指挥台 and waited for
# automation.weekly_result, research.batch_fundamental, and share.weixin.
```

Screenshot:

```text
/tmp/ai_trade_system_weekly_agent_tools.png
```

## Notes

- No strategy logic changed; fixed-stock strategy benchmark backtests were not triggered.
- No browser UI changed in this task; the existing AI Command Center page will display these new tool steps through the existing task polling and tool-list APIs.
- `share.weixin` currently prepares the final response for OpenClaw/Weixin to return. It does not perform an independent active channel send.
