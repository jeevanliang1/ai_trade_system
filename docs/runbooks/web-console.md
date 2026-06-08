# Streamlit Web 操作台运行手册

## 用途

Web 操作台用于个人本地或服务器查看 A股公开数据、管理和编辑用户策略、选择策略运行回测、查看信号预览、资金曲线、交易记录和纸面交易日志。

它不包含实盘下单入口。实盘券商网关必须在接口、风控和运行规则明确后单独接入。

## 启动

安装依赖：

```bash
python -m pip install -e ".[web,data]"
```

启动：

```bash
./scripts/run_web.sh
```

默认地址：

```text
http://localhost:8501
```

服务器部署时应放在安全网络或反向代理之后，不要直接公网裸露。

## 常见输入

- CSV 数据：默认 `data/000001_daily.csv`
- 纸面交易日志：默认 `logs/paper_events.jsonl`
- 策略：内置双均线、RSI 均值回归、布林带均值回归、Donchian/Turtle 突破、价格动量，以及 `strategies/` 下用户自定义策略

## 策略页

策略页展示策略列表、来源、策略文件路径，并支持新建和编辑 `strategies/` 下的用户策略。

回测页和纸面交易页都可以选择策略。策略构造函数参数会自动渲染成输入控件。

信号预览不等同于成交结果；实际成交仍以回测或纸面交易页经过资金、滑点、手续费和风控后的结果为准。

用户策略会作为本机 Python 代码执行，只编辑和运行可信策略。

如果 AKShare 未安装，页面的数据下载会提示安装 `.[web,data]`。

## 数据下载排障

页面的“下载日线数据”依赖 AKShare。下载顺序为东方财富、腾讯、新浪，前一个源在当前网络下不可用时会自动尝试下一个源。

- 如果提示缺少 AKShare，运行 `python -m pip install -e ".[web,data]"` 或 `python -m pip install akshare`。
- 如果提示 AKShare request failed，说明三个数据源都不可用，优先检查服务器代理、防火墙或到行情源的访问。
- 网络不可用时，可以先把行情 CSV 放到 `data/` 目录，再用 Web 页面读取 CSV 跑回测和纸面交易。
