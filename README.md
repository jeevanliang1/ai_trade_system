# A股自部署量化交易系统

这是一个面向 A股的第一版自部署量化系统骨架。当前目标不是直接实盘下单，而是先打通：

- 免费公开数据下载和标准化
- 自定义策略接入
- 本地回测
- 服务器纸面交易/模拟交易
- 后续券商实盘网关预留

核心框架选型以 vn.py/VeighNa 为长期方向，当前代码保持轻量纯 Python，避免在没有券商接口和正式运行环境前被重依赖卡住。

## 环境

建议生产/长期开发使用 Python 3.10 或 3.11：

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,data]"
```

当前测试只依赖 `pandas` 和 `pytest`：

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

## 拉取 A股数据

使用 AKShare 下载日线或分钟级 K 线并保存为 CSV。默认周期是 `daily`，分钟级支持 `1m`、`5m`、`15m`、`30m`、`60m`：

```bash
python -m ai_trade_system.cli download \
  --symbol 000001 \
  --exchange SZSE \
  --start 20240101 \
  --end 20241231 \
  --timeframe daily \
  --output data/000001_daily.csv
```

分钟级示例：

```bash
python -m ai_trade_system.cli download \
  --symbol 000001 \
  --exchange SZSE \
  --start 20240102 \
  --end 20240105 \
  --timeframe 5m \
  --output data/market/a_share/SZSE/000001/000001_SZSE_5m_qfq_latest.csv
```

说明：AKShare 分钟数据来自公开分时接口，`1m` 历史深度和复权能力受上游限制；系统会按请求周期标准化并持久化本地 CSV，但不会伪造上游没有返回的长期 1 分钟历史。

## 股票目录与搜索

项目内置本地 A股股票目录：

```text
data/a_share_stocks.csv
```

Web 操作台启动后会加载该文件，并支持按股票名称或代码搜索选择标的。选中后会自动带出股票代码和交易所；目录不可用时仍可手动输入代码。

刷新股票目录：

```bash
PYTHONPATH=src python -m ai_trade_system.cli stocks refresh \
  --output data/a_share_stocks.csv
```

搜索股票：

```bash
PYTHONPATH=src python -m ai_trade_system.cli stocks search 平安
PYTHONPATH=src python -m ai_trade_system.cli stocks search 000001
```

## 自选股本地行情数据管理

股票配置中心的自选股可以统一管理本地日线或分钟级文件。当前采用“主 CSV + 增量 CSV + manifest 索引”，文件名包含行情周期：

```text
data/market/a_share/SSE/601318/
  601318_SSE_daily_qfq_latest.csv
  601318_SSE_5m_qfq_latest.csv
  increments/
    601318_SSE_daily_qfq_20260618_from_20260617_to_20260618.csv
    601318_SSE_5m_qfq_20260618_from_20260617_to_20260618.csv
  manifest.json
  manifest_5m_qfq.json
