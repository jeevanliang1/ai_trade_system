# Volume Momentum Strategy Benchmark

Date: 2026-06-19

## Fixed Dataset

- 中芯国际: `688981` / `SSE`
- 五粮液: `000858` / `SZSE`
- Requested window: `20230619` to `20260619`
- Actual latest trading day returned by AKShare: `2026-06-18`
- Adjust: `qfq`

## Local Persistent Paths

- `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

These data files are local benchmark fixtures and are ignored by git through `data/*`. Re-run the update command only when intentionally refreshing the benchmark window.

## Strategy Parameters

Default `VolumeConfirmedMomentumStrategy` parameters:

- `momentum_window=20`
- `min_momentum_pct=0.08`
- `volume_window=20`
- `volume_multiplier=1.5`
- `trend_window=60`
- `max_holding_bars=20`
- `trade_size=100`

## Data Update Command

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.data_manager import update_watchlist_data

stocks = [
    {"code": "688981", "name": "中芯国际", "exchange": "SSE"},
    {"code": "000858", "name": "五粮液", "exchange": "SZSE"},
]
print(update_watchlist_data(stocks, start_date="20230619", end_date="20260619", adjust="qfq", if_stale=True))
PY
```

## Backtest Command

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.strategies.popular import VolumeConfirmedMomentumStrategy

cases = [
    ("688981", "中芯国际", "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"),
    ("000858", "五粮液", "data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv"),
]
for symbol, name, path in cases:
    bars = read_bars_csv(path)
    strategy = VolumeConfirmedMomentumStrategy(symbol=symbol)
    result = run_backtest(bars, strategy, BacktestConfig(initial_cash=100000))
    metrics = calculate_backtest_metrics(result.equity_curve, result.trades, 100000)
    print(
        f"{symbol}\t{name}\trows={len(bars)}\t"
        f"start={bars[0].trading_day}\tend={bars[-1].trading_day}\t"
        f"final_equity={result.final_equity:.2f}\ttrades={len(result.trades)}\t"
        f"return_pct={metrics.total_return_pct:.4f}\tbenchmark_return_pct={metrics.benchmark_return_pct:.4f}\t"
        f"max_drawdown_pct={metrics.max_drawdown_pct:.4f}"
    )
PY
```

## Results

```text
688981	中芯国际	rows=720	start=2023-06-19	end=2026-06-18	final_equity=108668.64	trades=14	return_pct=8.6686	benchmark_return_pct=155.5394	max_drawdown_pct=-2.0016
000858	五粮液	rows=726	start=2023-06-19	end=2026-06-18	final_equity=102824.91	trades=4	return_pct=2.8249	benchmark_return_pct=-52.8208	max_drawdown_pct=-2.4964
```

Interpretation: this is a repeatable baseline for comparing later strategy revisions. It is not a performance claim or live-trading recommendation.
