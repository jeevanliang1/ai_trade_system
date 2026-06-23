# AKShare Minute Data Design

## Goal

接入 AKShare A股分钟级 K 线，并让数据下载、本地托管、API、CLI、回测、纸面交易、研究信号和 React 操作台都能识别同一个行情周期字段。现有日线行为保持默认兼容。

## Approach

采用统一 `timeframe` 字段，而不是单独新增一套分钟数据系统。`daily` 继续使用现有日线接口、CSV 形态和默认路径；分钟线使用 `1m`、`5m`、`15m`、`30m`、`60m`，通过 AKShare 分时接口下载，持久化到 `data/market/a_share/{exchange}/{code}/{code}_{exchange}_{timeframe}_{adjust}_latest.csv`。

`Bar` 保留现有构造方式，新增可选 `timestamp` 和 `timeframe`。日线 `timestamp` 为空或等于交易日，分钟线 `timestamp` 精确到分钟。CSV 写出新增 `timestamp`、`timeframe` 两列，读取旧 CSV 时自动补 `timeframe=daily`，从而不破坏现有测试数据和本地文件。

## Data Flow

- API/CLI/React 设置增加 `timeframe`，默认 `daily`。
- `fetch_akshare_bars()` 根据周期分派：
  - `daily` -> 现有 `fetch_akshare_daily_bars()`。
  - 分钟周期 -> AKShare `stock_zh_a_minute()`，用 `sh/sz/bj` 市场前缀和 `period` 参数。
- `data_manager` 的托管文件、增量文件、manifest、状态结果都记录 `timeframe`。
- 回测、纸面交易、指标、研究信号继续消费 `list[Bar]`，不改变策略接口；策略会在分钟数据上按更细粒度 `on_bar()`。

## Error Handling

不支持的周期返回明确 400/ValueError。AKShare 分钟接口失败时返回友好 RuntimeError，说明可以使用已有 CSV。`1m` 的历史深度和复权限制由文档和 UI 提示暴露，不在本地伪造长期 1 分钟数据。

## Testing

先添加失败测试，再实现：

- 数据层：分钟行标准化、CSV 兼容旧格式、分钟 fetch 调用 AKShare 参数。
- 数据管理：`timeframe` 路径、manifest、增量合并按 timestamp 去重。
- API/CLI：settings/request 透传 timeframe，下载分钟数据写入对应路径。
- React：数据中心可选择周期，下载按钮和健康面板显示周期，自选股托管状态区分周期。

## Scope Notes

本次不重写缠论算法，也不改变策略默认参数；因此固定六股票策略基准只有在策略信号逻辑被改动时才需要重跑。本次会验证分钟数据能进入现有回测链路。
