# Portfolio Preset Combination Benchmark

Date: 2026-06-19

## Scope

This records fixed six-stock benchmark evidence for the built-in `PortfolioStrategy` preset combinations added on 2026-06-19.

The presets are UI/API templates that generate normal `PortfolioRequest` allocations. They reuse the existing single-symbol `PortfolioStrategy` modes and do not add live trading, multi-symbol holdings, or long-short spread accounting.

## Presets

### `conservative_trend_reversion`

- Name: 稳健趋势均值组合
- Mode: `weighted_vote`
- Allocations:
  - `DualMovingAverageStrategy`, weight `1.0`, role `趋势底座`
  - `AtrVolatilityBreakoutStrategy`, weight `0.8`, role `波动突破`
  - `VolumeConfirmedMomentumStrategy`, weight `0.7`, role `量价确认`
  - `RsiMeanReversionStrategy`, weight `0.55`, role `超卖修复`
  - `BollingerMeanReversionStrategy`, weight `0.45`, role `通道回归`

### `momentum_breakout_stack`

- Name: 动量突破组合
- Mode: `weighted_vote`
- Allocations:
  - `VolumeConfirmedMomentumStrategy`, weight `1.0`, role `量价动量`
  - `AtrVolatilityBreakoutStrategy`, weight `0.9`, role `ATR突破`
  - `DonchianBreakoutStrategy`, weight `0.75`, role `通道突破`
  - `PriceMomentumStrategy`, weight `0.65`, role `价格动量`
  - `MacdTrendStrategy`, weight `0.55`, role `MACD确认`

### `chan_research_stack`

- Name: 缠论研究组合
- Mode: `weighted_vote`
- Allocations:
  - `ChanStructureStrategy`, weight `1.0`, role `缠论结构`
  - `ChanRsiResearchStrategy`, weight `0.75`, role `缠论RSI`
  - `VolumeConfirmedMomentumStrategy`, weight `0.55`, role `量价确认`
  - `AtrVolatilityBreakoutStrategy`, weight `0.45`, role `波动确认`

## Fixed Dataset

Requested range: `20230619` to `20260619`

Actual fixture range: `2023-06-19` to `2026-06-18`

Adjustment: `qfq`

## Backtest Assumptions

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Trade size: strategy defaults
- AI adjustment: disabled

## Verification Command

```bash
PYTHONPATH=src python - <<'PY'
from ai_trade_system.analytics import calculate_backtest_metrics
from ai_trade_system.api.schemas import PortfolioRequest
from ai_trade_system.api.service import _build_portfolio
from ai_trade_system.backtest import BacktestConfig, run_backtest
from ai_trade_system.data import read_bars_csv
from ai_trade_system.portfolio_presets import portfolio_preset_views
from ai_trade_system.strategy_registry import discover_strategies

cases = [
    ("688981", "中芯国际", "SSE", "data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv"),
    ("000858", "五粮液", "SZSE", "data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv"),
    ("601318", "中国平安", "SSE", "data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv"),
    ("600901", "江苏金租", "SSE", "data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv"),
    ("600989", "宝丰能源", "SSE", "data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv"),
    ("603986", "兆易创新", "SSE", "data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv"),
]
strategies = discover_strategies()
for preset_id in ["conservative_trend_reversion", "momentum_breakout_stack", "chan_research_stack"]:
    for symbol, name, exchange, path in cases:
        bars = read_bars_csv(path)
        preset = next(item for item in portfolio_preset_views(strategies, symbol) if item["id"] == preset_id)
        portfolio = PortfolioRequest(
            allocations=[
                {"strategy": allocation["strategy"], "weight": allocation["weight"], "enabled": allocation["enabled"]}
                for allocation in preset["allocations"]
            ],
            mode=preset["mode"],
            ai_adjust=False,
            ai_direction=None,
        )
        result = run_backtest(bars, _build_portfolio(portfolio), BacktestConfig(initial_cash=100000))
        metrics = calculate_backtest_metrics(result.equity_curve, result.trades, 100000)
        print(preset_id, symbol, result.final_equity, metrics.total_return_pct, len(result.trades))
PY
```

## Results: conservative_trend_reversion

