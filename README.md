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

使用 AKShare 下载日线数据并保存为 CSV：

```bash
python -m ai_trade_system.cli download \
  --symbol 000001 \
  --exchange SZSE \
  --start 20240101 \
  --end 20241231 \
  --output data/000001_daily.csv
```

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

## 打开 React Web 平台

默认 Web 平台使用 React + FastAPI，包含数据下载、CSV 查看、策略管理、策略编辑、策略选择回测、组合实验室、信号预览、资金曲线、买卖点、交易记录、纸面交易日志、风控和 Mock AI 研究员。

安装 API 依赖并安装前端依赖：

```bash
python -m pip install -e ".[api,data]"
cd frontend && npm install && cd ..
```

启动 React 平台：

```bash
./scripts/run_app.sh
```

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
- `DonchianBreakoutStrategy`: Donchian/Turtle 突破入场、跌破退出通道离场。
- `PriceMomentumStrategy`: 价格动量入场、负动量退出。

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
