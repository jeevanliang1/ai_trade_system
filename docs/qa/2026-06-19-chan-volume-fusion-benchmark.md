# Chan Volume Fusion Strategy Benchmark

Date: 2026-06-19

## Scope

This QA record covers adding `ChanVolumeFusionStrategy`, a built-in strategy that keeps Chan structure as the primary signal source and uses volume-price momentum as helper evidence:

- T2 second-buy entries require strong volume-price confirmation by default.
- T3 and Chan confirmation buys can boost from the base high-confidence target to `max_units` when volume-price momentum is strong.
- If no Chan sell signal appears and volume-price momentum turns weak, the strategy reduces one position unit by default.
- Chan sell signals keep priority over weak-volume exits.

## Verification Commands

```bash
PYTHONPATH=src python -m pytest \
  tests/test_strategy_registry.py::test_chan_volume_fusion_strategy_is_registered_with_guidance \
  tests/test_builtin_popular_strategies.py::test_registry_includes_popular_builtin_strategies \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_blocks_low_confidence_without_strong_volume \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_boosts_high_confidence_units_with_strong_volume \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_weak_volume_reduces_or_exits \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_requires_strong_volume_for_t2_buy \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_boosts_t3_buy_on_strong_volume \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_weak_volume_reduces_position_without_chan_sell \
  tests/test_builtin_popular_strategies.py::test_chan_volume_fusion_prioritizes_chan_sell_before_weak_volume_reduce \
  tests/test_api_routes.py::test_strategies_route_exposes_enum_parameter_options \
  -q
```

Result: `10 passed in 0.62s`.

```bash
PYTHONPATH=src python -m pytest tests/test_builtin_popular_strategies.py tests/test_strategy_registry.py tests/test_api_routes.py -q
```

Result: `97 passed in 2.52s`.

```bash
PYTHONPATH=src python -m pytest
```

Result: `177 passed in 4.70s`.

## Fixed Six-Stock Benchmark

Execution used persisted local qfq fixtures under `data/market/a_share/{exchange}/{code}/`, `BacktestConfig(initial_cash=100000)`, and default strategy parameters.

### Baseline: ChanStructureStrategy

