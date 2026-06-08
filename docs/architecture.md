# 架构说明

## 当前模块

- `market`: 统一的 `Bar` 和 `Signal` 数据模型。
- `data`: AKShare 数据标准化、CSV 读写。
- `strategy`: 策略抽象接口。
- `strategy_registry`: 发现内置和 `strategies/` 用户策略、读取/保存策略源码、按构造函数生成参数。
- `strategies`: 示例策略和后续自定义策略目录。
- `paper`: 纸面账户、风控限制、订单执行模拟。
- `backtest`: 单品种事件式回测。
- `paper_service`: 服务器模拟交易服务，输出 JSONL 事件日志。
- `gateways`: A股券商网关候选清单和部署提示。
- `web`: Streamlit 操作台，复用数据、回测和纸面交易服务，不包含实盘下单入口。

## 数据流

```text
AKShare/public data -> normalize_bars -> CSV/local storage
CSV/local storage -> Strategy.on_bar -> Signal -> PaperBroker -> equity/trades/logs
CSV/local storage -> Streamlit web -> backtest/paper service -> charts/tables
strategies/*.py -> strategy registry -> selected Strategy -> backtest/paper service
```

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
- 突破：Donchian/Turtle 通道突破。
- 动量：固定回看窗口价格动量。

配对交易、统计套利和多因子轮动需要多标的数据结构、组合层和仓位分配模块，暂不内置到当前单标的策略引擎。
