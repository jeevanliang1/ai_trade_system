# Popular Strategy Expansion Benchmark

Date: 2026-06-19

## Scope

This records fixed six-stock benchmark evidence for the 2026-06-19 popular strategy expansion:

- Tuned `VolumeConfirmedMomentumStrategy` defaults and added `trailing_stop_pct`.
- Added `MacdTrendStrategy`.
- Added `AtrVolatilityBreakoutStrategy`.

These are backtest validation records, not live-trading recommendations or return promises.

## Fixed Dataset

Requested range: `20230619` to `20260619`

Actual fixture range: `2023-06-19` to `2026-06-18`

Adjustment: `qfq`

| Symbol | Name | Exchange | CSV path | Rows | Start | End |
|---|---:|---|---|---:|---|---|
| `688981` | 中芯国际 | `SSE` | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720 | 2023-06-19 | 2026-06-18 |
| `000858` | 五粮液 | `SZSE` | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| `601318` | 中国平安 | `SSE` | `data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| `600901` | 江苏金租 | `SSE` | `data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| `600989` | 宝丰能源 | `SSE` | `data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |
| `603986` | 兆易创新 | `SSE` | `data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv` | 726 | 2023-06-19 | 2026-06-18 |

## Backtest Assumptions

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Trade size: default `100`

## Final Strategy Parameters

`VolumeConfirmedMomentumStrategy`:

- `momentum_window=15`
- `min_momentum_pct=0.10`
- `volume_window=20`
- `volume_multiplier=1.1`
- `trend_window=60`
- `max_holding_bars=45`
- `trailing_stop_pct=0.18`
- `trade_size=100`

`MacdTrendStrategy`:

- `fast_period=12`
- `slow_period=18`
- `signal_period=9`
- `trend_window=90`
- `trade_size=100`

`AtrVolatilityBreakoutStrategy`:

- `breakout_window=30`
- `atr_window=10`
- `entry_atr_multiplier=0.0`
- `stop_atr_multiplier=2.0`
- `trailing_atr_multiplier=3.0`
- `max_holding_bars=45`
- `trade_size=100`

## Verification Command

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.strategies.popular import (
    AtrVolatilityBreakoutStrategy,
    MacdTrendStrategy,
    VolumeConfirmedMomentumStrategy,
)

cases = [
    ("688981", "中芯国际", "SSE", "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"),
    ("000858", "五粮液", "SZSE", "data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv"),
    ("601318", "中国平安", "SSE", "data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv"),
    ("600901", "江苏金租", "SSE", "data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv"),
    ("600989", "宝丰能源", "SSE", "data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv"),
    ("603986", "兆易创新", "SSE", "data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv"),
]

strategies = [
    ("VolumeConfirmedMomentumStrategy", VolumeConfirmedMomentumStrategy),
    ("MacdTrendStrategy", MacdTrendStrategy),
    ("AtrVolatilityBreakoutStrategy", AtrVolatilityBreakoutStrategy),
]

for strategy_name, strategy_cls in strategies:
    print(f"## {strategy_name}")
    for symbol, name, exchange, path in cases:
        bars = read_bars_csv(path)
        result = run_backtest(bars, strategy_cls(symbol=symbol), BacktestConfig(initial_cash=100000))
        metrics = calculate_backtest_metrics(result.equity_curve, result.trades, 100000)
        print(symbol, name, result.final_equity, metrics.total_return_pct, len(result.trades))
PY
```

## Results: VolumeConfirmedMomentumStrategy

