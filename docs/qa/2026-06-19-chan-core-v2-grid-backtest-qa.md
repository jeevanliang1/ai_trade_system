# Chan Core V2 Grid Backtest QA

## Scope

This record covers a detailed grid backtest for the current Chan Core V2 integration using the fixed persisted qfq fixtures:

- 中芯国际 `688981/SSE`: `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv`
- 五粮液 `000858/SZSE`: `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv`

This is a strategy-consumption grid for `ChanStructureStrategy`. Chan Core V2 itself currently provides structure/lifecycle/cache metadata and does not introduce a new default trading signal family.

## Method

Default structure parameters for the main grid:

- `min_bars=60`
- `lookback=160`
- `min_stroke_bars=5`
- `min_rebound_pct=0.03`
- `trade_size=100`
- Backtest defaults: initial cash `100000`, commission `0.0003`, slippage `0.01`, max order cash `50000`

Main grid dimensions:

- `min_signal_score`: `24`, `26`, `28`, `30`, `32`, `36`, `40`
- `signal_mode`: `all`, `confirmation`, `structure`
- `max_holding_bars`: `0`, `5`, `10`, `15`, `20`, `30`
- `watch_confirm_bars`: `0`, `10`, `20`, `40`
- `allowed_point_types`: `all`, `first-buy,first-sell`, `second-buy,second-sell`, `third-buy,third-sell`, `first-buy,first-sell,third-buy,third-sell`, `second-buy,second-sell,third-buy,third-sell`
- `allowed_levels`: `all`, `segment`, `stroke`, `fractal`

Execution:

- Main grid: `12096` parameter combinations.
- Signal generation was precomputed per bar with current Chan Core V2 code, then strategy state transitions were simulated against same-day signals.
- Key configurations were validated again with the real `ChanStructureStrategy` object.
- Full generated main-grid CSV: `/tmp/chan_core_v2_grid_results.csv`
- Summary JSON: `/tmp/chan_core_v2_grid_summary.json`
- Elapsed time: `108.8s`

## Coverage Summary

| Metric | Count |
| --- | ---: |
| Total main-grid configs | 12096 |
| Both fixtures positive with trades | 2352 |
| Zero-trade configs | 7344 |
| Configs with at least one fixture negative | 2400 |

## Current Default

| Params | Sum Return | Worst Return | Worst Drawdown | Trades | 688981 Return | 000858 Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `score=28, mode=all, hold=15, watch=20, points=third-buy,third-sell, levels=all` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |

The selected default remains the best balanced result under the fixed structural defaults. For this selected third-buy/third-sell profile, `min_signal_score` values from `24` through `40` produced the same trades.

## Highest Sum Return

The highest sum-return rows are not balanced because 五粮液 stays negative.

| Rank | Params | Sum Return | Worst Return | Worst Drawdown | Trades | 688981 Return | 000858 Return |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `score=24, mode=all, hold=0, watch=0, points=second-buy,second-sell, levels=stroke` | 3.9188% | -0.4795% | -4.6338% | 5 | 4.3983% | -0.4795% |
| 2 | `score=24, mode=all, hold=0, watch=0, points=third-buy,third-sell, levels=all` | 3.9014% | -0.8148% | -4.6198% | 3 | 4.7162% | -0.8148% |
| 3 | `score=24, mode=all, hold=0, watch=0, points=all, levels=stroke` | 3.8083% | -0.4795% | -4.6387% | 7 | 4.2878% | -0.4795% |
| 4 | `score=24, mode=all, hold=15, watch=0, points=third-buy,third-sell, levels=all` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |
| 5 | `score=24, mode=all, hold=10, watch=0, points=third-buy,third-sell, levels=all` | 2.0215% | 0.5488% | -1.5597% | 18 | 1.4727% | 0.5488% |

Interpretation:

- The raw sum-return winner is a second-buy/second-sell stroke-level profile with no max holding exit.
- It is not a good default candidate because 五粮液 is negative and worst drawdown is around `-4.63%`.

## Best Balanced Positive Rows

Rows below require both fixed fixtures to be positive and have trades.

| Rank | Params | Sum Return | Worst Return | Worst Drawdown | Trades | 688981 Return | 000858 Return |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `score=24, mode=all, hold=15, watch=0, points=third-buy,third-sell, levels=all` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |
| 2 | `score=24, mode=all, hold=10, watch=0, points=third-buy,third-sell, levels=all` | 2.0215% | 0.5488% | -1.5597% | 18 | 1.4727% | 0.5488% |
| 3 | `score=24, mode=all, hold=30, watch=0, points=third-buy,third-sell, levels=all` | 1.3607% | 0.4288% | -1.8093% | 10 | 0.9319% | 0.4288% |
| 4 | `score=24, mode=all, hold=20, watch=0, points=third-buy,third-sell, levels=all` | 1.1003% | 0.4786% | -1.5512% | 12 | 0.4786% | 0.6217% |
| 5 | `score=24, mode=all, hold=5, watch=0, points=all, levels=stroke` | 1.0324% | 0.2939% | -1.8356% | 40 | 0.2939% | 0.7385% |

