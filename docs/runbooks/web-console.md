# React Web 平台运行手册

## 用途

默认 Web 操作台是 React + FastAPI AI量化平台工作台，用于个人本地或服务器查看 A股公开数据、管理和编辑用户策略、组合多个策略、运行回测、查看信号预览、资金曲线、交易记录、纸面交易日志、风险状态和 Mock AI 研究观点。

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

## 常见输入

- CSV 数据：默认 `data/000001_daily.csv`
- 股票目录：默认 `data/a_share_stocks.csv`，用于按名称或代码搜索 A股标的
- 纸面交易日志：默认 `logs/paper_events.jsonl`
- 策略：内置双均线、RSI 均值回归、布林带均值回归、Donchian/Turtle 突破、价格动量，以及 `strategies/` 下用户自定义策略
- 信息面摘要：AI研究员页的手工文本输入，先用于 Mock LLM 观点生成
- 风控阈值：侧边栏的最大回撤、单笔最大金额、最小现金余额、最大持仓股数

## 页面结构

React 工作台包含八个区域：

- `总览`：数据、策略、纸面交易、AI观点和最近回测摘要。
- `数据中心`：下载 AKShare 数据、读取 CSV、生成演示数据、查看 K线和数据健康。
- `策略工坊`：发现内置和用户策略，新建/编辑用户策略，预览信号。
- `组合实验室`：添加多个策略，配置权重和聚合模式，预览组合信号。
- `回测中心`：运行单策略或组合策略回测，查看价格、买卖点、权益、回撤、指标和交易表。
- `AI研究员`：基于技术指标、信息面摘要和风控上下文生成结构化 Mock AI 观点。
- `纸面交易`：重放 CSV 行情并输出 JSONL 事件日志。
- `风控`：查看确定性风控阈值和回测风险状态。

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

## AI研究员

AI研究员当前使用 `MockLLMProvider`：

- 输入：最新技术指标快照、信息面摘要、风控上下文、提示词模式。
- 输出：方向、置信度、建议动作、技术证据、信息面证据、风险提示、provider、prompt version。
- 可勾选“显示Prompt快照”查看模型输入。
- 真实 API 接入应实现同一 provider 接口，不应绕过风控和纸面/回测流程。

如果 AKShare 未安装，页面的数据下载会提示安装 `.[web,data]`。

## 数据下载排障

页面的“下载日线数据”依赖 AKShare。下载顺序为东方财富、腾讯、新浪，前一个源在当前网络下不可用时会自动尝试下一个源。

- 如果提示缺少 AKShare，运行 `python -m pip install -e ".[web,data]"` 或 `python -m pip install akshare`。
- 如果提示 AKShare request failed，说明三个数据源都不可用，优先检查服务器代理、防火墙或到行情源的访问。
- 网络不可用时，可以先把行情 CSV 放到 `data/` 目录，再用 Web 页面读取 CSV 跑回测和纸面交易。
- 如果只是想试用平台流程，点击数据中心的“生成演示数据”，会向当前 CSV 路径写入一份确定性的本地演示 K线。

## 股票目录刷新与搜索

Web 侧边栏启动时只加载本地股票目录，不会自动联网刷新。

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
