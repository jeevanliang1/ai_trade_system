# 2026-06-21 周六扫描深度分析投递 QA

## 目标

把周六自动任务从“只生成周扫描 Top 候选”升级为完整周报链路：

- 维护科创板 `688*` 和创业板 `300*/301*` 候选行情。
- 使用默认 `chan_multilevel_daily_anchor` 扫描策略生成周榜。
- 生成科创板 Top10、创业板 Top10、综合非 ST Top10 的逐股 AI 深度分析。
- 将周度分析缓存到 `data/automation/weekly_analysis/YYYY-Www.json` 和 `data/automation/weekly_analysis_latest.json`。
- 通过 OpenClaw 通知命令投递到微信或飞书；未配置时记录 `not_configured`，不伪造已投递。
- OpenClaw/微信查询本周扫描分析时，优先复用缓存，缓存存在时不重复外部研究。

## 关键行为

- `AutomationConfig` 新增：
  - `weekly_analysis_enabled=True`
  - `weekly_analysis_top_n=10`
  - `weekly_delivery_enabled=True`
  - `weekly_delivery_channel="weixin"`
- `WeeklyRadarResult` 保留旧 `top` 兼容字段，同时新增 `board_top`。
- `WeeklyAnalysisResult` 记录分区、逐股分析、证据状态、投递状态和完整分享文本。
- `automation.weekly_result` 返回 `analysis_cache`。
- `research.batch_fundamental` 看到 `analysis_cache` 时返回 `status="cached"`，不调用 OpenClaw 外部研究。
- `share.weixin` 支持按分区输出缓存分析，`target` 可由上下文切换到 `feishu`。

## 验证

```bash
PYTHONPATH=src python -m pytest tests/test_automation_store.py tests/test_automation_service.py tests/test_agent_system_tools.py -q
```

结果：`18 passed in 31.17s`。

```bash
PYTHONPATH=src python -m pytest tests/test_automation_radar.py tests/test_automation_scheduler.py tests/test_agent_openclaw.py tests/test_api_routes.py -q
```

结果：`44 passed in 1.73s`。

```bash
AI_TRADE_LLM_PROVIDER=mock PYTHONPATH=src python -m pytest -q
```

结果：`294 passed in 10.09s`。

```bash
npm --prefix frontend test
npm --prefix frontend run build
```

结果：前端 `21` 个测试文件、`101` 个测试通过；生产构建通过。

## 浏览器验收

- 截图：`docs/qa/screenshots/2026-06-21-weekly-deep-analysis-automation_desktop_1440.png`
- 页面：React 自动任务工作区。
- 观察：页面真实加载自动任务状态，并显示 `NO_WEEKLY_ANALYSIS` 诊断，证明状态接口已能暴露“周扫描存在但 AI 深度分析缓存缺失”的情况。

## 注意

本次没有真实调用微信或飞书外部投递。投递通过 `AI_TRADE_OPENCLAW_NOTIFY_COMMAND` 间接执行，测试覆盖了通知命令边界和自动任务的通知调用点。

## 2026-06-21 多级联动校准回归

用户复核后指出两个问题：

- OpenClaw 临时查询本周结果时，深度分析仍只覆盖综合 Top5，而不是科创板 Top10 和创业板 Top10。
- AI 分析结论和原因没有显式绑定缠论多级联动依据，容易退化为泛化基本面摘要。

处理结果：

- `automation.weekly_result` 继续保留兼容用的 `top_candidates`，同时透出 `board_top` 和 `board_top_counts`。
- `research.batch_fundamental` 在没有周度分析缓存但周榜存在 `board_top` 时，优先按板块 section 做 Top10 研究；不再被 OpenClaw 上下文里的 `research_limit=5` 截断为综合 Top5。
- 周度 AI 分析缓存项新增 `chan_multilevel_basis`，自动化周报 Prompt、OpenClaw fallback 研究 Prompt 和微信/飞书分享文本都会展示“本地缠论”依据。
- 普通旧周榜候选没有缠论字段时，分享文本保持旧格式，避免输出“未记录信号”噪声。

验证：

```bash
PYTHONPATH=src python -m pytest tests/test_agent_system_tools.py -q
```

结果：`12 passed in 0.79s`。

```bash
PYTHONPATH=src python -m pytest tests/test_automation_service.py tests/test_automation_store.py tests/test_automation_radar.py -q
```

结果：`10 passed in 40.81s`。

```bash
AI_TRADE_LLM_PROVIDER=mock PYTHONPATH=src python -m pytest
```

结果：`296 passed in 10.57s`。

环境说明：直接运行 `PYTHONPATH=src python -m pytest` 时，本机 `AI_TRADE_LLM_PROVIDER` 取到了 DeepSeek，导致 `tests/test_api_routes.py::test_demo_data_backtest_ai_and_risk_flow` 期望 `MockLLMProvider` 的断言失败。使用 `AI_TRADE_LLM_PROVIDER=mock` 固定测试环境后全量通过。

## 2026-06-21 OpenClaw 重发仍为 Top5 的修复

复现现象：

