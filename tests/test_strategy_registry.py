from pathlib import Path

from ai_trade_system.strategy_registry import (
    create_strategy_template,
    discover_strategies,
    instantiate_strategy,
    inspect_strategy_parameters,
    read_strategy_source,
    save_strategy_source,
)


def test_discover_strategies_includes_builtin_dual_moving_average():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))

    names = [spec.name for spec in specs]

    assert "DualMovingAverageStrategy" in names


def test_discover_strategies_loads_user_strategy_from_file(tmp_path):
    strategy_file = tmp_path / "my_strategy.py"
    strategy_file.write_text(
        """
from ai_trade_system.market import Signal
from ai_trade_system.strategy import Strategy

class MyStrategy(Strategy):
    def __init__(self, symbol: str, trade_size: int = 100):
        self.symbol = symbol
        self.trade_size = trade_size

    def on_bar(self, bar):
        return [Signal("buy", bar.symbol, bar.close_price, self.trade_size, "demo")]
""".strip(),
        encoding="utf-8",
    )

    specs = discover_strategies(user_dir=tmp_path)

    user_spec = next(spec for spec in specs if spec.name == "MyStrategy")
    strategy = instantiate_strategy(user_spec, {"symbol": "000001", "trade_size": 300})

    assert strategy.symbol == "000001"
    assert strategy.trade_size == 300


def test_inspect_strategy_parameters_exposes_constructor_defaults(tmp_path):
    strategy_file = tmp_path / "param_strategy.py"
    strategy_file.write_text(
        """
from ai_trade_system.strategy import Strategy

class ParamStrategy(Strategy):
    def __init__(self, symbol: str, fast_window: int = 5, threshold: float = 1.2, enabled: bool = True):
        pass

    def on_bar(self, bar):
        return []
""".strip(),
        encoding="utf-8",
    )
    spec = next(spec for spec in discover_strategies(user_dir=tmp_path) if spec.name == "ParamStrategy")

    params = inspect_strategy_parameters(spec)

    assert [(param.name, param.default, param.annotation) for param in params] == [
        ("symbol", None, "str"),
        ("fast_window", 5, "int"),
        ("threshold", 1.2, "float"),
        ("enabled", True, "bool"),
    ]


def test_save_strategy_source_validates_python_and_sanitizes_filename(tmp_path):
    path = save_strategy_source(tmp_path, "../bad name", create_strategy_template("ExampleStrategy"))

    assert path == tmp_path / "bad_name.py"
    assert "class ExampleStrategy" in read_strategy_source(path)

    try:
        save_strategy_source(tmp_path, "broken", "class Broken(:")
    except ValueError as exc:
        assert "invalid Python" in str(exc)
    else:
        raise AssertionError("invalid strategy source should raise ValueError")
