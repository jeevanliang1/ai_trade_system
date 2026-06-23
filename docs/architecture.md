# 架构说明

## 当前模块

- `market`: 统一的 `Bar` 和 `Signal` 数据模型；`Bar` 支持默认日线和可选分钟级 `timestamp`/`timeframe`。
- `data`: AKShare 日线/分钟级数据标准化、CSV 读写，分钟周期支持 `1m`、`5m`、`15m`、`30m`、`60m`。
- `data_manager`: 自选股本地行情文件管理，维护按 `timeframe` 区分的规范主 CSV、增量 CSV、manifest 索引和批量更新流程。
- `stock_catalog`: 本地 A股股票目录加载、搜索、刷新和交易所推断。
- `strategy`: 策略抽象接口。
- `strategy_registry`: 发现内置和 `strategies/` 用户策略、读取/保存策略源码、按构造函数生成参数。
- `indicators`: 计算均线、RSI、布林带、动量、回撤和最新技术指标快照。
- `analytics`: 将回测资金曲线和交易记录转换为收益、基准收益、超额收益、波动、夏普比率、回撤、胜率、盈亏比、持仓暴露和信号归因等指标。
- `portfolio`: 将多个 `Strategy` 按加权投票、等权投票、优先级或主策略辅助确认合成为一个可回测的组合策略。
- `research`: 研究信号层，当前将本地 K线转换为分析帧，并生成轻量缠论二买/二卖、缠论结构分型/笔/线段/递归中枢/背驰确认、Chan Core V2 多级别走势/中枢生命周期/增量缓存诊断、增强 RSI 超买/超卖/修复/背离和综合评分预览。
- `risk`: 汇总确定性风控阈值和回测风险状态。
- `llm`: AI 研究员接口，默认使用 Mock provider，也可通过 `.env.local` 接入 DeepSeek OpenAI-compatible Chat Completions，基于技术指标、信息面摘要和风控上下文输出结构化研究观点。
- `deepseek`: DeepSeek 本地客户端，读取 `.env.local`/环境变量，调用 `https://api.deepseek.com/chat/completions` 并解析 JSON 输出。
- `agent`: AI 指挥台内核，持久化 Agent 任务、步骤、工具调用、权限确认、OpenClaw 外部研究状态和报告；同时提供本地 Memory、Skill、Planner Policy 和计划预览治理能力，并通过 API/CLI/MCP 复用同一套可恢复编排逻辑。
- `automation`: 本地自动化雷达维护内核，持久化配置、状态、周扫描、日判断和运行记录，并向 API/React 暴露最近运行历史与失败诊断。
- `realtime`: 第一版实时盯盘内核，后台轮询当前标的分钟级公开行情，预热策略状态，只对新增 K 线输出 `bar_updated`、`signal_triggered`、心跳和错误事件。
- `strategies`: 示例策略和后续自定义策略目录。
- `paper`: 纸面账户、风控限制、订单执行模拟。
- `backtest`: 单品种事件式回测。
- `paper_service`: 服务器模拟交易服务，输出 JSONL 事件日志。
- `gateways`: A股券商网关候选清单和部署提示。
- `api`: FastAPI 本地接口层，向 React 平台暴露数据、策略、组合、回测、Agent任务、AI研究、纸面交易和风控能力。
- `web`: legacy Streamlit AI量化平台，保留为迁移期间的对照和回退入口。
- `frontend`: React + TypeScript + Vite 平台，默认 Web 操作台，包含 AI指挥台但不包含实盘下单入口。

## 数据流

```text
AKShare/public stock list -> stock_catalog -> data/a_share_stocks.csv -> Web/CLI search
AKShare/public daily or minute data -> normalize_bars -> CSV/local storage
watchlist -> data_manager -> data/market/a_share/{exchange}/{code}/{code}_{exchange}_{timeframe}_{adjust}_latest.csv + increments/ + manifest*.json
CSV/local storage -> Strategy.on_bar -> Signal -> PaperBroker -> equity/trades/logs
CSV/local storage -> indicators/analytics/signal attribution -> FastAPI -> React charts/tables
CSV/local storage -> research Chan/RSI/Chan structure preview -> FastAPI -> React Strategy Workshop
stock_catalog + optional data_manager pre-update + local CSV files -> default Chan multi-level daily-anchor strategy scan, optional research/volume/Chan-structure batch scan -> FastAPI -> React Signal Radar
automation scheduler/manual trigger -> data_manager/default scan -> board Top10 weekly AI deep analysis cache -> OpenClaw Weixin/Feishu notification -> automation state/run logs -> FastAPI -> React 自动任务 diagnostics
current settings + selected Strategy -> realtime monitor -> public minute bars polling -> Strategy.on_bar on new bars -> realtime event cache -> FastAPI -> React 实时盯盘
strategies/*.py -> strategy registry -> selected Strategy -> backtest/paper service
selected Strategy[] -> portfolio aggregation -> backtest/paper service
technical snapshot + information notes + risk context -> MockLLMProvider or DeepSeekLLMProvider -> LLMInsight
React/CLI/MCP/OpenClaw/Weixin prompt -> Agent governance memory/skill/policy -> DeepSeek planner fallback keyword planner -> agent queue/orchestrator -> append-only trace events + data/automation/research/radar/backtest/risk/paper/share tool adapters -> reports -> React AI指挥台 status/log viewer
```