```

- `*_latest.csv` 是当前完整数据文件，数据中心、回测和信号流程默认读取当前设置的周期文件。
- `increments/*.csv` 记录每次新增拉取的数据片段，文件名包含拉取日和数据日期范围。
- manifest 记录股票、复权方式、行情周期、主 CSV 路径、数据起止时间、行数和最近更新时间。

命令行批量更新自选股：

```bash
PYTHONPATH=src python -m ai_trade_system.cli data update-watchlist \
  --start 20240618 \
  --end 20260618 \
  --timeframe daily \
  --if-stale
```

`--if-stale` 会跳过已经更新到目标结束日期的股票。真正的每日系统级定时任务可以在本机用 cron/launchd 调用这个命令，但本仓库默认不提交机器本地调度配置。

## 信号雷达数据维护

React 平台的信号雷达支持按全部目录、科创板、仅本地 CSV、当前标的四种范围批量扫描。科创板范围会从本地 A股目录中筛选 `SSE` 且代码以 `688` 开头的候选，扫描数量上限为 300。默认评分模式使用“缠论多级别日线锚定”，即 `ChanMultiLevelReversalStrategy` 的 `daily_anchor` 优化预设；只有用户显式切换评分模式时才使用旧的研究分、量价动量或单级别缠论结构评分。

默认扫描只读取 `data/market/a_share/{exchange}/{code}/` 下的托管 CSV；打开“扫描前自动更新数据”后，后端会在扫描候选前复用 `data_manager.update_stock_data` 下载/维护候选行情，并返回本次维护汇总和逐股数据状态。该能力只维护本地研究数据，不会发出纸面交易或实盘指令。

## 运行回测

```bash
python -m ai_trade_system.cli backtest \
  --data data/000001_daily.csv \
  --symbol 000001 \
  --fast 5 \
  --slow 20 \
  --size 100 \
  --cash 100000
```

## 运行纸面交易

纸面交易会重放 CSV 行情，经过策略和风控后输出 JSONL 事件日志：

```bash
python -m ai_trade_system.cli paper \
  --data data/000001_daily.csv \
  --symbol 000001 \
  --fast 5 \
  --slow 20 \
  --size 100 \
  --cash 100000 \
  --log logs/paper_events.jsonl
```

## 实时盯盘

React 平台提供第一版实时盯盘工作区。该能力复用当前股票、周期和策略选择，后端通过公开分钟 K 线接口轮询最新行情，预热策略状态后只对新增 K 线输出事件和策略信号。当前范围是研究提醒和纸面联动前置能力，不会发出实盘委托。

接口：

```text
POST /api/realtime/start
GET  /api/realtime/status
GET  /api/realtime/events
POST /api/realtime/stop
```

第一版默认监听当前标的，适合 `1m/5m/15m/30m/60m` 分钟级准实时盯盘。后续 Signal Radar 实时化和 tick/券商级行情源会在同一事件模型上扩展。

## AI 指挥台 Agent 入口

AI 指挥台是系统级 Agent 入口。来自 React、CLI、MCP、OpenClaw 或微信的请求都会进入同一套本地任务内核，并持久化任务步骤、工具调用、证据、确认请求和报告。

### DeepSeek 本地配置

DeepSeek 使用官方 OpenAI-compatible Chat Completions API。密钥只放本机环境或 `.env.local`，不要写进源码或文档：

```bash
cp .env.example .env.local
```

编辑 `.env.local`：

```bash
AI_TRADE_LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=<你的 DeepSeek API Key>
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

`deepseek-v4-flash` 是默认模型；复杂规划或长链路分析可以改成 `deepseek-v4-pro`。配置后，AI研究员和 AI指挥台规划器会优先使用 DeepSeek；未配置或调用失败时，本地 Mock/关键词规划仍保留为兜底。

当前 Agent 可以调度的系统能力包括：

- `data.update`：维护当前标的或自选股的本地托管行情数据。
- `automation.weekly_result`：读取本地自动化任务持久化的最近周扫描 Top 候选和周度 AI 深度分析缓存，支持“本周/这周扫描结果”类请求优先复用定时结果。
- `research.fundamental`：通过 OpenClaw connector 边界获取基本面、信息面、公告、新闻等外部资料；未配置时记录 `not_configured`。
- `research.batch_fundamental`：对周扫描候选批量调用 OpenClaw 外部研究，汇总基本面、信息面、公告新闻、行业催化和风险点；该工具需要确认后执行。
- `radar.scan`：运行本地信号雷达批量扫描并记录 Top 候选摘要。
- `backtest.run`：复用本地回测服务运行选定或默认策略。
- `risk.evaluate`：复用确定性风控规则评估回测或传入指标。
- `paper.run`：复用纸面交易服务重放本地行情。
- `share.weixin`：把周榜、分区 Top10 AI 深度分析和 AI 结论整理成可由 OpenClaw/微信/飞书返回的紧凑摘要；完整外部研究保存在 Agent 报告中，缓存存在时优先按板块输出缓存分析。当任务上下文启用 `notify_on_completion` 且配置了 OpenClaw 通知命令时，后台任务完成后会让 OpenClaw 继续投递给用户。

## 周六自动扫描与投递

自动任务默认在周六执行完整周任务：维护科创板和创业板候选行情，使用当前默认“缠论多级别日线锚定”扫描策略生成分板块周榜，对科创板 Top10、创业板 Top10、综合非 ST Top10 生成 AI 深度分析缓存，然后通过 OpenClaw 通知命令投递到微信或飞书。

周度 AI 分析缓存保存在：

```text
data/automation/weekly_analysis/YYYY-Www.json
data/automation/weekly_analysis_latest.json
```

如果 OpenClaw/微信请求“这周扫描分析结果”，Agent 会先读取缓存；缓存存在时不重复联网研究或重跑扫描。通知实际投递仍由本机 `AI_TRADE_OPENCLAW_NOTIFY_COMMAND` 负责，`weekly_delivery_channel` 支持 `weixin` 或 `feishu`。

命令行创建 Agent 任务：

```bash
PYTHONPATH=src ai-trade agent run "帮我研究 000001 最近是否值得关注" \
  --source cli \
  --symbol 000001 \
  --exchange SZSE \
  --json
```

如果任务暂停在 `waiting_confirmation`，用下面命令批准并继续执行：

```bash
PYTHONPATH=src ai-trade agent approve <task_id> --json
```

查看工具和任务：

```bash
PYTHONPATH=src ai-trade agent tools --json
PYTHONPATH=src ai-trade agent list --json
PYTHONPATH=src ai-trade agent show <task_id> --json
PYTHONPATH=src ai-trade agent trace <task_id> --json
```

每个 Agent 任务都会写入 append-only 执行日志：

```text
data/agent/runs/<task_id>/events.jsonl
```

Trace events 覆盖请求进入、计划生成、工具开始/结束/失败、确认请求、批准记录、任务完成/失败/阻断。React `AI指挥台` 任务卡的“执行日志”按钮会读取同一份 trace，并展示事件摘要与原始 JSON payload，便于排查微信/OpenClaw 请求具体在哪一步失败。

作为 MCP stdio server 暴露给 OpenClaw/Codex 等本地 Agent：

```bash
PYTHONPATH=src ai-trade agent mcp
```

MCP 暴露两个常用触发入口：

- `create_agent_task`：通用 Agent 任务入口。
- `get_weekly_scan_report`：语义化周扫描报告入口。OpenClaw 遇到“这周/本周股票扫描结果、股票扫描分析结论、输出给我、完成分享”等自然语言请求时，应优先调用它；它会创建 Agent 任务，读取或自动触发本周扫描，再继续进入候选股票分析和微信可返回结论链路。MCP 创建入口会为短时间内重复的同源同 prompt 请求生成 `idempotency_key`，复用尚未终止的任务，避免重复 queued。

OpenClaw 外部研究通过 `research.fundamental` 工具边界接入。`AI_TRADE_OPENCLAW_RESEARCH_COMMAND=python scripts/openclaw_external_research.py` 会让系统把任务 JSON 通过 stdin 传给 OpenClaw 侧代理，由 OpenClaw 运行外部信息研究并把摘要、来源会话和置信度返回给 Agent 报告。脚本会从 OpenClaw session 中提取 `web_search` 或浏览器工具留下的 URL 作为外部证据；如果 OpenClaw 返回了看似成功的摘要但没有可验证网页 URL，Agent 会把该研究项降级为 `failed`/`low` 并提示“外部证据不足”，不会把无来源文本当作基本面结论采纳。未配置时会在任务报告中记录 `not_configured`，不会伪造外部资料。

OpenClaw/微信长任务使用异步回发语义：MCP 调用只创建任务并立即返回 `task_id`，不会一直等完整分析结束。`get_weekly_scan_report` 会默认写入 `context.notify_on_completion=true` 和 `context.notification_channel=openclaw`；后台队列在任务完成、失败、阻断或等待确认后调用 `AI_TRADE_OPENCLAW_NOTIFY_COMMAND=python scripts/openclaw_notify_user.py`，把 `share.weixin` 的微信摘要优先交给 OpenClaw 投递。通用 `create_agent_task` 如需同样回发，也应显式传入这两个 context 字段。未配置通知命令时，任务和 trace 仍会完整落盘，但不会主动发微信。队列每次提交前会标记超时停留在 `queued`/`running` 的历史任务为 failed，并追加 `orphan_task_marked` trace，避免前端长期显示假运行状态。

OpenClaw 注册本系统 MCP 的推荐命令：

```bash
openclaw mcp add ai_trade_system \
  --command "$(which python)" \
  --arg=-m \
  --arg ai_trade_system.cli \
  --arg agent \
  --arg mcp \
  --cwd /Users/jeevanliang/Desktop/github/ai_trade_system \
  --connect-timeout 10 \
  --timeout 300
openclaw mcp probe ai_trade_system
openclaw mcp reload
```

OpenClaw/微信触发后，任务会写入 `data/agent/tasks/` 并显示在 React `AI指挥台`。需要确认的工具会显示 `等待确认`，在前端确认或通过 MCP `approve_agent_action` 后继续；启用异步通知的任务会在等待确认或最终完成时追加 `task_notification_*` trace 事件。

例如，在微信里让 OpenClaw 调用本系统并说“给我这周股票扫描结果并完成分享的最终结果”，Agent 会规划为读取周扫描结果、批量外部研究和准备微信分享文本。批量外部研究会暂停等待确认；确认后继续调用 OpenClaw 研究候选股票，把完整研究写入报告，并向微信返回压缩后的核心结论、仅扫描候选和报告路径。

如果本周周扫描结果不存在、从未跑过、上次跑完但结果未落盘，或当前请求要求本周结果但持久化结果已过期，`automation.weekly_result` 会自动触发一次周扫描。触发结果会写入 Agent trace 和工具输出中的 `missing_reason`、`auto_run_attempted`、`auto_ran_scan` 字段，便于判断到底是“没扫过”还是“没保存/已过期/上次失败”。

`Agent治理` 工作区管理本地 Agent 的 Memory、Skills、Planner Policy 和计划预览。当前治理数据使用本地 JSON 文件持久化：

```text
data/agent/memory.json
data/agent/skills.json
data/agent/policy.json
```

同一治理输出也会被真实 `AgentOrchestrator` 消费：当用户没有显式指定工具时，命中的 Skill 会生成实际执行计划，Planner Policy 会影响工具确认/阻断权限，命中的 Memory/Skill 会写入任务证据链。

本地文件足够支撑当前单机使用、审计、备份和前端管理，不需要安装数据库。后续如出现并发写入、全文检索或大量历史查询，再迁移到 SQLite。

实盘、下单、券商委托等请求默认阻断；Agent 只能用于研究、解释、编排、回测/纸面交易前复核和状态汇总。

## 打开 React Web 平台

默认 Web 平台使用 React + FastAPI，包含 AI指挥台、数据下载、CSV 查看、策略管理、策略编辑、策略选择回测、组合实验室、信号预览、信号雷达、资金曲线、买卖点、交易记录、信号归因、纸面交易日志、风控和 AI 研究员。信号雷达可以扫描本地目录、科创板、本地 CSV 子集或当前标的，并可显式开启扫描前数据维护。

组合实验室支持手动配置策略 allocation，也内置稳健趋势均值、动量突破、缠论研究和缠论进攻融合四组组合模板，套用后仍走同一套组合预览、组合回测和纸面交易流程。

安装 API 依赖并安装前端依赖：

```bash
python -m pip install -e ".[api,data]"
cd frontend && npm install && cd ..
```

启动前也可以先做一次环境和依赖检查：

```bash
./scripts/run_all.sh --check
```

检查会覆盖 Python 版本、FastAPI/uvicorn/API 模块、Node.js/npm、前端依赖和默认端口占用；失败时会输出明确原因和推荐修复命令。

启动 React 平台：

```bash
./scripts/run_app.sh
```

`run_app.sh` 兼容旧入口，实际会转调 `scripts/run_all.sh`，一次性启动 FastAPI 和 React/Vite。

默认访问地址：

```text
http://localhost:5173
```

后端 API 默认地址是 `http://127.0.0.1:8000`。

如果部署在服务器，请在安全网络或反向代理后访问，不要直接暴露到公网。

## Legacy Streamlit 操作台

Streamlit 页面仍保留为 legacy 控制台，便于迁移期间对照和回退：

```bash
python -m pip install -e ".[web,data]"
./scripts/run_web.sh
```

默认 legacy 地址是 `http://localhost:8501`。

## 自定义策略

当前内置策略包括：

- `DualMovingAverageStrategy`: 双均线趋势跟随。
- `RsiMeanReversionStrategy`: RSI 超卖/超买均值回归。
- `BollingerMeanReversionStrategy`: 布林带下轨买入、回归中轨卖出。
- `ChanRsiResearchStrategy`: 将缠论 + 增强 RSI 研究预览包装为可回测策略。
- `ChanStructureStrategy`: 基于包含关系、分型、笔和中枢识别二买/二卖、三买/三卖，并按买卖点确定性、背驰确认、低确定性 T2 门控和动态仓位上限调整仓位单位。
- `ChanVolumeFusionStrategy`: 以缠论结构为主，使用量价动量确认二买等低确定性买点、放量增强三买/确认买点；量价转弱时默认先看延续趋势，趋势未破坏时不急于减仓。
- `DonchianBreakoutStrategy`: Donchian/Turtle 突破入场、跌破退出通道离场。
- `PriceMomentumStrategy`: 价格动量入场、负动量退出。
- `VolumeConfirmedMomentumStrategy`: 价格动量、放量确认、趋势过滤和跟踪止盈结合的量价动量策略。
- `MacdTrendStrategy`: MACD 金叉配合趋势均线过滤入场，死叉或趋势破位退出。
- `AtrVolatilityBreakoutStrategy`: 近期高点突破入场，使用 ATR 初始止损、跟踪止损和时间退出。

这些策略是研究和回测模板，不是收益承诺。

内置策略代码在 `src/ai_trade_system/strategies/`。

新策略建议继承 `ai_trade_system.strategy.Strategy`：

- `on_init`: 初始化指标、缓存、状态
- `on_start`: 启动策略
- `on_stop`: 停止策略
- `on_bar`: 接收 K线并返回 `Signal`

后续接入 vn.py 时，可以将同一套策略逻辑包一层 `CtaTemplate` 适配器，映射到 vn.py 的 `on_init/on_start/on_tick/on_bar/on_order/on_trade` 和 `buy/sell/short/cover`。

Web 操作台会自动发现 `strategies/` 目录下的 `.py` 策略文件。每个用户策略文件需要定义至少一个继承 `Strategy` 的类；构造函数参数会自动显示在回测和纸面交易页面，`symbol` 参数默认使用侧边栏股票代码。

## 实盘网关预留

A股实盘依赖券商开通接口。候选方向：

- XTP：中泰 XTP，A股/ETF 期权
- TORA：华鑫奇点，A股/ETF 期权
- QMT/xtquant：常见个人量化路线，通常依赖 miniQMT 客户端

第一版不直接实盘下单。等券商接口确定后，再新增 gateway 适配层，保持策略层不绑定具体券商 SDK。
