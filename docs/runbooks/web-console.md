# React Web 平台运行手册

## 用途

默认 Web 操作台是 React + FastAPI AI量化平台工作台，用于个人本地或服务器查看 A股公开数据、管理和编辑用户策略、组合多个策略、运行回测、查看信号预览、资金曲线、交易记录、纸面交易日志、风险状态、AI 指挥台任务和 AI 研究观点。

它不包含实盘下单入口。实盘券商网关必须在接口、风控和运行规则明确后单独接入。

## 启动

安装依赖：

```bash
python -m pip install -e ".[api,data]"
cd frontend
npm install
cd ..
```

启动前检查：

```bash
./scripts/run_all.sh --check
```

检查项包括 Python 3.10+、FastAPI/uvicorn/API 模块导入、Node.js 20 LTS+、npm、`frontend/package.json`、`frontend/node_modules` 和默认端口 `8000/5173` 是否可用。缺前端依赖时脚本会尝试 `npm install`；其他问题会输出 `原因：...` 与 `建议：...`。

启动：

```bash
./scripts/run_app.sh
```

`run_app.sh` 保留为兼容入口，实际转调 `scripts/run_all.sh`。如果仓库根目录存在 `.venv/bin/python`，启动脚本会优先使用该虚拟环境；否则使用当前 shell 的 `python3` 或 `python`。本项目建议 Python 3.10 或 3.11。

常见失败处理：

- 提示缺 Python API 依赖：运行 `python -m pip install -e ".[api,data]"`。
- 提示缺 Node.js/npm 或版本过低：安装 Node.js 20 LTS 或更高版本。
- 提示端口被占用：结束占用进程，或使用 `API_PORT=8001 FRONTEND_PORT=5174 ./scripts/run_all.sh` 换端口启动。

默认地址：

```text
http://localhost:5173
```

服务器部署时应放在安全网络或反向代理之后，不要直接公网裸露。

## API 与 Legacy 入口

FastAPI 默认监听：

```text
http://127.0.0.1:8000
```

单独启动 API：

```bash
./scripts/run_api.sh
```

单独启动 React：

```bash
./scripts/run_frontend.sh
```

Streamlit legacy 控制台保留在：

```bash
python -m pip install -e ".[web,data]"
./scripts/run_web.sh
```

legacy 地址仍为 `http://localhost:8501`。

## API 错误响应契约

React 工作台通过 `frontend/src/api/client.ts` 统一请求 FastAPI。本地 API 报错时，优先查看浏览器 Network 面板里的 HTTP 状态码和 JSON `detail` 字段，再回到页面提示定位具体操作。

业务输入错误和本地路径安全错误返回 HTTP 400，响应形状为：

```json
{
  "detail": "CSV data not found: data/missing.csv"
}
```

上游或本地运行时依赖失败返回 HTTP 502，响应形状同样使用字符串 `detail`：

```json
{
  "detail": "AKShare request failed"
}
```

请求体缺字段、字段类型错误或不符合 Pydantic schema 时，FastAPI 返回 HTTP 422，`detail` 是校验错误列表：