| Symbol | Final equity | Strategy return | Benchmark return | Excess return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981` | 105061.56 | 5.0616% | 155.5394% | -150.4778% | -2.6544% | 18 | 33.3333% | 4.1835 |
| `000858` | 101271.13 | 1.2711% | -52.8208% | 54.0919% | -2.5196% | 6 | 66.6667% | 1.9764 |
| `601318` | 101384.58 | 1.3846% | 23.8525% | -22.4679% | -0.6662% | 10 | 80.0000% | 170.9785 |
| `600901` | 100112.14 | 0.1121% | 85.0153% | -84.9032% | -0.0550% | 6 | 66.6667% | 7.4981 |
| `600989` | 100479.32 | 0.4793% | 87.6963% | -87.2170% | -0.5218% | 16 | 37.5000% | 2.1308 |
| `603986` | 147737.95 | 47.7380% | 459.7579% | -412.0199% | -4.3074% | 23 | 45.4545% | 5.5089 |

Summary: average return `9.3411%`, worst return `0.1121%`, total trades `79`.

Comparison against the previous default six-stock run:

- Previous default average return: `5.6022%`.
- Tuned default average return: `9.3411%`.
- Previous worst return: `0.0683%`.
- Tuned worst return: `0.1121%`.
- Trade count stayed comparable: previous `80`, tuned `79`.
- Trade-off: 中芯国际 return fell from `8.6686%` to `5.0616%`; the average improvement was driven mainly by stronger 兆易创新 participation.

## Results: MacdTrendStrategy

| Symbol | Final equity | Strategy return | Benchmark return | Excess return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981` | 102572.43 | 2.5724% | 155.5394% | -152.9670% | -2.2962% | 21 | 20.0000% | 2.3598 |
| `000858` | 99338.23 | -0.6618% | -52.8208% | 52.1590% | -1.7578% | 14 | 42.8571% | 0.5326 |
| `601318` | 100723.22 | 0.7232% | 23.8525% | -23.1293% | -1.2380% | 22 | 36.3636% | 1.4637 |
| `600901` | 99886.94 | -0.1131% | 85.0153% | -85.1284% | -0.1367% | 46 | 21.7391% | 0.5116 |
| `600989` | 100270.59 | 0.2706% | 87.6963% | -87.4257% | -0.5731% | 40 | 35.0000% | 1.2932 |
| `603986` | 122814.72 | 22.8147% | 459.7579% | -436.9432% | -8.1050% | 36 | 33.3333% | 2.9501 |

Summary: average return `4.2677%`, worst return `-0.6618%`, total trades `179`.

Interpretation: MACD adds a recognizable trend-following template and works on strong momentum samples, but still churns on some stable or declining stocks. It should be treated as a combinable signal source rather than a standalone default recommendation.

## Results: AtrVolatilityBreakoutStrategy

| Symbol | Final equity | Strategy return | Benchmark return | Excess return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981` | 105058.07 | 5.0581% | 155.5394% | -150.4813% | -3.1462% | 16 | 50.0000% | 3.2876 |
| `000858` | 100072.58 | 0.0726% | -52.8208% | 52.8934% | -3.2900% | 10 | 60.0000% | 1.0542 |
| `601318` | 101636.63 | 1.6366% | 23.8525% | -22.2159% | -0.7481% | 18 | 44.4444% | 2.2216 |
| `600901` | 99993.46 | -0.0065% | 85.0153% | -85.0218% | -0.1326% | 24 | 41.6667% | 0.9664 |
| `600989` | 101049.97 | 1.0500% | 87.6963% | -86.6463% | -0.6588% | 20 | 30.0000% | 2.5563 |
| `603986` | 146765.87 | 46.7659% | 459.7579% | -412.9920% | -5.5921% | 15 | 71.4286% | 10.9892 |

Summary: average return `9.0961%`, worst return `-0.0065%`, total trades `103`.

Interpretation: ATR breakout is the strongest of the two new additions on this fixture set and is a useful complement to volume-confirmed momentum. It still underperforms buy-and-hold in the high-beta winners because this engine uses fixed 100-share trades rather than full capital allocation.

## Browser Acceptance

React + FastAPI platform was started with `./scripts/run_app.sh`.

Captured with:

```bash
node scripts/capture_app_screenshots.mjs \
  --url http://localhost:5173 \
  --out-dir /tmp \
  --prefix ai_trade_system_strategy_expansion
```

Screenshots:

- Desktop: `/tmp/ai_trade_system_strategy_expansion_desktop_1440.png` (`1440x1024`)
- Mobile: `/tmp/ai_trade_system_strategy_expansion_mobile_390.png` (`390x844`)

API strategy visibility check:

```text
MacdTrendStrategy MACD趋势策略 6
AtrVolatilityBreakoutStrategy ATR波动突破 8
VolumeConfirmedMomentumStrategy 量价动量策略 9
total 11
```
