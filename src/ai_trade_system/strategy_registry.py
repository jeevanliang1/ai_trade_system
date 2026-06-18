from __future__ import annotations

import importlib
import importlib.util
import inspect
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from ai_trade_system.strategy import Strategy


@dataclass(frozen=True)
class StrategySpec:
    id: str
    name: str
    class_name: str
    source: str
    path: Path | None
    module_name: str | None = None
    display_name: str | None = None
    description: str = ""


@dataclass(frozen=True)
class StrategyParameter:
    name: str
    default: Any
    annotation: str
    display_name: str = ""
    description: str = ""
    increase_effect: str = ""
    decrease_effect: str = ""


@dataclass(frozen=True)
class ParameterGuidance:
    display_name: str
    description: str
    increase_effect: str
    decrease_effect: str


BUILTIN_STRATEGIES = [
    StrategySpec(
        id="builtin:dual_moving_average:DualMovingAverageStrategy",
        name="DualMovingAverageStrategy",
        class_name="DualMovingAverageStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.dual_moving_average",
        display_name="双均线趋势",
        description="快慢均线金叉买入、死叉卖出，适合趋势行情。",
    ),
    StrategySpec(
        id="builtin:popular:BollingerMeanReversionStrategy",
        name="BollingerMeanReversionStrategy",
        class_name="BollingerMeanReversionStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="布林带均值回归",
        description="价格跌破布林带下轨后尝试买入，回归中轨附近卖出，适合震荡行情。",
    ),
    StrategySpec(
        id="builtin:popular:DonchianBreakoutStrategy",
        name="DonchianBreakoutStrategy",
        class_name="DonchianBreakoutStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="通道突破",
        description="突破近期高点入场，跌破近期低点离场，偏趋势跟随。",
    ),
    StrategySpec(
        id="builtin:popular:PriceMomentumStrategy",
        name="PriceMomentumStrategy",
        class_name="PriceMomentumStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="价格动量",
        description="按固定回看窗口的涨跌幅判断动量，强势买入、转弱退出。",
    ),
    StrategySpec(
        id="builtin:popular:VolumeConfirmedMomentumStrategy",
        name="VolumeConfirmedMomentumStrategy",
        class_name="VolumeConfirmedMomentumStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="量价动量策略",
        description="价格上涨动量、成交量放大和趋势过滤同时满足时买入；动量转弱、跌破趋势或持仓超期时卖出。",
    ),
    StrategySpec(
        id="builtin:popular:RsiMeanReversionStrategy",
        name="RsiMeanReversionStrategy",
        class_name="RsiMeanReversionStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="RSI均值回归",
        description="RSI 超卖时买入、超买时卖出，适合短线修复和震荡反弹。",
    ),
    StrategySpec(
        id="builtin:popular:ChanRsiResearchStrategy",
        name="ChanRsiResearchStrategy",
        class_name="ChanRsiResearchStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="缠论RSI研究",
        description="结合缠论二买/二卖和增强 RSI 信号，输出可回测的研究信号。",
    ),
    StrategySpec(
        id="builtin:popular:ChanStructureStrategy",
        name="ChanStructureStrategy",
        class_name="ChanStructureStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
        display_name="缠论结构策略",
        description="从包含关系、分型、笔和中枢结构中识别二买/二卖、三买/三卖；确认模式包含背驰观察、背驰确认和三买/三卖回抽确认，支持可选最大持仓退出。",
    ),
]


def discover_strategies(user_dir: Path | str = "strategies") -> list[StrategySpec]:
    specs = list(BUILTIN_STRATEGIES)
    directory = Path(user_dir)
    if not directory.exists():
        return specs

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = _load_module_from_path(path)
        except Exception:
            continue
        for _, strategy_class in _iter_strategy_classes(module):
            specs.append(
                StrategySpec(
                    id=f"user:{path.stem}:{strategy_class.__name__}",
                    name=strategy_class.__name__,
                    class_name=strategy_class.__name__,
                    source="user",
                    path=path,
                    display_name=strategy_class.__name__,
                    description=f"自定义策略：{strategy_class.__name__}，按本地源码定义的交易逻辑运行。",
                )
            )
    return specs


def load_strategy_class(spec: StrategySpec) -> type[Strategy]:
    if spec.source == "builtin":
        if not spec.module_name:
            raise ValueError(f"builtin strategy missing module name: {spec.id}")
        module = importlib.import_module(spec.module_name)
    elif spec.path is not None:
        module = _load_module_from_path(spec.path)
    else:
        raise ValueError(f"strategy missing source path: {spec.id}")

    strategy_class = getattr(module, spec.class_name)
    if not inspect.isclass(strategy_class) or not issubclass(strategy_class, Strategy) or strategy_class is Strategy:
        raise ValueError(f"{spec.class_name} is not a Strategy subclass")
    return strategy_class


