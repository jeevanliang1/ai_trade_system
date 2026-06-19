# 架构说明

## 当前模块

- `market`: 统一的 `Bar` 和 `Signal` 数据模型。
- `data`: AKShare 数据标准化、CSV 读写。
- `data_manager`: 自选股本地行情文件管理，维护规范主 CSV、每日增量 CSV、manifest 索引和批量更新流程。
- `stock_catalog`: 本地 A股股票目录加载、搜索、刷新和交易所推断。
- `strategy`: 策略抽象接口。
- `strategy_registry`: 发现内置和 `strategies/` 用户策略、读取/保存策略源码、按构造函数生成参数。
- `indicators`: 计算均线、RSI、布林带、动量、回撤和最新技术指标快照。
- `analytics`: 将回测资金曲线和交易记录转换为收益、基准收益、超额收益、波动、夏普比率、回撤、胜率、盈亏比、持仓暴露和信号归因等指标。
- `portfolio`: 将多个 `Strategy` 按加权投票、等权投票、优先级或主策略辅助确认合成为一个可回测的组合策略。
- `research`: 研究信号层，当前将本地 K线转换为分析帧，并生成轻量缠论二买/二卖、缠论结构分型/笔/线段/递归中枢/背驰确认、Chan Core V2 多级别走势/中枢生命周期/增量缓存诊断、增强 RSI 超买/超卖/修复/背离和综合评分预览。
- `risk`: 汇总确定性风控阈值和回测风险状态。
- `llm`: Mock LLM 研究员接口，基于技术指标、信息面摘要和风控上下文输出结构化研究观点。
- `strategies`: 示例策略和后续自定义策略目录。
- `paper`: 纸面账户、风控限制、订单执行模拟。
- `backtest`: 单品种事件式回测。
- `paper_service`: 服务器模拟交易服务，输出 JSONL 事件日志。
- `gateways`: A股券商网关候选清单和部署提示。
- `api`: FastAPI 本地接口层，向 React 平台暴露数据、策略、组合、回测、AI研究、纸面交易和风控能力。
- `web`: legacy Streamlit AI量化平台，保留为迁移期间的对照和回退入口。
- `frontend`: React + TypeScript + Vite 平台，默认 Web 操作台，不包含实盘下单入口。

## 数据流

```text
AKShare/public stock list -> stock_catalog -> data/a_share_stocks.csv -> Web/CLI search
AKShare/public data -> normalize_bars -> CSV/local storage
watchlist -> data_manager -> data/market/a_share/{exchange}/{code}/{code}_{exchange}_daily_{adjust}_latest.csv + increments/ + manifest.json
CSV/local storage -> Strategy.on_bar -> Signal -> PaperBroker -> equity/trades/logs
CSV/local storage -> indicators/analytics/signal attribution -> FastAPI -> React charts/tables
CSV/local storage -> research Chan/RSI/Chan structure preview -> FastAPI -> React Strategy Workshop
stock_catalog + optional data_manager pre-update + local CSV files -> research/volume/Chan-structure batch scan -> FastAPI -> React Signal Radar
strategies/*.py -> strategy registry -> selected Strategy -> backtest/paper service
selected Strategy[] -> portfolio aggregation -> backtest/paper service
technical snapshot + information notes + risk context -> MockLLMProvider -> LLMInsight
```

## AI 研究员边界

`llm` 模块当前只提供 Mock provider 和结构化接口。它的输出是研究观点，不是实盘指令：

- 输入来自可审计的技术指标快照、用户填写的信息面摘要和风控上下文。
- 输出 `LLMInsight`，包含方向、置信度、建议动作、技术证据、信息面证据、风险提示、provider 和 prompt version。
- React 页面可以显示 AI 观点，并允许用户在组合实验中启用“AI参与评分”作为轻量权重修正。
- AI 观点不能绕过 `PaperBroker`、`risk` 或未来实盘前置规则。

## Web/API 边界

React 是默认浏览器界面，启动脚本为：

```bash
./scripts/run_app.sh
```

该脚本同时启动 FastAPI 和 Vite。FastAPI 只暴露本地研究、回测和纸面交易接口；策略源码写入限制在 `strategies/`，行情 CSV 限制在 `data/`，纸面日志限制在 `logs/`。

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
