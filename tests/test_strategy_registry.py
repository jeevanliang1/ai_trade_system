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


def test_builtin_strategy_specs_expose_chinese_names_and_descriptions():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))

    dual = next(spec for spec in specs if spec.class_name == "DualMovingAverageStrategy")
    rsi = next(spec for spec in specs if spec.class_name == "RsiMeanReversionStrategy")

    assert dual.display_name == "双均线趋势"
    assert "快慢均线金叉" in dual.description
    assert rsi.display_name == "RSI均值回归"
    assert "超卖" in rsi.description


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

    assert user_spec.display_name == "MyStrategy"
    assert "自定义策略" in user_spec.description
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


def test_strategy_parameters_include_chinese_guidance_for_tuning():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    dual = next(spec for spec in specs if spec.class_name == "DualMovingAverageStrategy")

    params = {param.name: param for param in inspect_strategy_parameters(dual)}

    assert params["fast_window"].display_name == "快线周期"
    assert "短期均线" in params["fast_window"].description
    assert "更平滑" in params["fast_window"].increase_effect
    assert "更敏感" in params["fast_window"].decrease_effect
    assert params["trade_size"].display_name == "每次交易股数"
    assert "仓位" in params["trade_size"].increase_effect


def test_volume_confirmed_momentum_strategy_metadata_and_parameter_guidance():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(item for item in specs if item.name == "VolumeConfirmedMomentumStrategy")

    assert spec.display_name == "量价动量策略"
    assert "成交量放大" in spec.description

    params = {param.name: param for param in inspect_strategy_parameters(spec)}
    assert params["momentum_window"].display_name == "动量回看周期"
    assert "价格涨幅" in params["min_momentum_pct"].description
    assert "成交量" in params["volume_multiplier"].description
    assert "持仓" in params["max_holding_bars"].description
    assert params["trailing_stop_pct"].display_name == "跟踪止盈回撤"
    assert "最高收盘价回撤" in params["trailing_stop_pct"].description


def test_volume_confirmed_momentum_registry_exposes_tuned_defaults():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(item for item in specs if item.name == "VolumeConfirmedMomentumStrategy")

    defaults = {param.name: param.default for param in inspect_strategy_parameters(spec)}

    assert defaults["momentum_window"] == 15
    assert defaults["min_momentum_pct"] == 0.10
    assert defaults["volume_window"] == 20
    assert defaults["volume_multiplier"] == 1.1
    assert defaults["trend_window"] == 60
    assert defaults["max_holding_bars"] == 45
    assert defaults["trailing_stop_pct"] == 0.18


def test_macd_and_atr_strategies_expose_metadata_and_guidance():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    macd = next(item for item in specs if item.name == "MacdTrendStrategy")
    atr = next(item for item in specs if item.name == "AtrVolatilityBreakoutStrategy")

    assert macd.display_name == "MACD趋势策略"
    assert "MACD" in macd.description
    assert atr.display_name == "ATR波动突破"
    assert "ATR" in atr.description

    macd_params = {param.name: param for param in inspect_strategy_parameters(macd)}
    assert macd_params["fast_period"].display_name == "MACD快线周期"
    assert "EMA" in macd_params["slow_period"].description
    assert "金叉" in macd_params["signal_period"].description

    atr_params = {param.name: param for param in inspect_strategy_parameters(atr)}
    assert atr_params["breakout_window"].display_name == "突破观察窗口"
    assert "ATR" in atr_params["atr_window"].description
    assert "止损" in atr_params["stop_atr_multiplier"].description
    assert "跟踪" in atr_params["trailing_atr_multiplier"].description

    macd_defaults = {param.name: param.default for param in macd_params.values()}
    assert macd_defaults["fast_period"] == 12
    assert macd_defaults["slow_period"] == 18
    assert macd_defaults["signal_period"] == 9
    assert macd_defaults["trend_window"] == 90

    atr_defaults = {param.name: param.default for param in atr_params.values()}
    assert atr_defaults["breakout_window"] == 30
    assert atr_defaults["atr_window"] == 10
    assert atr_defaults["entry_atr_multiplier"] == 0.0
    assert atr_defaults["stop_atr_multiplier"] == 2.0
    assert atr_defaults["trailing_atr_multiplier"] == 3.0
    assert atr_defaults["max_holding_bars"] == 45


