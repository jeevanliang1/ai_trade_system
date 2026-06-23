# OpenClaw MCP Integration QA

## Scope

Completed the OpenClaw side of the AI command center integration:

- OpenClaw Gateway and `openclaw-weixin` channel health.
- OpenClaw MCP registration for `ai_trade_system`.
- OpenClaw agent visibility of the system MCP tools.
- OpenClaw agent creation of an audited `ai_trade_system` Agent task.
- Reverse `research.fundamental` path from `ai_trade_system` back into OpenClaw external research.

This work does not change strategy logic, so the fixed-stock strategy benchmark rule is not triggered.

## OpenClaw Runtime Evidence

```bash
openclaw gateway status
```

Result: Gateway `Runtime: running`, `Connectivity probe: ok`, version `2026.6.6`, loopback `127.0.0.1:18789`.

```bash
openclaw channels list --all
```

Result: `openclaw-weixin default`, `openclaw-weixin fc43871dc76a-im-bot`, and Feishu are installed, configured, and enabled.

```bash
openclaw status
```

Result: default model `deepseek-v4-flash`; channel `openclaw-weixin` state `OK`.

## MCP Evidence

```bash
openclaw mcp show ai_trade_system
```

Result: existing MCP config launches:

```text
/opt/homebrew/Caskroom/miniconda/base/bin/python -m ai_trade_system.cli agent mcp
cwd=/Users/jeevanliang/Desktop/github/ai_trade_system
connectTimeout=10
timeout=300
```

```bash
openclaw mcp probe ai_trade_system --json
```

Result: probe returned five OpenClaw-facing MCP tools:

- `ai_trade_system__approve_agent_action`
- `ai_trade_system__create_agent_task`
- `ai_trade_system__get_agent_task_status`
- `ai_trade_system__list_agent_tasks`
- `ai_trade_system__list_agent_tools`

```bash
openclaw mcp reload
openclaw mcp status --json --verbose
```

Result: cached MCP runtimes disposed; `ai_trade_system` status `configured=true`, `enabled=true`, `ok=true`, transport `stdio`.

## OpenClaw Agent Tool Call Evidence

Read-only tool visibility:

```bash
openclaw agent --session-key agent:main:ai-trade-mcp-smoke \
  --message '请只调用 MCP 工具 ai_trade_system__list_agent_tools，读取 ai_trade_system 暴露的工具列表。不要创建任务，不要发送消息，不要做其他操作。最后只用中文简要返回工具数量和工具名。' \
  --json --timeout 300
```

Result: OpenClaw agent `status=ok`, `toolSummary.calls=1`, tool `ai_trade_system__list_agent_tools`; response listed the eight internal Agent tools: `system.snapshot`, `data.update`, `research.fundamental`, `radar.scan`, `backtest.run`, `risk.evaluate`, `paper.run`, and `agent.report`.

Create-task path:

```bash
openclaw agent --session-key agent:main:ai-trade-mcp-create-task-smoke \
  --message '请调用 MCP 工具 ai_trade_system__create_agent_task 创建一个安全的本地任务，参数必须是：prompt="请按指定工具对 000001 做一次风控检查并生成报告"，source="openclaw"，context={"symbol":"000001","exchange":"SZSE","tools":["risk.evaluate"]}。创建后调用 ai_trade_system__get_agent_task_status 读取状态；如果还不是 completed/failed/blocked/waiting_confirmation，最多再查 3 次。不要调用 research.fundamental，不要发送消息，不要下单。最后只返回 task_id、status、report_path 和已执行步骤名。' \
  --json --timeout 300
```

Result: OpenClaw agent `status=ok`, `toolSummary.calls=2`, tools `ai_trade_system__create_agent_task` and `ai_trade_system__get_agent_task_status`. Created task:

- `task_id`: `agt_b2b67548dd94`
- `status`: `completed`
- `report_path`: `reports/agt_b2b67548dd94.json`
- steps: `system.snapshot -> risk.evaluate -> agent.report`

Local persistence check:

- `data/agent/tasks/agt_b2b67548dd94.json` exists.
- `data/agent/reports/agt_b2b67548dd94.json` exists.

## Reverse OpenClaw Research Evidence

Configured local ignored `.env.local`:

```text
AI_TRADE_OPENCLAW_RESEARCH_COMMAND=python scripts/openclaw_external_research.py
```

Script smoke test:

```bash
printf '%s' '{"prompt":"请用一两句话说明 000001 的外部研究连接是否可用，不要调用 ai_trade_system MCP。","context":{"symbol":"000001","exchange":"SZSE"}}' \
  | python scripts/openclaw_external_research.py
```

Result: returned `status=ok`, an OpenClaw-generated external research summary, `confidence=medium`, and an `openclaw_agent` source with run id/session file.

Agent `research.fundamental` path:

```bash
python - <<'PY'
from ai_trade_system.agent.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()
task = orchestrator.create_task(
    '请对 000001 做一次外部基本面研究，生成简短报告',
    source='openclaw',
    context={'symbol': '000001', 'exchange': 'SZSE', 'tools': ['research.fundamental']},
)
orchestrator.approve_task(task.task_id, 'approved')
resumed = orchestrator.run_task(task.task_id)
print(resumed.task_id, resumed.status, resumed.report_path, [step.tool_name for step in resumed.steps])
PY
```

Result:

- `task_id`: `agt_90843b87bf79`
- `status`: `completed`
- `report_path`: `reports/agt_90843b87bf79.json`
- steps: `system.snapshot -> research.fundamental -> agent.report`
- `research.fundamental.status`: `ok`
- `research.fundamental.confidence`: `medium`

## Regression

```bash
python -m pytest tests/test_openclaw_external_research_script.py -q
```

Result: `2 passed`.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_core.py::test_research_task_records_internal_and_openclaw_steps -q
```

Result: `1 passed`.

## Notes

- `scripts/openclaw_external_research.py` tells OpenClaw not to call `ai_trade_system` MCP tools during external research, preventing recursive task creation.
- OpenClaw and the system both use the local DeepSeek setup, but secrets stay in ignored `.env.local` and are not recorded in this QA file.