```json
{
  "detail": [
    {
      "loc": ["body", "settings"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

前端页面主要面向字符串 `detail` 展示可读错误，例如 `请求失败：CSV data not found: data/missing.csv`。如果看到 422 或浏览器原生网络错误，通常说明前端请求 payload、API schema 或本地 API 连接状态不一致，应先检查请求体、后端日志和 `./scripts/run_all.sh --check` 输出。

## 常见输入

- CSV 数据：默认 `data/000001_daily.csv`
- 股票目录：默认 `data/a_share_stocks.csv`，用于按名称或代码搜索 A股标的
- 纸面交易日志：默认 `logs/paper_events.jsonl`
- 策略：内置双均线、RSI 均值回归、布林带均值回归、Donchian/Turtle 突破、价格动量，以及 `strategies/` 下用户自定义策略
- 信息面摘要：AI研究员页的手工文本输入，先用于 Mock LLM 观点生成
- 风控阈值：侧边栏的最大回撤、单笔最大金额、最小现金余额、最大持仓股数

## 页面结构

React 工作台包含以下主要区域：

- `总览`：数据、策略、纸面交易、AI观点和最近回测摘要。
- `AI指挥台`：创建、查看和复核来自前端、CLI、MCP、OpenClaw 或微信的 Agent 任务，显示步骤、工具调用、报告路径和确认请求。
- `股票配置`：管理本地自选股和共享股票选择。
- `数据中心`：下载 AKShare 数据、读取 CSV、生成演示数据、查看 K线和数据健康。
- `信号雷达`：批量扫描股票目录、本地 CSV 候选或当前标的，支持 Chan/RSI 研究分、量价动量和缠论结构评分，标出缺失行情 CSV 的候选，并支持准备缺失数据、保留扫描历史和导出 CSV。
- `策略工坊`：发现内置和用户策略，新建/编辑用户策略，预览信号。
- `组合实验室`：添加多个策略，配置权重和聚合模式，预览组合信号。
- `回测中心`：运行单策略或组合策略回测，查看价格、买卖点、权益、回撤、指标和交易表。
- `AI研究员`：基于技术指标、信息面摘要和风控上下文生成结构化 Mock AI 观点。
- `纸面交易`：重放 CSV 行情并输出 JSONL 事件日志。
- `风控`：查看确定性风控阈值和回测风险状态。
- `自动任务`：查看和手动触发本地自动化雷达维护和每日判断任务。

## 策略页

策略页展示策略列表、来源、策略文件路径，并支持新建和编辑 `strategies/` 下的用户策略。

回测页和纸面交易页都可以选择策略。策略构造函数参数会自动渲染成输入控件。

信号预览不等同于成交结果；实际成交仍以回测或纸面交易页经过资金、滑点、手续费和风控后的结果为准。

用户策略会作为本机 Python 代码执行，只编辑和运行可信策略。

## 组合策略

组合实验室会把多个策略包装成 `PortfolioStrategy`，仍然走原有 `Strategy.on_bar -> Signal` 接口。当前支持同一股票、同一日线 CSV 上的多策略聚合：

- `weighted_vote`：按权重比较买卖方向。
- `equal_vote`：每个启用策略一票。
- `first_active`：采用第一个产生信号的启用策略。

启用“AI参与评分”时，最近一次 AI 观点为看多会轻微提高组合权重。该行为只用于研究和回测，不会产生实盘委托。

## DeepSeek 配置

真实模型接入通过本机 `.env.local` 完成，示例见 `.env.example`：

```bash
AI_TRADE_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=<本机密钥>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`.env.local` 已被 `.gitignore` 忽略。不要把真实密钥写进 README、测试、截图或提交记录。DeepSeek 用于 AI研究员结构化观点和 AI指挥台工具规划；实际数据更新、雷达扫描、回测、风控和纸面交易仍由本地确定性工具执行。

## AI研究员

AI研究员默认使用 `MockLLMProvider`，当 `AI_TRADE_LLM_PROVIDER=deepseek` 且 `DEEPSEEK_API_KEY` 存在时使用 `DeepSeekLLMProvider`：

- 输入：最新技术指标快照、信息面摘要、风控上下文、提示词模式。
- 输出：方向、置信度、建议动作、技术证据、信息面证据、风险提示、provider、prompt version。
- 可勾选“显示Prompt快照”查看模型输入。
- DeepSeek 调用失败时会返回中性研究观点和风险提示，不会绕过风控和纸面/回测流程。

## AI指挥台

AI指挥台使用 `ai_trade_system.agent.AgentOrchestrator`：

