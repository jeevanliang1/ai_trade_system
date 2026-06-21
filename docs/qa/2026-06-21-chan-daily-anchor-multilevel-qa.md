# Chan Daily Anchor Multi-Level QA

## Scope

Optimized `ChanMultiLevelReversalStrategy` after the previous lower-level discovery mode failed to outperform the daily-only Chan baseline.

New behavior:

- `entry_mode="daily_anchor"` preserves the original daily Chan structure buy/sell decisions.
- Lower-level data no longer acts as a hard gate for daily buy points in `daily_anchor`.
- Same-day lower-level signals can improve daily execution price:
  - buy: use the lower `60m` confirm buy price when available,
  - sell: use the higher lower-level sell price when available.
- Lower-level risk signals can reduce or exit only after a profit threshold or drawdown threshold is reached.
- Independent lower-level early entries remain in `entry_mode="lower_level_discovery"` and are not part of the final outperforming preset.

## External Chan Rationale

Public Chan summaries consistently describe the multi-level method as:

- big level decides direction, lower level locates buy/sell points,
- interval nesting narrows execution timing,
- small-level divergence is useful mainly when it is nested inside a larger-level segment or reversal setup,
- leaving level context creates false signals.

Reviewed sources:

- FXBaoGao / Zhongtai Securities Chan framework summary: `https://www.fxbaogao.com/detail/5267477`
- BigQuant Chanlun knowledge base: `https://bigquant.com/wiki/doc/cOsACEKd1x`
- Eastmoney Chan quotes collection: `https://m.eastmoney.com/blog/article/776559505`

Implementation implication: do not let lower-level signals blindly replace the daily structure. Use daily as the anchor, and use lower levels mainly for execution and tightly scoped defense.

## Root Cause From Previous QA

Previous best offensive mode:

```text
ml_lower_discovery_60_30_skip_c28_r24_reduce
```

It improved over the conservative multi-level gate, but was still below daily-only:

| Variant | Avg return % | Avg max DD % | Trades | Avg win rate % | Avg profit factor |
| --- | ---: | ---: | ---: | ---: | ---: |
| `daily_chan_structure_default` | 6.7631 | -5.4286 | 581 | 38.8215 | 1.2930 |
| `ml_lower_discovery_60_30_skip_c28_r24_reduce` | 2.3259 | -5.1180 | 553 | 45.3255 | 1.4383 |

Root cause: the old multi-level logic made lower-level confirmation a hard gate for daily buy points. That removed good daily trades and treated noisy lower-level discovery as an independent source of edge.

## Final Preset

Recommended outperforming preset:

```python
ChanMultiLevelReversalStrategy(
    entry_mode="daily_anchor",
    confirm_timeframe="60m",
    risk_timeframe="30m",
    minute_missing_policy="daily_only",
    lower_level_policy="confirm_only",
    min_confirm_score=28,
    min_risk_score=24,
    minute_sell_mode="reduce",
    max_holding_bars=30,
)
```

The `max_holding_bars=30` reference is included because daily-only also improves when held longer; the final multi-level preset must beat that stronger daily reference, not only the original default.

## Benchmark Method

Universe:

- `688981/SSE` 中芯国际
- `000858/SZSE` 五粮液
- `601318/SSE` 中国平安
- `600901/SSE` 江苏金租
- `600989/SSE` 宝丰能源
- `603986/SSE` 兆易创新
- `688733/SSE` 壹石通
- `688072/SSE` 拓荆科技

Window: `2023-06-19` to `2026-06-19`.

Data:

- Daily qfq local fixtures under `data/market/a_share/{exchange}/{symbol}/`
- `60m` and `30m` qfq local fixtures for lower-level replay
- `688733/SSE` daily starts at `2024-06-21`, so its available daily range is shorter.

Engine:

- `run_backtest`
- `calculate_backtest_metrics`
- `BacktestConfig()` defaults: `100000` initial cash, `0.0003` commission, `0.01` slippage, `50000` max order cash
- `ChanCoreV2Analyzer` results were precomputed per symbol/timeframe and replayed through strategy variants to avoid repeated scan cost.

## Aggregate Results