## AI 指挥台与研究员边界

`agent` 是系统级 AI 入口，不替代确定性交易模块。它把来自 React、CLI、MCP、OpenClaw 或微信的自然语言请求转换为可审计任务：

- 任务持久化在 `data/agent/tasks/`，报告持久化在 `data/agent/reports/`，逐事件执行日志持久化在 `data/agent/runs/<task_id>/events.jsonl`。
- HTTP API 和 stdio MCP 通过后台 `AgentTaskQueue` 提交任务并立即返回 `task_id`，React/OpenClaw 通过持久化状态和 trace 跟踪进度；MCP 会为短时间内重复的同源同 prompt 请求写入 `idempotency_key` 并复用未终止任务；`ai-trade agent ...` CLI 默认同步执行，遇到确认时可用 `ai-trade agent approve <task_id>` 续跑。
- DeepSeek planner 可在配置后为自然语言任务选择 `data.update`、`automation.weekly_result`、`research.fundamental`、`research.batch_fundamental`、`radar.scan`、`backtest.run`、`risk.evaluate`、`paper.run`、`share.weixin`，输出会被本地工具注册表过滤；未配置时退回关键词规划。
- Agent tool adapters 复用现有服务能力：`data.update` 调用托管行情维护，`automation.weekly_result` 读取自动化周扫描和周度 AI 深度分析缓存，`research.fundamental` 调用 OpenClaw 外部研究边界，`research.batch_fundamental` 优先复用周度分析缓存、没有缓存时才对周榜候选批量调用 OpenClaw 外部研究，`radar.scan` 调用信号雷达扫描且默认使用缠论多级别日线锚定优化预设，`backtest.run` 调用本地回测，`risk.evaluate` 调用确定性风控，`paper.run` 调用纸面交易重放，`share.weixin` 准备可由 OpenClaw/微信/飞书返回的紧凑摘要，完整研究保留在 Agent 报告中。
- `automation.weekly_result` 具备周榜自恢复行为：当用户明确要求本周/这周结果而本地没有持久化结果、结果已过期、上次成功但文件缺失或上次失败时，会记录 `missing_reason` 并自动触发一次周扫描；扫描完成后会附带可用的周度 AI 深度分析缓存，后续分享优先复用该缓存。
- 周六自动任务是完整周报链路，不只是扫描：它维护科创板和创业板候选行情，生成分板块 Top10 周榜，按科创板 Top10、创业板 Top10、综合非 ST Top10 逐股生成 AI 深度分析缓存，保存到 `data/automation/weekly_analysis/YYYY-Www.json` 和 `weekly_analysis_latest.json`，再通过 OpenClaw 通知命令投递到微信或飞书。未配置 OpenClaw 研究或通知命令时，任务会保留缓存/诊断状态而不是伪造已投递结论。
- OpenClaw/微信长任务采用异步回发边界：任务上下文显式设置 `notify_on_completion` 或 `notification_channel=openclaw` 后，队列线程会在任务进入 `completed`、`failed`、`blocked` 或 `waiting_confirmation` 时调用 OpenClaw 通知命令，把微信摘要或任务状态交给 OpenClaw 发送给用户；通知失败只写入 trace，不改变主任务状态。
- Trace Log 是任务状态之外的 append-only 事件流，记录 `request_received`、`plan_selected`、`tool_started`、`tool_finished`、`tool_failed`、`confirmation_requested`、`approval_recorded`、`task_completed`、`task_failed`、`task_blocked` 和 `orphan_task_marked`，用于复盘 OpenClaw/微信请求的完整执行链。
- `research.fundamental` 是外部信息代理边界；未配置时记录 `not_configured` 状态，不会静默假装完成外部研究。OpenClaw 返回的研究摘要必须带有可验证外部 URL 证据，只有 `openclaw_agent` session 来源但没有网页来源时不能作为基本面结论采纳。
- `research.batch_fundamental` 是 confirm 级外部批量研究边界；读取周榜和准备分享文本本身没有交易副作用，可自动执行。批量研究会从 OpenClaw session 提取 `web_search` 或浏览器工具留下的 URL；若某候选只有无来源摘要，会将该候选研究项降级为 `failed`/`low` 并保留“外部证据不足”原因。`share.weixin` 只生成最终回复文本；默认只在微信里返回已研究候选的核心摘要、未研究扫描候选和报告路径，是否主动投递由异步 OpenClaw 通知命令控制。
- `Agent治理` 页面通过 FastAPI 管理 `data/agent/memory.json`、`data/agent/skills.json`、`data/agent/policy.json`，并提供 plan preview，让用户在执行前看到匹配 Memory、选中 Skill、计划工具、权限和停止条件；同一治理预览也会进入 `AgentOrchestrator`，在没有显式工具覆盖时由 Skill 生成真实任务计划，并用 Planner Policy 控制工具确认/阻断权限。
- confirm 级工具会创建 `TOOL_CONFIRMATION_REQUIRED` 并暂停到 `waiting_confirmation`；前端、CLI 或 MCP 批准后从已完成步骤之后继续执行。自动补周扫描不绕过 `research.batch_fundamental` 的确认边界。
- 实盘、下单、券商委托等请求默认阻断，不能绕过 `PaperBroker`、`risk`、回测/纸面交易或未来实盘前置规则。