- HTTP 入口：`GET /api/agent/tools`、`GET /api/agent/tasks`、`POST /api/agent/tasks`、`GET /api/agent/tasks/{task_id}`、`GET /api/agent/tasks/{task_id}/trace`、`POST /api/agent/tasks/{task_id}/approve`。
- CLI 入口：`ai-trade agent run "..." --source cli --json`、`ai-trade agent approve <task_id> --json`、`ai-trade agent tools --json`、`ai-trade agent list --json`、`ai-trade agent show <task_id> --json`、`ai-trade agent trace <task_id> --json`。
- MCP 入口：`ai-trade agent mcp`，暴露 `create_agent_task`、`get_weekly_scan_report`、`get_agent_task_status`、`get_agent_trace`、`list_agent_tasks`、`approve_agent_action` 和 `list_agent_tools`。MCP 创建和审批任务走后台队列，调用方可轮询状态并读取 trace。OpenClaw 遇到“这周股票扫描分析结论输出给我”这类请求时应优先调用 `get_weekly_scan_report`；短时间重复的同源同 prompt 请求会复用未终止任务并在 routing 里标记 `deduplicated`。
- OpenClaw/微信入口：将来源记录为 `openclaw` 或 `weixin`，外部研究走 `research.fundamental` 工具边界；`AI_TRADE_OPENCLAW_RESEARCH_COMMAND=python scripts/openclaw_external_research.py` 会通过 OpenClaw agent 生成外部研究摘要，并从 OpenClaw session 的 `web_search` 结果或浏览器工具记录中提取网页 URL 作为外部证据。未配置时报告中显示 `not_configured`；若返回摘要但没有可验证外部 URL，批量研究项会被标记为 `failed`/`low`，摘要写明“外部证据不足”，避免把 AI 自行编造的资料当成结论。长任务回发走 `AI_TRADE_OPENCLAW_NOTIFY_COMMAND=python scripts/openclaw_notify_user.py`；MCP 会立即返回 `task_id`，后台任务进入 `waiting_confirmation`、`completed`、`failed` 或 `blocked` 后再让 OpenClaw 投递消息给用户。
- Agent 系统工具：`data.update`、`automation.weekly_result`、`research.fundamental`、`research.batch_fundamental`、`radar.scan`、`backtest.run`、`risk.evaluate`、`paper.run`、`share.weixin`。这些工具复用现有 API/service 能力，步骤和摘要会写入 `data/agent/tasks/` 并显示在前端 AI指挥台。
- Agent Trace Log：每个任务追加写入 `data/agent/runs/<task_id>/events.jsonl`，覆盖请求、计划、工具开始/结束/失败、确认、批准、任务终态、`orphan_task_marked` 和 `task_notification_sent`/`task_notification_skipped`/`task_notification_failed`。AI指挥台任务卡“执行日志”按钮会读取 `GET /api/agent/tasks/{task_id}/trace`，展示事件摘要和 raw JSON payload；排障时优先从这里定位失败工具、错误摘要、OpenClaw 输出、通知投递结果和耗时。
- 周度扫描分享链路：OpenClaw/微信可创建“给我这周股票扫描结果并完成分享的最终结果”任务。Agent 会读取 `data/automation/star_radar_top10.json`，批量研究周榜候选，并准备微信返回文本。如果当前周榜缺失或过期，`automation.weekly_result` 会自动触发周扫描，并在输出里标记 `missing_reason`、`auto_run_attempted`、`auto_ran_scan`。`research.batch_fundamental` 会暂停到 `等待确认`；批准后继续调用 OpenClaw 外部研究。`share.weixin` 返回适合微信阅读的摘要，只展开已研究候选的核心结论，未研究候选单独列为“仅扫描候选”，完整正文和来源保留在 Agent 报告路径中。`get_weekly_scan_report` 默认启用 `notify_on_completion`，因此 OpenClaw 不需要一直阻塞等结果，而是在任务状态需要用户关注时再收到系统通知。
- Agent治理：React `Agent治理` 工作区管理本地 Memory、Skills、Planner Policy，并可以在不执行工具的情况下预览自然语言任务会匹配哪些 Memory、选择哪个 Skill、调用哪些工具和触发哪些停止条件。真实 Agent 任务也会消费同一治理输出：没有显式工具覆盖时，命中 Skill 会驱动实际计划，Planner Policy 会控制工具确认/阻断权限。治理数据保存在 `data/agent/memory.json`、`data/agent/skills.json`、`data/agent/policy.json`；当前不需要数据库。
- 前端状态刷新：AI指挥台打开时每 3 秒轮询 Agent 工具和任务列表，OpenClaw/微信触发的任务步骤会自动出现在任务卡中；“刷新状态”按钮可立即手动刷新。状态包括 `排队中`、`执行中`、`等待确认`、`已完成`、`已阻断` 和 `失败`。
- OpenClaw MCP 注册示例：确保所选 Python 能直接 `import ai_trade_system`，再运行 `openclaw mcp add ai_trade_system --command "$(which python)" --arg=-m --arg ai_trade_system.cli --arg agent --arg mcp --cwd /path/to/ai_trade_system --connect-timeout 10 --timeout 300`。OpenClaw 会忽略 stdio 启动中的 `PYTHONPATH`，不要依赖 `--env PYTHONPATH=src`；注册后运行 `openclaw mcp probe ai_trade_system`、`openclaw mcp reload`、`openclaw mcp status --json --verbose`。可用 `openclaw agent --message '请只调用 MCP 工具 ai_trade_system__list_agent_tools...' --json` 做真实 Agent 调用验收。
- 权限边界：读取、总结和本地研究任务可自动执行；`research.fundamental`、`research.batch_fundamental` 等 confirm 级工具会暂停到 `等待确认`；`share.weixin` 只准备回复文本，真正投递由显式配置的 OpenClaw 通知命令完成；实盘、下单、券商委托等请求默认阻断。