- 用户让 OpenClaw 重新发送本周扫描分析，结果仍是综合 Top5。
- 最新 Agent 任务 `agt_f0959b6d40fb` 的 `automation.weekly_result` 已使用新代码，但输出中 `board_top={}`、`analysis_cache=null`。
- 本地 `data/automation/star_radar_top10.json` 是旧 schema，只包含 `top`，没有 `board_top`；`data/automation/weekly_analysis_latest.json` 不存在。

根因：

- 之前只修了“有 board_top 时按板块 Top10 分析”的路径，但没有把旧 schema 周榜识别为不完整结果。
- OpenClaw 重新请求时仍读取旧周榜缓存，因此只能 fallback 到 `top_candidates[:research_limit]`，而上下文默认 `research_limit=5`。

处理结果：

- `automation.weekly_result` 在用户请求本周“分析/结论/分享/发给我”等语义时，如果当前周榜缺少 `board_top` 且没有完整科创/创业分析缓存，会返回 `legacy_result_missing_board_top` 并自动触发周榜自恢复。
- 普通“只看扫描结果”的请求不会强制补分析，避免不必要的完整周任务。
- 已用低层扫描函数重建本地周榜缓存，未触发外部 AI 深度研究或微信/飞书投递。

本地修复后缓存状态：

```text
run_id=weekly-2026-06-21T18:49:01
total_candidates=2006
scanned=2006
missing=0
board_top_counts={'star': 10, 'chinext': 10, 'combined_non_st': 10}
```

工具链仿真验证：

```text
weekly_result: board_top_counts {'star': 10, 'chinext': 10, 'combined_non_st': 10}
research.batch_fundamental: sections=3 requested=30 researched=30
share.weixin: sections=3 items=30，消息包含科创板 Top10、创业板 Top10、本地缠论
```

验证命令：

```bash
PYTHONPATH=src python -m pytest tests/test_agent_system_tools.py tests/test_automation_service.py tests/test_automation_store.py tests/test_automation_radar.py -q
```

结果：`23 passed in 38.62s`。

```bash
AI_TRADE_LLM_PROVIDER=mock PYTHONPATH=src python -m pytest
```

结果：`297 passed in 10.41s`。

## 2026-06-21 OpenClaw MCP/Skill 默认 Top10 修复

用户继续复核 OpenClaw 最新请求日志后发现：

- OpenClaw 最新请求没有生成新的 `data/agent/tasks/*.json`，而是复用了旧 Top5 结果。
- OpenClaw 会话里没有真正拿到 `ai_trade_system__get_weekly_scan_report` MCP 工具，却仍回复“MCP重新获取完成”。
- 项目 MCP 工具 schema 和 OpenClaw 本地 skill 默认调用参数都仍是 `limit=5`、`research_limit=5`。

处理结果：

- `get_weekly_scan_report` MCP schema 默认值改为 `limit=10`、`research_limit=30`。
- 不传参数时，进入 Agent task context 的默认值同样为 `limit=10`、`research_limit=30`，避免重复请求复用旧 Top5 idempotency。
- OpenClaw 本地 skill `~/.openclaw/workspace/skills/ai-trade-system/SKILL.md` 默认调用参数改为 `limit=10`、`research_limit=30`。
- OpenClaw skill 增加约束：如果当前 turn 看不到 `ai_trade_system` MCP 工具，不允许复用旧会话、投递代理文本、本地文件或记忆来伪装刷新完成；必须报告 MCP 不可用并要求执行 `openclaw mcp reload` 与 `openclaw mcp probe ai_trade_system`。
- 已执行 `openclaw mcp reload` 清理缓存 runtime。

验证：

```bash
python -m pytest tests/test_agent_mcp.py -q
```

红灯结果：新增断言先失败，旧 schema/default context 仍返回 `5`。

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest tests/test_agent_mcp.py tests/test_agent_openclaw.py tests/test_agent_system_tools.py -q
```

结果：`25 passed in 0.88s`。

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest
```

结果：`298 passed in 10.77s`。

```bash
openclaw mcp reload
openclaw mcp probe ai_trade_system
```

结果：已清理 cached MCP runtimes；`ai_trade_system` probe 返回 `7 tools`。

```bash
openclaw agent --session-key agent:main:ai-trade-mcp-visibility-after-top10-fix \
  --message '请只调用 MCP 工具 ai_trade_system__list_agent_tools，读取 ai_trade_system 暴露的内部工具列表。不要创建任务，不要调用周报，不要发送消息，不要下单。最后只用中文简要返回工具数量和工具名。' \
  --json --timeout 300
```

结果：OpenClaw agent `status=ok`，`toolSummary.calls=1`，调用工具为 `ai_trade_system__list_agent_tools`；返回 11 个内部 Agent 工具，包含 `automation.weekly_result`、`research.batch_fundamental` 和 `share.weixin`。

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | /opt/homebrew/Caskroom/miniconda/base/bin/python -m ai_trade_system.cli agent mcp
```

结果：`get_weekly_scan_report` 对外 schema 默认值为 `limit=10`、`research_limit=30`，工具总数为 `7`。