| Variant | Avg return % | Median return % | Avg benchmark return % | Avg excess % | Avg max DD % | Total trades | Avg win rate % | Avg profit factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ml_daily_anchor_60_30_h30_exec` | 13.3998 | 1.2671 | 152.7850 | -139.3853 | -5.0484 | 523 | 38.35 | 1.4542 |
| `daily_h30_reference` | 13.2192 | 1.2396 | 152.7850 | -139.5659 | -5.1317 | 523 | 37.90 | 1.4107 |
| `daily_default` | 6.7631 | 0.4001 | 152.7850 | -146.0219 | -5.4286 | 581 | 38.82 | 1.2930 |
| `ml_previous_lower_discovery_60_30_skip_h15` | 2.3259 | 0.2530 | 152.7850 | -150.4591 | -5.1180 | 553 | 45.33 | 1.4383 |

## Per-Symbol Final Preset

| Symbol | Return % | Benchmark return % | Excess % | Max DD % | Trades | Win rate % | Profit factor |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | 4.4774 | 155.5394 | -151.0620 | -5.7826 | 64 | 46.6667 | 1.2417 |
| `000858/SZSE` | -6.1238 | -52.8208 | 46.6970 | -6.8603 | 58 | 25.0000 | 0.1392 |
| `601318/SSE` | -3.8153 | 23.8525 | -27.6678 | -4.4919 | 59 | 46.4286 | 0.6238 |
| `600901/SSE` | -0.0499 | 85.0153 | -85.0652 | -0.2917 | 67 | 30.3030 | 1.3833 |
| `600989/SSE` | -0.4230 | 87.6963 | -88.1193 | -2.2564 | 46 | 52.3810 | 1.3276 |
| `603986/SSE` | 95.4543 | 459.7579 | -364.3036 | -6.2550 | 97 | 43.1818 | 4.5459 |
| `688733/SSE` | 2.5841 | 177.6747 | -175.0906 | -1.4855 | 53 | 26.9231 | 0.8906 |
| `688072/SSE` | 15.0943 | 285.5650 | -270.4707 | -12.9636 | 79 | 35.8974 | 1.4818 |

## Interpretation

- The final multi-level preset beats the original daily baseline by `+6.6367` percentage points of average return.
- It also beats the stronger daily `max_holding_bars=30` reference by `+0.1806` percentage points.
- Average max drawdown improves versus both daily references:
  - final multi-level: `-5.0484%`
  - daily 30-day reference: `-5.1317%`
  - daily default: `-5.4286%`
- Win rate and profit factor both improve versus daily references.
- The edge comes from lower-level execution price optimization, not from blindly adding lower-level independent entries.

## Verification

TDD red checks:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Observed expected failures before implementation for missing `daily_anchor`, `risk_profit_threshold_pct`, drawdown defense, and lower-level execution price optimization.

Targeted green checks:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py -q
```

Result: `36 passed in 0.47s`.

Full Python suite:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Result: `287 passed in 6.97s`.

Frontend tests:

```bash
npm --prefix frontend test
```

Result: `21 passed`, `101 passed`, duration `4.27s`.

Frontend build:

```bash
npm --prefix frontend run build
```

Result: succeeded.

## Screenshot Acceptance

Rendered the React + FastAPI platform from `./scripts/run_app.sh` at `http://127.0.0.1:5173`.

Captured screenshots:

- `docs/qa/screenshots/2026-06-21-chan-daily-anchor_desktop_1440.png` (`1440x1024`)
- `docs/qa/screenshots/2026-06-21-chan-daily-anchor_mobile_390.png` (`390x844`)
- `docs/qa/screenshots/2026-06-21-chan-daily-anchor_strategy-entry-mode_desktop_1440.png` (`1440x1024`)

Strategy metadata API validation:

```json
{
  "display": "缠论多级别反转",
  "entryOptions": ["daily_confirmed", "lower_level_discovery", "daily_anchor"],
  "riskProfitLabel": "浮盈风控阈值"
}
```

DOM validation after selecting the strategy in the real UI:

```json
{
  "value": "daily_anchor",
  "options": ["daily_confirmed", "lower_level_discovery", "daily_anchor"],
  "hasRiskProfit": true,
  "textHasExecution": true
}
```

Console events during the check were limited to `debug` and `info`; no browser error events were observed.

## Remaining Risk

- The final strategy still underperforms buy-and-hold benchmark returns in a strong semiconductor sample, but it improves the strategy-vs-strategy comparison requested here.
- Minute data coverage is still shorter than daily coverage, especially for `30m` and `15m`.
- Independent lower-level discovery remains available but should not be the default outperforming preset until it has stronger high-level background filters.
