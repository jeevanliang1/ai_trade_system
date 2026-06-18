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

React 工作台包含八个区域：

- `总览`：数据、策略、纸面交易、AI观点和最近回测摘要。
- `数据中心`：下载 AKShare 数据、读取 CSV、生成演示数据、查看 K线和数据健康。
- `策略工坊`：发现内置和用户策略，新建/编辑用户策略，预览信号。
- `组合实验室`：添加多个策略，配置权重和聚合模式，预览组合信号。
- `回测中心`：运行单策略或组合策略回测，查看价格、买卖点、权益、回撤、指标和交易表。
- `信号雷达`：批量扫描股票目录、本地 CSV 候选或当前标的，按缠论/增强 RSI 研究评分排序，标出缺失行情 CSV 的候选，并支持准备缺失数据、保留扫描历史和导出 CSV。
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
- 浏览器验收：浏览器可见变更需运行 headless Chrome 截图流程，并在收尾说明截图路径；无可截图界面时说明原因。
- 风控边界：确认没有新增默认实盘交易入口，AI 观点、回测、纸面交易和风险控制边界仍然清晰。
