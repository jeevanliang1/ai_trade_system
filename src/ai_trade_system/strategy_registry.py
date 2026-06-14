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


@dataclass(frozen=True)
class StrategyParameter:
    name: str
    default: Any
    annotation: str


BUILTIN_STRATEGIES = [
    StrategySpec(
        id="builtin:dual_moving_average:DualMovingAverageStrategy",
        name="DualMovingAverageStrategy",
        class_name="DualMovingAverageStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.dual_moving_average",
    ),
    StrategySpec(
        id="builtin:popular:BollingerMeanReversionStrategy",
        name="BollingerMeanReversionStrategy",
        class_name="BollingerMeanReversionStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
    ),
    StrategySpec(
        id="builtin:popular:DonchianBreakoutStrategy",
        name="DonchianBreakoutStrategy",
        class_name="DonchianBreakoutStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
    ),
    StrategySpec(
        id="builtin:popular:PriceMomentumStrategy",
        name="PriceMomentumStrategy",
        class_name="PriceMomentumStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
    ),
    StrategySpec(
        id="builtin:popular:RsiMeanReversionStrategy",
        name="RsiMeanReversionStrategy",
        class_name="RsiMeanReversionStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
    ),
    StrategySpec(
        id="builtin:popular:ChanRsiResearchStrategy",
        name="ChanRsiResearchStrategy",
        class_name="ChanRsiResearchStrategy",
        source="builtin",
        path=None,
        module_name="ai_trade_system.strategies.popular",
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
        params.append(StrategyParameter(name=name, default=default, annotation=annotation))
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
