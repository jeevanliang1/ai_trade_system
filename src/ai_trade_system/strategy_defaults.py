from __future__ import annotations

from typing import Any


DEFAULT_SCAN_SCORE_MODE = "chan_multilevel_daily_anchor"
DEFAULT_SCAN_STRATEGY_ID = "builtin:popular:ChanMultiLevelReversalStrategy"

CHAN_DAILY_ANCHOR_SCAN_PARAMS: dict[str, Any] = {
    "entry_mode": "daily_anchor",
    "confirm_timeframe": "60m",
    "risk_timeframe": "30m",
    "minute_missing_policy": "daily_only",
    "lower_level_policy": "confirm_only",
    "min_confirm_score": 28.0,
    "min_risk_score": 24.0,
    "minute_sell_mode": "reduce",
    "max_holding_bars": 30,
}


def chan_daily_anchor_scan_params(
    *,
    symbol: str,
    exchange: str,
    adjust: str = "qfq",
    min_bars: int | None = None,
    lookback: int | None = None,
) -> dict[str, Any]:
    params = {
        **CHAN_DAILY_ANCHOR_SCAN_PARAMS,
        "symbol": symbol,
        "exchange": exchange,
        "adjust": adjust,
    }
    if min_bars is not None:
        params["min_bars"] = min_bars
    if lookback is not None:
        params["lookback"] = lookback
    return params
