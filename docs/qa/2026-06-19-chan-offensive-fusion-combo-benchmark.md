# Chan Offensive Fusion Combo Benchmark

Date: 2026-06-19

## Scope

This QA record covers the offensive Chan-primary combination update:

- `ChanVolumeFusionStrategy` keeps weak volume from reducing exposure while price remains above the continuation trend average, unless momentum is severely weak or Chan Core V2 context turns bearish.
- `severe_weak_momentum_pct` default is tuned from `-0.06` to `-0.04` after the fixed-six grid showed better average return, better best return, better average drawdown, and unchanged worst return.
- `PortfolioStrategy` adds `primary_assist` mode. The first enabled allocation is the primary strategy. Auxiliary strategies cannot open trades on their own, can veto primary buy signals when opposite auxiliary weight is above `0.15`, and can boost aligned primary buy volume by `8%`.
- `chan_offensive_fusion_stack` now uses `primary_assist` with `ChanVolumeFusionStrategy` as the primary strategy plus Chan structure, volume momentum, MACD trend, and ATR breakout as auxiliary confirmation.

## Verification Commands

```bash
PYTHONPATH=src python -m pytest \
  tests/test_portfolio.py \
  tests/test_api_routes.py::test_bootstrap_returns_portfolio_presets_for_strategy_combinations \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_holds_weak_volume_above_continuation_trend \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_reduces_weak_volume_after_continuation_trend_break \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_severe_weak_momentum_reduces_before_trend_break \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_chan_sell_ignores_continuation_hold \
  tests/test_strategy_registry.py::test_chan_volume_fusion_strategy_is_registered_with_guidance \
  -q
```

Result: `14 passed in 0.61s`.

```bash
npm test -- --run
```

Result: `18 passed`, `90 passed`.

```bash
npm run build
```

Result: TypeScript and Vite build passed.

```bash
PYTHONPATH=src python -m pytest
```

Result: `185 passed in 3.61s`.

```bash
./scripts/run_app.sh
```

Result: FastAPI served `http://127.0.0.1:8000`; Vite served `http://127.0.0.1:5173`.

Headless Chrome acceptance captured the React Portfolio Lab after applying `缠论进攻融合组合`; the text check confirmed both `当前模式：主策略辅助确认` and `缠论进攻融合组合`.

- `docs/qa/screenshots/2026-06-19-chan-offensive-fusion-combo_desktop_1440.png`
- `docs/qa/screenshots/2026-06-19-chan-offensive-fusion-combo_mobile_390.png`

## Fixed Six-Stock Benchmark

Execution used persisted local qfq fixtures under `data/market/a_share/{exchange}/{code}/`, requested range `20230619` to `20260619`, actual fixture range ending `2026-06-18`, and `BacktestConfig(initial_cash=100000, commission_rate=0.0003, slippage=0.01, max_order_cash=50000)`.

### Default ChanVolumeFusionStrategy