如果 AKShare 未安装，页面的数据下载会提示安装 `.[web,data]`。

## 自动任务

自动任务页展示本地雷达维护和每日判断的可审计状态，不直接读取运行 JSON/JSONL 也能判断任务健康：

- `运行诊断`：来自 `/api/automation/status` 的派生诊断，覆盖正在运行、最近运行失败、尚无周扫描结果、周扫描存在缺失行情等状态，并给出后续处理建议。
- `最近运行`：展示最近的 weekly/daily run 记录，包括 run id、任务类型、状态、开始/结束时间和运行消息。失败记录会保留错误摘要，便于从页面定位 AKShare、数据维护或判断刷新问题。
- `周扫描`：维护 STAR/自选股行情并刷新 Top N 候选，运行结果会进入自动任务状态和最近运行列表。
- `日判断`：基于最近 Top N 候选刷新判断卡片，缺少周扫描结果时会返回可见阻断信息。

自动任务仍只做本地数据维护、研究扫描和纸面判断，不新增实盘下单或券商委托入口。

## 数据下载排障

页面的“下载日线数据”依赖 AKShare。下载顺序为东方财富、腾讯、新浪，前一个源在当前网络下不可用时会自动尝试下一个源。

- 如果提示缺少 AKShare，运行 `python -m pip install -e ".[web,data]"` 或 `python -m pip install akshare`。
- 如果提示 AKShare request failed，说明三个数据源都不可用，优先检查服务器代理、防火墙或到行情源的访问。
- 网络不可用时，可以先把行情 CSV 放到 `data/` 目录，再用 Web 页面读取 CSV 跑回测和纸面交易。
- 如果只是想试用平台流程，点击数据中心的“生成演示数据”，会向当前 CSV 路径写入一份确定性的本地演示 K线。

## 股票目录刷新与搜索

Web 侧边栏启动时只加载本地股票目录，不会自动联网刷新。

信号雷达页同样只读取本地股票目录和 `data/<股票代码>_daily.csv`。扫描范围支持：

- `全部目录候选`：按股票目录和搜索词取候选，缺少 CSV 的候选会保留在结果中并标为 `缺少CSV`。
- `仅本地CSV`：只扫描已有 `data/<股票代码>_daily.csv` 的候选，适合快速复扫可用数据池。
- `当前标的`：只扫描当前全局设置里的 symbol/exchange/csv_path。

它不会自动联网下载缺失行情；缺少 CSV 的候选可点击 `准备数据` 写入数据中心设置，再到数据中心下载或手动放入对应文件后重新扫描。成功扫描会在页面保留最近历史摘要，当前排行可用 `导出CSV` 下载。

刷新目录：

```bash
PYTHONPATH=src python -m ai_trade_system.cli stocks refresh --output data/a_share_stocks.csv
```

命令行搜索：

```bash
PYTHONPATH=src python -m ai_trade_system.cli stocks search 平安
PYTHONPATH=src python -m ai_trade_system.cli stocks search 000001
```

如果目录文件不存在，侧边栏会显示手动输入股票代码和交易所的兜底控件。

## 交付检查清单

准备提交或打开 PR 前，按影响范围勾选以下检查：

- Python 行为：涉及 `src/ai_trade_system/` 或 API 路由时运行 `python -m pytest`，或至少运行直接覆盖变更的测试文件并说明范围。
- 前端行为：涉及 React、TypeScript 或样式时在 `frontend/` 运行相关 `npm test`，并在累积 UI 变更后运行 `npm run build`。
- API 契约：涉及请求/响应形状时同步更新 `tests/test_api_routes.py`、`frontend/src/api/client.test.ts` 或调用方测试。
- 文档和待办：广义功能推进后更新 `docs/context/pending-features.md`，保持一个 `Next Recommended Feature`。
- 策略基准回测：每次修改策略或新增策略，必须用本地固定的中芯国际 `688981/SSE` 和 五粮液 `000858/SZSE` 三年 qfq 数据跑回测，并把可比结果记录到 `docs/qa/`；跳过时说明原因。
- 浏览器验收：浏览器可见变更需运行 headless Chrome 截图流程，并在收尾说明截图路径；无可截图界面时说明原因。
- 风控边界：确认没有新增默认实盘交易入口，AI 观点、回测、纸面交易和风险控制边界仍然清晰。
