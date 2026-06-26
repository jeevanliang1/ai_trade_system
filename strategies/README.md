# 自定义策略目录

这个目录用于放你自己的策略草稿、研究脚本或后续 vn.py `CtaTemplate` 策略文件。

Web 操作台会自动发现这个目录下的 `.py` 文件。文件中需要定义继承 `ai_trade_system.strategy.Strategy` 的类。

当前可运行的内置示例策略在：

```text
src/ai_trade_system/strategies/
```

默认内置策略聚焦缠论核心：

- `ChanRsiResearchStrategy`: 缠论 + 增强 RSI 研究预览策略。
- `ChanStructureStrategy`: 包含关系、分型、笔和中枢驱动的缠论结构策略，并按二买/背驰确认/三买等确定性分层调整仓位单位；普通二买/二卖 T2 默认还会经过低确定性门控，买入目标仓位还会受动态风险预算约束。
- `ChanVolumeFusionStrategy`: 缠论结构主导、量价动量辅助的融合策略；二买默认需要放量确认，三买/确认买点可放量加仓，弱量价时结合延续趋势破坏、严重弱动量和缠论空头上下文再减仓。
- `ChanMultiLevelReversalStrategy`: 以日线结构作为主锚点，结合 `60m/30m` 等低级别确认、执行价优化和持仓风险控制。

简单趋势、均值回归、突破、MACD、ATR 等模板代码仍保留在源码中供历史测试、CLI 或自定义策略参考，但不再作为默认策略列表或默认组合入口展示。

建议先把策略核心写成纯 Python，确认数据、回测、纸面交易都能跑通；实盘券商接口确定后，再添加 vn.py 包装层。

最小策略示例：

```python
from ai_trade_system.market import Signal
from ai_trade_system.strategy import Strategy


class MyStrategy(Strategy):
    def __init__(self, symbol: str, trade_size: int = 100):
        self.symbol = symbol
        self.trade_size = trade_size

    def on_bar(self, bar):
        if bar.symbol != self.symbol:
            return []
        if bar.close_price > bar.open_price:
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "close_above_open")]
        return []
```

构造函数里的参数会在 Web 回测和纸面交易页面自动变成输入控件。用户策略会作为本机 Python 代码执行，只运行你信任的策略。