| Symbol | Name | Rows | Date range | Final equity | Return | Annual return | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981/SSE` | 中芯国际 | 720 | 2023-06-19 to 2026-06-18 | 101175.31 | 1.1753% | 0.4098% | -4.3745% | 82 | 47.5000% | 1.5354 | 26.3889% |
| `000858/SZSE` | 五粮液 | 726 | 2023-06-19 to 2026-06-18 | 101257.52 | 1.2575% | 0.4347% | -1.3047% | 7 | 33.3333% | 2.4045 | 2.8926% |
| `601318/SSE` | 中国平安 | 726 | 2023-06-19 to 2026-06-18 | 99564.03 | -0.4360% | -0.1515% | -1.5681% | 72 | 45.7143% | 0.8906 | 62.6722% |
| `600901/SSE` | 江苏金租 | 726 | 2023-06-19 to 2026-06-18 | 99870.33 | -0.1297% | -0.0450% | -0.2340% | 66 | 30.3030% | 0.5451 | 72.7273% |
| `600989/SSE` | 宝丰能源 | 726 | 2023-06-19 to 2026-06-18 | 100490.33 | 0.4903% | 0.1699% | -0.6502% | 26 | 50.0000% | 2.1004 | 65.0138% |
| `603986/SSE` | 兆易创新 | 726 | 2023-06-19 to 2026-06-18 | 114584.31 | 14.5843% | 4.8390% | -8.2670% | 129 | 41.9355% | 1.5751 | 62.2590% |

Summary: average return `2.8236%`, best return `14.5843%`, worst return `-0.4360%`, average max drawdown `-2.7331%`, total trades `382`.

### chan_offensive_fusion_stack

| Symbol | Name | Rows | Date range | Final equity | Return | Annual return | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981/SSE` | 中芯国际 | 720 | 2023-06-19 to 2026-06-18 | 103942.42 | 3.9424% | 1.3625% | -6.4012% | 81 | 46.1538% | 1.5272 | 47.6389% |
| `000858/SZSE` | 五粮液 | 726 | 2023-06-19 to 2026-06-18 | 99938.10 | -0.0619% | -0.0215% | -2.8812% | 7 | 33.3333% | 2.4015 | 55.6474% |
| `601318/SSE` | 中国平安 | 726 | 2023-06-19 to 2026-06-18 | 99993.08 | -0.0069% | -0.0024% | -1.0918% | 58 | 44.4444% | 0.9536 | 73.1405% |
| `600901/SSE` | 江苏金租 | 726 | 2023-06-19 to 2026-06-18 | 100004.46 | 0.0045% | 0.0015% | -0.2197% | 55 | 34.6154% | 0.6445 | 64.7383% |
| `600989/SSE` | 宝丰能源 | 726 | 2023-06-19 to 2026-06-18 | 100653.95 | 0.6539% | 0.2265% | -1.6207% | 26 | 50.0000% | 2.0985 | 73.8292% |
| `603986/SSE` | 兆易创新 | 726 | 2023-06-19 to 2026-06-18 | 119719.13 | 19.7191% | 6.4464% | -9.2076% | 121 | 45.4545% | 1.6837 | 62.6722% |

Summary: average return `4.0419%`, best return `19.7191%`, worst return `-0.0619%`, average max drawdown `-3.5704%`, total trades `348`.

### Comparison

| Metric | Default ChanVolumeFusionStrategy | chan_offensive_fusion_stack | Change |
|---|---:|---:|---:|
| Average return | 2.8236% | 4.0419% | +1.2183 pp |
| Best return | 14.5843% | 19.7191% | +5.1348 pp |
| Worst return | -0.4360% | -0.0619% | +0.3741 pp |
| Average max drawdown | -2.7331% | -3.5704% | -0.8373 pp |
| Total trades | 382 | 348 | -34 |

Interpretation:

- The final combo meets the requested upside and downside return goal on the fixed six-stock benchmark: average return, best return, and worst return all improve.
- It is not simply more conservative: exposure and upside rise materially on 中芯国际 and 兆易创新.
- The tradeoff is drawdown: average max drawdown worsens from `-2.7331%` to `-3.5704%`, mostly because aligned auxiliary signals increase exposure in stronger trends.
- The primary-assist mode reduced noise from helper-only trades compared with the earlier weighted-vote candidate, which had a worse fixed-six worst return.

## STAR Market Supplemental Backtest

The supplemental run used the same 20 persisted SSE STAR-market fixtures as the prior Chan-volume benchmark, excluding `688981` because it is already part of the fixed six-stock benchmark.

