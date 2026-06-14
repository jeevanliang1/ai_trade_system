from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from ai_trade_system.market import Bar


FRAME_COLUMNS = ["trading_day", "symbol", "exchange", "open", "high", "low", "close", "volume", "turnover"]


def bars_to_frame(bars: Sequence[Bar]) -> pd.DataFrame:
    rows = [
        {
            "trading_day": bar.trading_day,
            "symbol": bar.symbol,
            "exchange": bar.exchange,
            "open": float(bar.open_price),
            "high": float(bar.high_price),
            "low": float(bar.low_price),
            "close": float(bar.close_price),
            "volume": float(bar.volume),
            "turnover": float(bar.turnover),
        }
        for bar in bars
    ]
    frame = pd.DataFrame(rows, columns=FRAME_COLUMNS)
    if frame.empty:
        return frame
    return frame.sort_values("trading_day").reset_index(drop=True)