def inspect_strategy_parameters(spec: StrategySpec) -> list[StrategyParameter]:
    strategy_class = load_strategy_class(spec)
    signature = inspect.signature(strategy_class.__init__)
    params: list[StrategyParameter] = []
    for name, parameter in signature.parameters.items():
        if name == "self":
            continue
        default = None if parameter.default is inspect.Parameter.empty else parameter.default
        annotation = _annotation_name(parameter.annotation)
        guidance = _parameter_guidance(name, annotation)
        params.append(
            StrategyParameter(
                name=name,
                default=default,
                annotation=annotation,
                display_name=guidance.display_name,
                description=guidance.description,
                increase_effect=guidance.increase_effect,
                decrease_effect=guidance.decrease_effect,
            )
        )
    return params


def instantiate_strategy(spec: StrategySpec, values: dict[str, Any]) -> Strategy:
    strategy_class = load_strategy_class(spec)
    allowed = {param.name for param in inspect_strategy_parameters(spec)}
    kwargs = {key: value for key, value in values.items() if key in allowed}
    return strategy_class(**kwargs)


def read_strategy_source(path: Path | str) -> str:
    return Path(path).read_text(encoding="utf-8")


def save_strategy_source(user_dir: Path | str, filename: str, source: str) -> Path:
    try:
        compile(source, filename, "exec")
    except SyntaxError as exc:
        raise ValueError(f"invalid Python strategy source: {exc}") from exc

    directory = Path(user_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _sanitize_strategy_filename(filename)
    path.write_text(source, encoding="utf-8")
    return path


def create_strategy_template(class_name: str = "MyStrategy") -> str:
    safe_class = _sanitize_class_name(class_name)
    return f'''from ai_trade_system.market import Signal
from ai_trade_system.strategy import Strategy


class {safe_class}(Strategy):
    def __init__(self, symbol: str, trade_size: int = 100):
        self.symbol = symbol
        self.trade_size = trade_size

    def on_bar(self, bar):
        if bar.symbol != self.symbol:
            return []
        # Replace this demo condition with your own trading logic.
        if bar.close_price > bar.open_price:
            return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "close_above_open")]
        return []
'''


def _load_module_from_path(path: Path) -> ModuleType:
    module_name = f"ai_trade_system_user_strategy_{path.stem}_{abs(hash(path.resolve()))}"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load strategy module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _iter_strategy_classes(module: ModuleType):
    for name, value in inspect.getmembers(module, inspect.isclass):
        if value.__module__ == module.__name__ and issubclass(value, Strategy) and value is not Strategy:
            yield name, value


def _annotation_name(annotation: Any) -> str:
    if annotation is inspect.Parameter.empty:
        return "str"
    if isinstance(annotation, str):
        return annotation
    return getattr(annotation, "__name__", str(annotation))


PARAMETER_GUIDANCE: dict[str, ParameterGuidance] = {
    "symbol": ParameterGuidance(
        display_name="交易标的",
        description="策略只处理这个股票代码的行情和信号。",
        increase_effect="股票代码不是数值参数，不能用调大理解；换代码等于换交易标的。",
        decrease_effect="股票代码不是数值参数，不能用调小理解；换代码等于换交易标的。",
    ),
    "fast_window": ParameterGuidance(
        display_name="快线周期",
        description="用于计算短期均线，决定策略观察短线价格变化的长度。",
        increase_effect="调大后短期均线更平滑，信号更少更慢。",
        decrease_effect="调小后短期均线更敏感，信号更多但噪音也更多。",
    ),
    "slow_window": ParameterGuidance(
        display_name="慢线周期",
        description="用于计算长期均线，作为趋势判断的基准线。",
        increase_effect="调大后更看重长期趋势，入场/离场更慢，交易次数通常减少。",
        decrease_effect="调小后更贴近近期走势，信号更快，但更容易被短期波动干扰。",
    ),
    "trade_size": ParameterGuidance(
        display_name="每次交易股数",
        description="每次买入或卖出时使用的股票数量。",
        increase_effect="调大后仓位更重，盈利和亏损都会被放大。",
        decrease_effect="调小后仓位更轻，收益弹性降低，单次亏损也更小。",
    ),
    "rsi_period": ParameterGuidance(
        display_name="RSI周期",
        description="计算 RSI 指标时使用的回看天数。",
        increase_effect="调大后 RSI 更平滑，信号更稳但反应更慢。",
        decrease_effect="调小后 RSI 更敏感，能更早反应，但假信号更多。",
    ),
    "oversold": ParameterGuidance(
        display_name="超卖阈值",
        description="RSI 低于该值时，策略认为价格可能进入超卖区域并考虑买入。",
        increase_effect="调大后更容易触发买入，机会更多但质量可能下降。",
        decrease_effect="调小后买入更严格，信号更少但通常更偏极端超卖。",
    ),
    "overbought": ParameterGuidance(
        display_name="超买阈值",
        description="RSI 高于该值时，策略认为价格可能进入超买区域并考虑卖出。",
        increase_effect="调大后卖出更晚，可能吃到更多趋势，也可能回吐利润。",
        decrease_effect="调小后卖出更早，保护利润更积极，但可能过早离场。",
    ),
    "window": ParameterGuidance(
        display_name="统计窗口",
        description="计算均值、波动或通道时使用的回看天数。",
        increase_effect="调大后指标更稳定，信号更少更慢。",
        decrease_effect="调小后指标更灵敏，信号更多但更容易受噪音影响。",
    ),
    "num_std": ParameterGuidance(
        display_name="标准差倍数",
        description="布林带上下轨距离中轨的宽度。",
        increase_effect="调大后通道更宽，触发买入更少，条件更严格。",
        decrease_effect="调小后通道更窄，触发买入更多，但误判概率也更高。",
    ),
    "entry_window": ParameterGuidance(
        display_name="突破入场窗口",
        description="判断价格是否突破近期高点时使用的回看天数。",
        increase_effect="调大后突破门槛更高，信号更少但趋势确认更强。",
        decrease_effect="调小后更容易突破入场，信号更快但假突破更多。",
    ),
    "exit_window": ParameterGuidance(
        display_name="突破离场窗口",
        description="判断价格是否跌破近期低点并离场时使用的回看天数。",
        increase_effect="调大后离场更宽松，持仓更久但回撤可能更大。",
        decrease_effect="调小后离场更敏感，止损更快但可能被震荡洗出。",
    ),
    "lookback": ParameterGuidance(
        display_name="回看周期",
        description="策略判断动量或研究信号时使用的历史行情长度。",
        increase_effect="调大后更看重中长期变化，信号更稳但更慢。",
        decrease_effect="调小后更看重近期变化，信号更快但更容易反复。",
    ),
    "entry_threshold": ParameterGuidance(
        display_name="入场涨幅阈值",
        description="价格动量达到该涨幅后，策略才考虑买入。",
        increase_effect="调大后买入更严格，信号更少但动量更强。",
        decrease_effect="调小后更容易买入，机会更多但追弱势反弹的风险更高。",
    ),
    "exit_threshold": ParameterGuidance(
        display_name="离场跌幅阈值",
        description="价格动量跌到该阈值后，策略考虑退出持仓。",
        increase_effect="调大后更容易触发离场，保护更积极但可能提前卖出。",
        decrease_effect="调小后离场更宽松，持仓更久但亏损可能扩大。",
    ),
    "momentum_window": ParameterGuidance(
        display_name="动量回看周期",
        description="比较当前收盘价和多少个交易日前的收盘价，用来判断价格涨幅是否足够强。",
        increase_effect="调大后更看重中期动量，信号更稳但更慢。",
        decrease_effect="调小后更看重短期动量，信号更快但更容易被噪音影响。",
    ),
    "min_momentum_pct": ParameterGuidance(
        display_name="最小动量涨幅",
        description="当前价格相对回看日前价格至少达到多少价格涨幅才允许入场。",
        increase_effect="调大后只追更强的上涨，交易更少。",
        decrease_effect="调小后更容易触发买入，机会更多但强度要求下降。",
    ),
    "volume_window": ParameterGuidance(
        display_name="成交量基准周期",
        description="计算平均成交量时使用的回看天数。",
        increase_effect="调大后成交量基准更稳定，异常放量确认更严格。",
        decrease_effect="调小后成交量基准更贴近近期变化，信号更敏感。",
    ),
    "volume_multiplier": ParameterGuidance(
        display_name="放量倍数",
        description="当前成交量至少达到历史平均成交量的多少倍，才认为有成交量放大确认。",
        increase_effect="调大后需要更明显放量才买入，交易更少但确认更强。",
        decrease_effect="调小后放量要求降低，信号更多但确认力度下降。",
    ),
    "trend_window": ParameterGuidance(
        display_name="趋势过滤周期",
        description="计算趋势均线时使用的回看天数，当前价格需站上该均线才允许买入。",
        increase_effect="调大后更偏中长期趋势过滤，入场更慢。",
        decrease_effect="调小后趋势过滤更灵敏，入场更早但抗噪更弱。",
    ),
    "max_holding_bars": ParameterGuidance(
        display_name="最大持仓天数",
        description="买入后最大持仓多少根日线，超过后即使未触发其他退出条件也会离场；支持该约定的策略可用 0 表示禁用时间退出。",
        increase_effect="调大后允许趋势运行更久，但可能承受更大回撤。",
        decrease_effect="调小后退出更快，资金周转更快但可能错过后续趋势。",
    ),
    "watch_confirm_bars": ParameterGuidance(
        display_name="背驰观察有效期",
        description="T1 底/顶背驰观察信号在多少根日线内等待同向确认、二买/二卖或三买/三卖后再交易；0 表示禁用背驰观察态。",
        increase_effect="调大后背驰观察保留更久，更容易等到后续确认，但可能接收较晚的确认。",
        decrease_effect="调小后背驰观察更快失效，交易更克制，但可能错过慢确认结构。",
    ),
    "min_bars": ParameterGuidance(
        display_name="最少行情数",
        description="研究信号开始计算前必须具备的最少 K 线数量。",
        increase_effect="调大后样本要求更严格，信号更少但基础更充分。",
        decrease_effect="调小后更早开始输出信号，但样本不足时稳定性更差。",
    ),
    "min_signal_score": ParameterGuidance(
        display_name="最低信号分",
        description="研究信号分数达到该值后，才允许转换为交易信号。",
        increase_effect="调大后信号更严格，交易更少。",
        decrease_effect="调小后信号更宽松，交易更多但质量可能下降。",
    ),
    "signal_mode": ParameterGuidance(
        display_name="信号模式",
        description="选择缠论结构策略交易的信号家族：confirmation 交易背驰确认和三买/三卖回抽确认，structure 交易二买/二卖/三买/三卖，all 允许全部结构信号。",
        increase_effect="该参数不是数值大小；切换枚举值会改变参与回测的缠论信号家族。",
        decrease_effect="该参数不是数值大小；confirmation 更聚焦确认类买卖点，structure 更聚焦结构买卖点，all 保留全部信号。",
    ),
    "min_stroke_bars": ParameterGuidance(
        display_name="成笔最小间隔",
        description="相邻顶/底分型之间至少间隔多少根K线，才允许构成缠论笔。",
        increase_effect="调大后成笔更严格，过滤更多短噪音，信号更少。",
        decrease_effect="调小后更容易成笔，结构信号更多但稳定性下降。",
    ),
    "min_rebound_pct": ParameterGuidance(
        display_name="二买二卖确认幅度",
        description="二买需要从底分型反弹、二卖需要从顶分型回落的最小确认比例。",
        increase_effect="调大后确认更严格，信号更少但反弹或回落更充分。",
        decrease_effect="调小后更早触发二买/二卖，信号更多但假突破风险更高。",
    ),
}


def _parameter_guidance(name: str, annotation: str) -> ParameterGuidance:
    if name in PARAMETER_GUIDANCE:
        return PARAMETER_GUIDANCE[name]
    display_name = _humanize_parameter_name(name)
    if annotation in {"int", "float"}:
        return ParameterGuidance(
            display_name=display_name,
            description=f"{display_name} 参数，具体含义由策略源码中的构造函数定义。",
            increase_effect="调大后该条件或数量的影响更强，建议通过回测确认收益和回撤变化。",
            decrease_effect="调小后该条件或数量的影响更弱，建议通过回测确认信号频率变化。",
        )
    return ParameterGuidance(
        display_name=display_name,
        description=f"{display_name} 参数，具体含义由策略源码中的构造函数定义。",
        increase_effect="该参数不适合简单按调大理解，修改前先确认源码含义。",
        decrease_effect="该参数不适合简单按调小理解，修改前先确认源码含义。",
    )


def _humanize_parameter_name(name: str) -> str:
    return name.replace("_", " ")


def _sanitize_strategy_filename(filename: str) -> str:
    base = Path(filename).name
    if base.endswith(".py"):
        base = base[:-3]
    base = re.sub(r"[^A-Za-z0-9_]+", "_", base).strip("_") or "strategy"
    return f"{base}.py"


def _sanitize_class_name(class_name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", class_name).strip("_") or "MyStrategy"
    if cleaned[0].isdigit():
        cleaned = f"Strategy{cleaned}"
    return cleaned