| Symbol | Name | Rows | Date range | Final equity | Return | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `688008/SSE` | 澜起科技 | 726 | 2023-06-19 to 2026-06-18 | 127689.77 | 27.6898% | -9.1831% | 37 | 27.7778% | 1.6496 | 86.6391% |
| `688012/SSE` | 中微公司 | 717 | 2023-06-19 to 2026-06-18 | 107465.42 | 7.4654% | -9.3115% | 84 | 40.0000% | 2.0294 | 78.9400% |
| `688017/SSE` | 绿的谐波 | 726 | 2023-06-19 to 2026-06-18 | 117366.66 | 17.3667% | -15.7094% | 79 | 40.5405% | 1.6734 | 79.3388% |
| `688041/SSE` | 海光信息 | 716 | 2023-06-19 to 2026-06-18 | 127259.58 | 27.2596% | -12.5032% | 77 | 44.4444% | 2.6664 | 55.0279% |
| `688048/SSE` | 长光华芯 | 726 | 2023-06-19 to 2026-06-18 | 139131.04 | 39.1310% | -9.6703% | 63 | 40.7407% | 3.8622 | 84.0220% |
| `688072/SSE` | 拓荆科技 | 726 | 2023-06-19 to 2026-06-18 | 104342.51 | 4.3425% | -13.6819% | 97 | 36.3636% | 0.5142 | 66.3912% |
| `688110/SSE` | 东芯股份 | 723 | 2023-06-19 to 2026-06-18 | 103650.54 | 3.6505% | -3.8728% | 36 | 56.2500% | 13.4705 | 73.1674% |
| `688126/SSE` | 沪硅产业 | 716 | 2023-06-19 to 2026-06-18 | 100594.88 | 0.5949% | -0.7297% | 20 | 25.0000% | 1.5838 | 55.0279% |
| `688146/SSE` | 中船特气 | 726 | 2023-06-19 to 2026-06-18 | 128663.94 | 28.6639% | -4.0614% | 25 | 36.3636% | 6.8642 | 52.6171% |
| `688183/SSE` | 生益电子 | 726 | 2023-06-19 to 2026-06-18 | 125128.83 | 25.1288% | -3.6070% | 47 | 52.3810% | 3.7243 | 47.7961% |
| `688256/SSE` | 寒武纪 | 726 | 2023-06-19 to 2026-06-18 | 121051.70 | 21.0517% | -4.0898% | 40 | 50.0000% | 2.9601 | 38.1543% |
| `688313/SSE` | 仕佳光子 | 717 | 2023-06-19 to 2026-06-18 | 107108.87 | 7.1089% | -2.8539% | 34 | 68.7500% | 24.3181 | 49.0934% |
| `688347/SSE` | 华虹宏力 | 683 | 2023-08-07 to 2026-06-18 | 122864.25 | 22.8643% | -6.4987% | 32 | 50.0000% | 1.7321 | 62.5183% |
| `688498/SSE` | 源杰科技 | 726 | 2023-06-19 to 2026-06-18 | 163590.17 | 63.5902% | -10.2581% | 42 | 45.0000% | 1.7385 | 74.3802% |
| `688521/SSE` | 芯原股份 | 716 | 2023-06-19 to 2026-06-18 | 107669.70 | 7.6697% | -7.8270% | 59 | 40.7407% | 1.1723 | 59.2179% |
| `688525/SSE` | 佰维存储 | 726 | 2023-06-19 to 2026-06-18 | 131324.77 | 31.3248% | -8.8178% | 43 | 42.1053% | 2.3864 | 68.3196% |
| `688627/SSE` | 精智达 | 707 | 2023-07-18 to 2026-06-18 | 142958.26 | 42.9583% | -9.2525% | 74 | 56.2500% | 3.4707 | 53.3239% |
| `688702/SSE` | 盛科通信 | 665 | 2023-09-14 to 2026-06-18 | 159867.79 | 59.8678% | -12.0533% | 55 | 56.0000% | 2.3621 | 77.4436% |
| `688766/SSE` | 普冉股份 | 716 | 2023-06-19 to 2026-06-18 | 164691.89 | 64.6919% | -9.5052% | 29 | 35.7143% | 1.7257 | 85.8939% |
| `688820/SSE` | 盛合晶微 | 40 | 2026-04-21 to 2026-06-18 | 100000.00 | 0.0000% | 0.0000% | 0 | n/a | n/a | 0.0000% |

Summary: `20` stocks, `19` positive, average return `25.1210%`, median return `23.9965%`, average max drawdown `-7.6743%`, total trades `973`, best `688766` at `64.6919%`, worst `688820` at `0.0000%`.

Interpretation:

- The offensive combo remains strongest on high-volatility STAR fixtures, especially semiconductor and computing names.
- `688820` has only 40 bars in the local fixture and no trades, so its `0.0000%` return is a data-window limitation rather than an active strategy call.
- STAR upside improved sharply versus the prior Chan-volume fusion supplemental baseline, but with higher exposure and larger average drawdown.

## Decision

Keep `chan_offensive_fusion_stack` as an offensive Chan-primary preset, not as the safest default portfolio. For lower drawdown requirements, use standalone `ChanVolumeFusionStrategy` or a future preset with a smaller auxiliary buy boost.