The current default is equivalent to the first row except it keeps `score=28` and `watch=20`. Those values are more conservative/readable defaults and produced the same trades in this grid.

## Parameter Diagnostics

| Dimension | Finding |
| --- | --- |
| `allowed_point_types` | `third-buy,third-sell` is the only clean positive family in this fixture pair. `second-buy,second-sell` can lift 中芯国际 but made 五粮液 negative. `first-buy,first-sell` produced no trades here. |
| `allowed_levels` | `all` and `stroke` contain the useful signals. `segment` and `fractal` produced zero trades under this grid. |
| `max_holding_bars` | `15` is best balanced. `0` maximizes 中芯国际 but leaves 五粮液 negative. `10/20/30` stay positive but reduce sum return. |
| `watch_confirm_bars` | No material effect for the selected third-buy/third-sell profile, because trades are driven by T3-style structures rather than T1 watch confirmation. |
| `signal_mode` | `all`, `confirmation`, and `structure` contain duplicate top results because T3 is allowed in both confirmation and structure families. Keeping `all` remains simplest. |
| `min_signal_score` | Under `third-buy,third-sell`, scores `24` through `40` produced the same trades. Keeping `28` remains acceptable. |

## Structural Sensitivity

This smaller sweep used the current default trading params and varied structure parameters:

- `lookback`: `120`, `160`, `240`
- `min_stroke_bars`: `4`, `5`, `6`
- `min_rebound_pct`: `0.02`, `0.03`

Top structural results:

| Params | Sum Return | Worst Return | Worst Drawdown | Trades | 688981 Return | 000858 Return |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `lookback=120, min_stroke_bars=5, min_rebound_pct=0.02` | 3.1683% | 1.1706% | -1.4998% | 14 | 1.9977% | 1.1706% |
| `lookback=120, min_stroke_bars=5, min_rebound_pct=0.03` | 3.1683% | 1.1706% | -1.4998% | 14 | 1.9977% | 1.1706% |
| `lookback=160, min_stroke_bars=5, min_rebound_pct=0.02` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |
| `lookback=160, min_stroke_bars=5, min_rebound_pct=0.03` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |
| `lookback=240, min_stroke_bars=5, min_rebound_pct=0.02` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |
| `lookback=240, min_stroke_bars=5, min_rebound_pct=0.03` | 2.6844% | 1.1706% | -1.5070% | 14 | 1.5138% | 1.1706% |

`min_stroke_bars=6` produced zero trades in this sensitivity sweep. `lookback=120` improved 中芯国际 while leaving 五粮液 unchanged, and was validated with the real strategy object:

| Real Strategy Params | Symbol | Return | Benchmark | Excess | Max Drawdown | Trades | Win Rate | Profit Factor |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `lookback=120, min_stroke_bars=5, min_rebound_pct=0.02` | `688981/SSE` | 1.9977% | 155.5394% | -153.5417% | -1.4998% | 12 | 66.6667% | 2.3596 |
| `lookback=120, min_stroke_bars=5, min_rebound_pct=0.02` | `000858/SZSE` | 1.1706% | -52.8208% | 53.9914% | -0.7333% | 2 | 100.0000% | n/a |
| `lookback=120, min_stroke_bars=5, min_rebound_pct=0.03` | `688981/SSE` | 1.9977% | 155.5394% | -153.5417% | -1.4998% | 12 | 66.6667% | 2.3596 |
| `lookback=120, min_stroke_bars=5, min_rebound_pct=0.03` | `000858/SZSE` | 1.1706% | -52.8208% | 53.9914% | -0.7333% | 2 | 100.0000% | n/a |

## Real Strategy Validation

Representative accelerated-grid rows were rerun through the real `ChanStructureStrategy` object:

| Config | Symbol | Return | Max Drawdown | Trades | Result |
| --- | --- | ---: | ---: | ---: | --- |
| current default | `688981/SSE` | 1.5138% | -1.5070% | 12 | matched |
| current default | `000858/SZSE` | 1.1706% | -0.7333% | 2 | matched |
| top sum | `688981/SSE` | 4.3983% | -4.6338% | 3 | matched |
| top sum | `000858/SZSE` | -0.4795% | -4.4902% | 2 | matched |
| top balanced | `688981/SSE` | 1.5138% | -1.5070% | 12 | matched |
| top balanced | `000858/SZSE` | 1.1706% | -0.7333% | 2 | matched |

## Conclusion

For the current two-fixture benchmark, the existing balanced default remains justified:

```text
min_signal_score=28
signal_mode=all
allowed_point_types=third-buy,third-sell
allowed_levels=all
max_holding_bars=15
watch_confirm_bars=20
```

The only clear improvement candidate from this grid is structural rather than trade-filter based:

```text
lookback=120
min_stroke_bars=5
min_rebound_pct=0.02 or 0.03
```

That candidate improves 中芯国际 from `1.5138%` to `1.9977%` while leaving 五粮液 at `1.1706%`, but it should not become a default from only two fixtures. It should be tested across a broader local CSV universe before changing defaults.