| Symbol | Final equity | Strategy return | Benchmark return | Excess return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981` | 129698.52 | 29.6985% | 155.5394% | -125.8409% | -10.2773% | 95 | 63.8298% | 2.7731 |
| `000858` | 86214.13 | -13.7859% | -52.8208% | 39.0349% | -14.8690% | 82 | 37.5000% | 0.4833 |
| `601318` | 101275.95 | 1.2760% | 23.8525% | -22.5765% | -9.5375% | 95 | 51.1111% | 1.5257 |
| `600901` | 100799.52 | 0.7995% | 85.0153% | -84.2158% | -0.4652% | 95 | 66.6667% | 4.8549 |
| `600989` | 101465.32 | 1.4653% | 87.6963% | -86.2310% | -5.2298% | 101 | 45.8333% | 3.1336 |
| `603986` | 230908.76 | 130.9088% | 459.7579% | -328.8491% | -15.3927% | 97 | 53.1915% | 2.0462 |

Summary: average return `25.0604%`, worst return `-13.7859%`, total trades `565`.

## Results: momentum_breakout_stack

| Symbol | Final equity | Strategy return | Benchmark return | Excess return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981` | 106653.83 | 6.6538% | 155.5394% | -148.8856% | -7.4936% | 77 | 31.5789% | 1.5624 |
| `000858` | 90497.88 | -9.5021% | -52.8208% | 43.3187% | -12.6797% | 55 | 29.6296% | 0.4206 |
| `601318` | 100202.32 | 0.2023% | 23.8525% | -23.6502% | -8.0462% | 82 | 52.5000% | 1.1860 |
| `600901` | 100064.79 | 0.0648% | 85.0153% | -84.9505% | -0.3071% | 103 | 43.1373% | 1.2163 |
| `600989` | 101360.11 | 1.3601% | 87.6963% | -86.3362% | -2.1567% | 117 | 41.3793% | 1.7966 |
| `603986` | 256157.65 | 156.1576% | 459.7579% | -303.6003% | -13.1769% | 95 | 45.6522% | 3.1960 |

Summary: average return `25.8227%`, worst return `-9.5021%`, total trades `529`.

## Results: chan_research_stack

| Symbol | Final equity | Strategy return | Benchmark return | Excess return | Max drawdown | Trades | Win rate | Profit factor |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981` | 128715.64 | 28.7156% | 155.5394% | -126.8238% | -9.6657% | 173 | 53.5714% | 2.7405 |
| `000858` | 96540.02 | -3.4600% | -52.8208% | 49.3608% | -19.6692% | 130 | 36.9231% | 0.7990 |
| `601318` | 99714.26 | -0.2857% | 23.8525% | -24.1382% | -5.5566% | 117 | 48.2759% | 1.2192 |
| `600901` | 100046.96 | 0.0470% | 85.0153% | -84.9683% | -0.4960% | 143 | 42.0290% | 1.1533 |
| `600989` | 101950.25 | 1.9503% | 87.6963% | -85.7460% | -2.4667% | 128 | 42.8571% | 1.4409 |
| `603986` | 191631.27 | 91.6313% | 459.7579% | -368.1266% | -15.9987% | 200 | 50.5155% | 2.7287 |

Summary: average return `19.7664%`, worst return `-3.4600%`, total trades `891`.

## Interpretation

The presets prove that the ten built-in strategies can now be combined through the existing portfolio engine and React Portfolio Lab. They are useful for comparison and workflow acceleration.

The fixed fixtures also show the main risk: weighted single-symbol voting can increase trade count and drawdown, especially on weak or declining samples such as 五粮液. Future preset tuning should optimize turnover and drawdown, not only average return.

## Browser Acceptance

Surface: React + FastAPI platform through `./scripts/run_app.sh`, `http://localhost:5173`, Portfolio Lab.

- Desktop Browser check confirmed the `预设组合` panel renders `稳健趋势均值组合`, `动量突破组合`, and `缠论研究组合`.
- Applying `稳健趋势均值组合` expanded the allocation editor to five enabled strategy rows with normalized weights.
- Browser console inspection found `0` warnings or errors after loading the page and applying the preset.
- Desktop screenshot: `/tmp/ai_trade_system_portfolio_presets_desktop.png`
- Mobile viewport screenshot: `/tmp/ai_trade_system_portfolio_presets_mobile_viewport.png`