| Symbol | Name | Rows | Date range | Final equity | Return | Benchmark | Excess | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981/SSE` | 中芯国际 | 720 | 2023-06-19 to 2026-06-18 | 104780.84 | 4.7808% | 155.5394% | -150.7586% | -4.6154% | 68 | 45.4545% | 1.3370 | 5.9397% |
| `000858/SZSE` | 五粮液 | 726 | 2023-06-19 to 2026-06-18 | 97272.04 | -2.7280% | -52.8208% | 50.0928% | -4.4337% | 56 | 25.0000% | 0.6017 | 3.2318% |
| `601318/SSE` | 中国平安 | 726 | 2023-06-19 to 2026-06-18 | 98023.55 | -1.9764% | 23.8525% | -25.8289% | -2.8425% | 68 | 38.2353% | 0.6924 | 2.9661% |
| `600901/SSE` | 江苏金租 | 726 | 2023-06-19 to 2026-06-18 | 99907.29 | -0.0927% | 85.0153% | -85.1080% | -0.3171% | 79 | 35.8974% | 1.1002 | 0.3736% |
| `600989/SSE` | 宝丰能源 | 726 | 2023-06-19 to 2026-06-18 | 100892.83 | 0.8928% | 87.6963% | -86.8035% | -1.0470% | 50 | 50.0000% | 1.9958 | 0.7983% |
| `603986/SSE` | 兆易创新 | 726 | 2023-06-19 to 2026-06-18 | 157302.04 | 57.3020% | 459.7579% | -402.4559% | -6.7301% | 105 | 51.0204% | 3.1668 | 11.1927% |

Summary: average return `9.6964%`, worst return `-2.7280%`, average max drawdown `-3.3310%`, total trades `426`.

### New Strategy: ChanVolumeFusionStrategy

| Symbol | Name | Rows | Date range | Final equity | Return | Benchmark | Excess | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `688981/SSE` | 中芯国际 | 720 | 2023-06-19 to 2026-06-18 | 103571.41 | 3.5714% | 155.5394% | -151.9680% | -3.4593% | 83 | 55.0000% | 1.8085 | 4.1304% |
| `000858/SZSE` | 五粮液 | 726 | 2023-06-19 to 2026-06-18 | 101257.52 | 1.2575% | -52.8208% | 54.0783% | -1.3047% | 7 | 33.3333% | 2.4045 | 0.5368% |
| `601318/SSE` | 中国平安 | 726 | 2023-06-19 to 2026-06-18 | 99702.99 | -0.2970% | 23.8525% | -24.1495% | -1.4708% | 72 | 45.7143% | 0.9724 | 1.2263% |
| `600901/SSE` | 江苏金租 | 726 | 2023-06-19 to 2026-06-18 | 99887.82 | -0.1122% | 85.0153% | -85.1275% | -0.2269% | 70 | 31.4286% | 0.5831 | 0.1809% |
| `600989/SSE` | 宝丰能源 | 726 | 2023-06-19 to 2026-06-18 | 100490.33 | 0.4903% | 87.6963% | -87.2060% | -0.6502% | 26 | 50.0000% | 2.1004 | 0.4252% |
| `603986/SSE` | 兆易创新 | 726 | 2023-06-19 to 2026-06-18 | 114138.08 | 14.1381% | 459.7579% | -445.6198% | -8.9007% | 135 | 43.0769% | 1.5292 | 8.9167% |

Summary: average return `3.1747%`, worst return `-0.2970%`, average max drawdown `-2.6688%`, total trades `393`.

Interpretation:

- The fusion strategy improves the fixed-six worst return from `-2.7280%` to `-0.2970%`.
- Average max drawdown improves from `-3.3310%` to `-2.6688%`.
- It gives up substantial upside on high-trend names such as 兆易创新 because the volume gate and weak-volume reduction reduce exposure.
- This is a more conservative Chan-primary combination, not a return-maximizing tune.

## STAR Market Supplemental Backtest

The supplemental run used 20 persisted SSE STAR-market fixtures excluding `688981`, because 中芯国际 is already included in the fixed six-stock benchmark.

| Symbol | Name | Rows | Date range | Final equity | Return | Benchmark | Excess | Max DD | Trades | Win rate | PF | Exposure |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `688008/SSE` | 澜起科技 | 726 | 2023-06-19 to 2026-06-18 | 105797.56 | 5.7976% | 342.9673% | -337.1697% | -5.8566% | 37 | 27.7778% | 1.6500 | 2.5473% |
| `688012/SSE` | 中微公司 | 717 | 2023-06-19 to 2026-06-18 | 100815.19 | 0.8152% | 219.9431% | -219.1279% | -9.1325% | 94 | 39.0244% | 1.6897 | 5.7432% |
| `688017/SSE` | 绿的谐波 | 726 | 2023-06-19 to 2026-06-18 | 106494.53 | 6.4945% | 161.7126% | -155.2181% | -15.3540% | 89 | 40.4762% | 1.6210 | 5.3861% |
| `688041/SSE` | 海光信息 | 716 | 2023-06-19 to 2026-06-18 | 117214.23 | 17.2142% | 311.8533% | -294.6391% | -9.5632% | 87 | 45.2381% | 2.4062 | 7.1938% |
| `688048/SSE` | 长光华芯 | 726 | 2023-06-19 to 2026-06-18 | 133969.61 | 33.9696% | 234.2764% | -200.3068% | -7.1893% | 80 | 48.6486% | 3.8013 | 5.2913% |
| `688072/SSE` | 拓荆科技 | 726 | 2023-06-19 to 2026-06-18 | 84999.80 | -15.0002% | 285.5650% | -300.5652% | -17.9099% | 121 | 36.2069% | 0.5685 | 7.6725% |
| `688110/SSE` | 东芯股份 | 723 | 2023-06-19 to 2026-06-18 | 103334.88 | 3.3349% | 310.5823% | -307.2474% | -3.3666% | 44 | 52.3810% | 12.2985 | 1.4076% |
| `688126/SSE` | 沪硅产业 | 716 | 2023-06-19 to 2026-06-18 | 100273.34 | 0.2733% | 48.6611% | -48.3878% | -0.7213% | 29 | 30.7692% | 1.9470 | 0.3393% |
| `688146/SSE` | 中船特气 | 726 | 2023-06-19 to 2026-06-18 | 125703.04 | 25.7030% | 736.3971% | -710.6941% | -3.8467% | 26 | 41.6667% | 7.1520 | 1.0257% |
| `688183/SSE` | 生益电子 | 726 | 2023-06-19 to 2026-06-18 | 118796.11 | 18.7961% | 1061.9128% | -1043.1167% | -2.7897% | 50 | 47.8261% | 3.0517 | 2.1141% |
| `688256/SSE` | 寒武纪 | 726 | 2023-06-19 to 2026-06-18 | 111182.30 | 11.1823% | 845.3531% | -834.1708% | -5.3419% | 43 | 52.3810% | 2.5555 | 4.7849% |
| `688313/SSE` | 仕佳光子 | 717 | 2023-06-19 to 2026-06-18 | 105936.88 | 5.9369% | 756.2225% | -750.2856% | -2.5932% | 41 | 60.0000% | 16.4972 | 0.8967% |
| `688347/SSE` | 华虹宏力 | 683 | 2023-08-07 to 2026-06-18 | 103397.26 | 3.3973% | 425.0614% | -421.6641% | -5.4684% | 32 | 50.0000% | 1.6913 | 1.7468% |
| `688498/SSE` | 源杰科技 | 726 | 2023-06-19 to 2026-06-18 | 104407.71 | 4.4077% | 637.4554% | -633.0477% | -5.5985% | 40 | 45.0000% | 1.7398 | 2.4219% |
| `688521/SSE` | 芯原股份 | 716 | 2023-06-19 to 2026-06-18 | 102250.93 | 2.2509% | 212.0018% | -209.7509% | -7.3842% | 63 | 46.6667% | 1.2284 | 3.8516% |
| `688525/SSE` | 佰维存储 | 726 | 2023-06-19 to 2026-06-18 | 111507.05 | 11.5070% | 286.9739% | -275.4669% | -5.8603% | 47 | 40.9091% | 2.1417 | 3.8427% |
| `688627/SSE` | 精智达 | 707 | 2023-07-18 to 2026-06-18 | 133668.66 | 33.6687% | 647.7870% | -614.1183% | -10.5229% | 83 | 50.0000% | 2.2890 | 8.3882% |
| `688702/SSE` | 盛科通信 | 665 | 2023-09-14 to 2026-06-18 | 129394.72 | 29.3947% | 439.2000% | -409.8053% | -8.6182% | 56 | 57.6923% | 2.5588 | 4.6171% |
| `688766/SSE` | 普冉股份 | 716 | 2023-06-19 to 2026-06-18 | 121601.49 | 21.6015% | 860.1302% | -838.5287% | -6.4333% | 29 | 35.7143% | 1.8307 | 2.6538% |
| `688820/SSE` | 盛合晶微 | 40 | 2026-04-21 to 2026-06-18 | 100000.00 | 0.0000% | 142.1396% | -142.1396% | 0.0000% | 0 | n/a | n/a | 0.0000% |

Summary: `20` stocks, `18` positive, average return `11.0373%`, median return `6.4945%`, average max drawdown `-6.6775%`, total trades `1091`, best `688048` at `33.9696%`, worst `688072` at `-15.0002%`.

Interpretation:

- The fusion rule remains more suitable for high-volatility STAR fixtures than for low-volatility financial/energy names.
- It still underperforms buy-and-hold on explosive STAR trends because the current design deliberately reduces exposure when volume-price momentum weakens.
- The next useful tuning dimension is not more signals; it is regime-specific position caps or a stronger trend-continuation hold rule for STAR names.

## Browser Acceptance

Command:

```bash
./scripts/run_app.sh
node scripts/capture_app_screenshots.mjs --url http://127.0.0.1:5173 --out-dir docs/qa/screenshots --prefix 2026-06-19-chan-volume-fusion
```

Screenshots:

- `docs/qa/screenshots/2026-06-19-chan-volume-fusion_desktop_1440.png`
- `docs/qa/screenshots/2026-06-19-chan-volume-fusion_mobile_390.png`

Runtime API check:

```bash
curl -s http://127.0.0.1:8000/api/strategies | python -c 'import json, sys; payload=json.load(sys.stdin); item=next(strategy for strategy in payload if strategy["class_name"] == "ChanVolumeFusionStrategy"); params={param["name"]: param for param in item["parameters"]}; print(item["display_name"]); print(item["description"]); print(params["weak_volume_exit_mode"]["options"])'
```

Output:

```text
缠论量价融合
以缠论结构为主策略，使用量价动量确认低确定性买点、增强三买等高确定性买点，并在量价转弱时减仓或退出。
['reduce', 'exit', 'ignore']
```