def test_chan_structure_strategy_metadata_and_parameter_guidance():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(item for item in specs if item.name == "ChanStructureStrategy")

    assert spec.display_name == "缠论结构策略"
    assert "分型" in spec.description
    assert "中枢" in spec.description

    params = {param.name: param for param in inspect_strategy_parameters(spec)}
    assert params["min_stroke_bars"].display_name == "成笔最小间隔"
    assert "分型" in params["min_stroke_bars"].description
    assert "反弹" in params["min_rebound_pct"].description
    assert "交易更少" in params["min_signal_score"].increase_effect
    assert params["signal_mode"].display_name == "信号模式"
    assert "confirmation" in params["signal_mode"].description
    assert "structure" in params["signal_mode"].description
    assert params["signal_mode"].options == ("all", "confirmation", "structure")
    assert params["signal_mode"].multiple is False
    assert "0" in params["max_holding_bars"].description
    assert params["watch_confirm_bars"].display_name == "背驰观察有效期"
    assert "背驰" in params["watch_confirm_bars"].description
    assert params["allowed_point_types"].display_name == "买卖点类型过滤"
    assert "all" in params["allowed_point_types"].description
    assert "first-buy" in params["allowed_point_types"].description
    assert "third-sell" in params["allowed_point_types"].description
    assert params["allowed_point_types"].options == (
        "all",
        "first-buy",
        "first-sell",
        "second-buy",
        "second-sell",
        "third-buy",
        "third-sell",
    )
    assert params["allowed_point_types"].multiple is True
    assert params["allowed_levels"].display_name == "结构层级过滤"
    assert "segment" in params["allowed_levels"].description
    assert "fractal" in params["allowed_levels"].description
    assert params["allowed_levels"].options == ("all", "segment", "stroke", "fractal")
    assert params["allowed_levels"].multiple is True
    assert params["low_confidence_units"].display_name == "低确定性目标仓位"
    assert "二买" in params["low_confidence_units"].description
    assert params["low_confidence_gate"].display_name == "低确定性门控"
    assert "二买" in params["low_confidence_gate"].description
    assert params["low_confidence_gate"].options == ("off", "divergence", "trend", "divergence_or_trend")
    assert params["low_confidence_min_score"].display_name == "低确定性放行分"
    assert "T2" in params["low_confidence_min_score"].description
    assert params["range_max_units"].display_name == "震荡区最大仓位"
    assert "range" in params["range_max_units"].description
    assert params["position_cap_mode"].display_name == "动态仓位上限"
    assert "trend_risk" in params["position_cap_mode"].description
    assert params["position_cap_mode"].options == ("off", "trend", "risk", "trend_risk")
    assert params["trend_cap_units"].display_name == "趋势不明上限"
    assert "range" in params["trend_cap_units"].description
    assert params["risk_drawdown_cap_pct"].display_name == "浮亏加仓阈值"
    assert "浮亏" in params["risk_drawdown_cap_pct"].description
    assert params["divergence_confirm_units"].display_name == "背驰确认目标仓位"
    assert "背驰" in params["divergence_confirm_units"].description
    assert params["high_confidence_units"].display_name == "高确定性目标仓位"
    assert "三买" in params["high_confidence_units"].description
    assert params["sell_confirm_units"].display_name == "卖出确认保留仓位"
    assert "顶背驰" in params["sell_confirm_units"].description


def test_chan_structure_strategy_registry_exposes_balanced_tuned_defaults():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(item for item in specs if item.name == "ChanStructureStrategy")

    defaults = {param.name: param.default for param in inspect_strategy_parameters(spec)}

    assert defaults["min_signal_score"] == 28.0
    assert defaults["signal_mode"] == "all"
    assert defaults["allowed_point_types"] == "all"
    assert defaults["allowed_levels"] == "all"
    assert defaults["max_holding_bars"] == 15
    assert defaults["watch_confirm_bars"] == 20
    assert defaults["low_confidence_gate"] == "divergence_or_trend"
    assert defaults["low_confidence_min_score"] == 32.0
    assert defaults["range_max_units"] == 1
    assert defaults["position_cap_mode"] == "risk"
    assert defaults["trend_cap_units"] == 2
    assert defaults["risk_drawdown_cap_pct"] == 8.0
    assert defaults["low_confidence_units"] == 1
    assert defaults["divergence_confirm_units"] == 2
    assert defaults["high_confidence_units"] == 3
    assert defaults["sell_confirm_units"] == 1


def test_chan_volume_fusion_strategy_is_registered_with_guidance():
    specs = discover_strategies(user_dir=Path("/tmp/nonexistent-ai-trade-strategies"))
    spec = next(strategy for strategy in specs if strategy.class_name == "ChanVolumeFusionStrategy")

    assert spec.display_name == "缠论量价融合"
    assert "量价动量确认低确定性买点" in spec.description

    parameters = {parameter.name: parameter for parameter in inspect_strategy_parameters(spec)}
    assert parameters["weak_volume_exit_mode"].options == ("reduce", "exit", "ignore")
    assert parameters["low_confidence_requires_volume"].display_name
    assert parameters["volume_boost_units"].description


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