## AI 研究员页面边界

`llm` 模块提供 Mock provider 和 DeepSeek provider。它的输出是研究观点，不是实盘指令：

- 输入来自可审计的技术指标快照、用户填写的信息面摘要和风控上下文。
- 输出 `LLMInsight`，包含方向、置信度、建议动作、技术证据、信息面证据、风险提示、provider 和 prompt version。
- React 页面可以显示 AI 观点，并允许用户在组合实验中启用“AI参与评分”作为轻量权重修正。
- AI 观点不能绕过 `PaperBroker`、`risk` 或未来实盘前置规则。

## Web/API 边界

React 是默认浏览器界面，启动脚本为：

```bash
./scripts/run_app.sh
```

该脚本同时启动 FastAPI 和 Vite。FastAPI 只暴露本地研究、回测和纸面交易接口；策略源码写入限制在 `strategies/`，行情 CSV 限制在 `data/`，纸面日志限制在 `logs/`。数据请求统一携带 `timeframe`，默认 `daily`，分钟级请求通过同一套回测和纸面交易链路按更细 K 线粒度驱动 `Strategy.on_bar`。

Streamlit 入口 `./scripts/run_web.sh` 保留为 legacy，不作为新功能默认开发目标。

## 后续接入 vn.py

vn.py 目标结构：

```text
EventEngine + MainEngine + Gateway + CtaStrategyApp/CtaBacktesterApp
```

策略接入方向：

1. 保留当前纯 Python 策略核心。
2. 增加 vn.py `CtaTemplate` 包装层。
3. 将 vn.py 的 `BarData/TickData` 转换为本项目 `Bar`。
4. 将本项目 `Signal` 转换为 vn.py 的 `buy/sell/short/cover`。

这样可以先在免费公开数据和纸面交易里稳定策略，再在券商接口明确后迁移到 vn.py 实盘。

## 内置策略

内置策略聚焦当前单股票、日线、长仓回测引擎可以直接支持的常见策略族：

- 趋势跟随：双均线。
- 均值回归：RSI、布林带。
- 研究信号策略：缠论 + 增强 RSI 预览包装策略、按买卖点确定性、背驰确认、低确定性 T2 门控和动态仓位上限分层调仓的缠论结构策略。
- 突破：Donchian/Turtle 通道突破。
- 动量：固定回看窗口价格动量、放量确认动量。
- MACD 趋势：快慢 EMA 的 MACD 金叉/死叉配合趋势均线过滤。
- 波动突破：ATR 突破入场、ATR 初始止损、ATR 跟踪退出。

当前组合层支持多个策略在同一标的、同一 K线序列上的信号聚合。`PortfolioStrategy` 支持加权投票、等权投票、优先级和主策略辅助确认四种模式；主策略辅助确认要求第一条启用 allocation 先触发信号，辅助策略只能过滤冲突买入或小幅增强顺向买入。`portfolio_presets` 提供稳健趋势均值、动量突破、缠论研究和缠论进攻融合四组预设组合，它们都会展开成普通 `PortfolioStrategy` allocation 后再进入组合预览、回测和纸面交易。配对交易、统计套利和多因子轮动仍需要多标的数据结构、组合层和仓位分配模块扩展，暂不内置到当前单标的策略引擎。
