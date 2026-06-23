# Chan Multilevel Reversal QA

## Scope

Added and validated `ChanMultiLevelReversalStrategy`, a new built-in Chan strategy that keeps daily bars as the main backtest loop while using lower-level minute contexts:

- Daily structure remains the major trend and signal source.
- `30m` bars confirm daily buy and sell signals.
- `15m` bars only act as risk control for existing positions; they do not independently open positions.
- Existing `ChanStructureStrategy` and `ChanVolumeFusionStrategy` defaults are unchanged.

## Verification

Targeted tests:

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py -q
```

Result: `9 passed`.

```bash
python -m pytest tests/test_strategy_registry.py::test_chan_multilevel_reversal_strategy_is_registered_with_guidance -q
```

Result: `1 passed`.

```bash
python -m pytest tests/test_chan_multilevel_reversal_strategy.py tests/test_strategy_registry.py -q
```

Result: `22 passed`.

Full verification:

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Result: `273 passed`.

```bash
npm --prefix frontend test
```

Result: `21 passed`, `101 passed`.

```bash
npm --prefix frontend run build
```

Result: production build succeeded.

## Minute Fixture Preparation

Command:

```bash
python - <<'PY'
from ai_trade_system.data_manager import update_watchlist_data
from ai_trade_system.stock_catalog import StockInfo

stocks = [
    StockInfo("688981", "中芯国际", "SSE"),
    StockInfo("000858", "五粮液", "SZSE"),
    StockInfo("601318", "中国平安", "SSE"),
    StockInfo("600901", "江苏金租", "SSE"),
    StockInfo("600989", "宝丰能源", "SSE"),
    StockInfo("603986", "兆易创新", "SSE"),
]

for timeframe in ("30m", "15m"):
    update_watchlist_data(
        stocks,
        start_date="20230619",
        end_date="20260619",
        adjust="qfq",
        timeframe=timeframe,
        if_stale=False,
    )
PY
```

Result: all six stocks updated for both `30m` and `15m`.

AKShare public minute history did not cover the full three-year daily benchmark window. The strategy benchmark below therefore uses full daily qfq fixtures for the backtest loop, while minute confirmations are available only over the rows shown here.

| Symbol | Name | Daily fixture | Daily rows/range | 30m fixture | 30m rows/range | 15m fixture | 15m rows/range |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `688981/SSE` | 中芯国际 | `data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv` | 720: 2023-06-19 to 2026-06-18 | `data/market/a_share/SSE/688981/688981_SSE_30m_qfq_latest.csv` | 1970: 2025-06-05 14:30:00 to 2026-06-18 15:00:00 | `data/market/a_share/SSE/688981/688981_SSE_15m_qfq_latest.csv` | 1970: 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| `000858/SZSE` | 五粮液 | `data/market/a_share/SZSE/000858/000858_SZSE_daily_qfq_latest.csv` | 726: 2023-06-19 to 2026-06-18 | `data/market/a_share/SZSE/000858/000858_SZSE_30m_qfq_latest.csv` | 1970: 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | `data/market/a_share/SZSE/000858/000858_SZSE_15m_qfq_latest.csv` | 1970: 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| `601318/SSE` | 中国平安 | `data/market/a_share/SSE/601318/601318_SSE_daily_qfq_latest.csv` | 726: 2023-06-19 to 2026-06-18 | `data/market/a_share/SSE/601318/601318_SSE_30m_qfq_latest.csv` | 1970: 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | `data/market/a_share/SSE/601318/601318_SSE_15m_qfq_latest.csv` | 1970: 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| `600901/SSE` | 江苏金租 | `data/market/a_share/SSE/600901/600901_SSE_daily_qfq_latest.csv` | 726: 2023-06-19 to 2026-06-18 | `data/market/a_share/SSE/600901/600901_SSE_30m_qfq_latest.csv` | 1970: 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | `data/market/a_share/SSE/600901/600901_SSE_15m_qfq_latest.csv` | 1970: 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| `600989/SSE` | 宝丰能源 | `data/market/a_share/SSE/600989/600989_SSE_daily_qfq_latest.csv` | 726: 2023-06-19 to 2026-06-18 | `data/market/a_share/SSE/600989/600989_SSE_30m_qfq_latest.csv` | 1970: 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | `data/market/a_share/SSE/600989/600989_SSE_15m_qfq_latest.csv` | 1970: 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |
| `603986/SSE` | 兆易创新 | `data/market/a_share/SSE/603986/603986_SSE_daily_qfq_latest.csv` | 726: 2023-06-19 to 2026-06-18 | `data/market/a_share/SSE/603986/603986_SSE_30m_qfq_latest.csv` | 1970: 2025-06-13 14:30:00 to 2026-06-18 15:00:00 | `data/market/a_share/SSE/603986/603986_SSE_15m_qfq_latest.csv` | 1970: 2025-12-11 14:45:00 to 2026-06-18 15:00:00 |

## Benchmark Assumptions

Backtests used the shared `run_backtest` engine and `BacktestConfig()` defaults:

- Initial cash: `100000`
- Commission rate: `0.0003`
- Slippage: `0.01`
- Max order cash: `50000`
- Adjustment: `qfq`
- Daily benchmark window: `2023-06-19` to `2026-06-18`

Compared strategies:

- `ChanStructureStrategy`: existing daily Chan baseline.
- `ChanVolumeFusionStrategy`: existing daily Chan-volume fusion baseline.
- `ChanMultiLevelReversalStrategy daily_fallback`: new strategy with missing lower CSV paths and `minute_missing_policy="daily_only"`.
- `ChanMultiLevelReversalStrategy confirm_only`: daily signal gated by `30m` confirmation.
- `ChanMultiLevelReversalStrategy confirm_then_risk`: daily signal gated by `30m` confirmation plus `15m` risk reduction.

## Benchmark Results

| Symbol | Name | Strategy | Final equity | Strategy return % | Benchmark return % | Excess % | Max DD % | Trades | Win rate % | Profit factor |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `688981/SSE` | 中芯国际 | 日线缠论结构基线 | 104780.84 | 4.7808 | 155.5394 | -150.7586 | -4.6154 | 68 | 45.4545 | 1.3370 |
| `688981/SSE` | 中芯国际 | 日线缠论量价融合基线 | 101175.31 | 1.1753 | 155.5394 | -154.3641 | -4.3745 | 82 | 47.5000 | 1.5354 |
| `688981/SSE` | 中芯国际 | 新策略：无分钟数据日线 fallback | 104724.70 | 4.7247 | 155.5394 | -150.8147 | -4.2466 | 73 | 43.3333 | 1.2412 |
| `688981/SSE` | 中芯国际 | 新策略：日线 + 30m 确认 | 98411.55 | -1.5885 | 155.5394 | -157.1279 | -3.7125 | 18 | 28.5714 | 0.4515 |
| `688981/SSE` | 中芯国际 | 新策略：日线 + 30m 确认 + 15m 风控 | 98931.39 | -1.0686 | 155.5394 | -156.6080 | -3.7125 | 18 | 28.5714 | 0.6338 |
| `000858/SZSE` | 五粮液 | 日线缠论结构基线 | 97272.04 | -2.7280 | -52.8208 | 50.0928 | -4.4337 | 56 | 25.0000 | 0.6017 |
| `000858/SZSE` | 五粮液 | 日线缠论量价融合基线 | 101257.52 | 1.2575 | -52.8208 | 54.0783 | -1.3047 | 7 | 33.3333 | 2.4045 |
| `000858/SZSE` | 五粮液 | 新策略：无分钟数据日线 fallback | 94464.78 | -5.5352 | -52.8208 | 47.2856 | -5.9423 | 64 | 25.8065 | 0.2469 |
| `000858/SZSE` | 五粮液 | 新策略：日线 + 30m 确认 | 99643.46 | -0.3565 | -52.8208 | 52.4643 | -0.5813 | 2 | 0.0000 | 0.0000 |
| `000858/SZSE` | 五粮液 | 新策略：日线 + 30m 确认 + 15m 风控 | 99643.46 | -0.3565 | -52.8208 | 52.4643 | -0.5813 | 2 | 0.0000 | 0.0000 |
| `601318/SSE` | 中国平安 | 日线缠论结构基线 | 98023.55 | -1.9764 | 23.8525 | -25.8289 | -2.8425 | 68 | 38.2353 | 0.6924 |
| `601318/SSE` | 中国平安 | 日线缠论量价融合基线 | 99564.03 | -0.4360 | 23.8525 | -24.2885 | -1.5681 | 72 | 45.7143 | 0.8906 |
| `601318/SSE` | 中国平安 | 新策略：无分钟数据日线 fallback | 97626.70 | -2.3733 | 23.8525 | -26.2258 | -2.4583 | 72 | 34.3750 | 0.6039 |
| `601318/SSE` | 中国平安 | 新策略：日线 + 30m 确认 | 98085.55 | -1.9144 | 23.8525 | -25.7669 | -2.2588 | 6 | 0.0000 | 0.0000 |
| `601318/SSE` | 中国平安 | 新策略：日线 + 30m 确认 + 15m 风控 | 98085.55 | -1.9144 | 23.8525 | -25.7669 | -2.2588 | 6 | 0.0000 | 0.0000 |
| `600901/SSE` | 江苏金租 | 日线缠论结构基线 | 99907.29 | -0.0927 | 85.0153 | -85.1080 | -0.3171 | 79 | 35.8974 | 1.1002 |
| `600901/SSE` | 江苏金租 | 日线缠论量价融合基线 | 99870.33 | -0.1297 | 85.0153 | -85.1450 | -0.2340 | 66 | 30.3030 | 0.5451 |
| `600901/SSE` | 江苏金租 | 新策略：无分钟数据日线 fallback | 99909.42 | -0.0906 | 85.0153 | -85.1059 | -0.3105 | 80 | 38.2353 | 1.0167 |
| `600901/SSE` | 江苏金租 | 新策略：日线 + 30m 确认 | 99877.67 | -0.1223 | 85.0153 | -85.1376 | -0.1223 | 11 | 25.0000 | 0.3766 |
| `600901/SSE` | 江苏金租 | 新策略：日线 + 30m 确认 + 15m 风控 | 99877.67 | -0.1223 | 85.0153 | -85.1376 | -0.1223 | 11 | 25.0000 | 0.3766 |
| `600989/SSE` | 宝丰能源 | 日线缠论结构基线 | 100892.83 | 0.8928 | 87.6963 | -86.8035 | -1.0470 | 50 | 50.0000 | 1.9958 |
| `600989/SSE` | 宝丰能源 | 日线缠论量价融合基线 | 100490.33 | 0.4903 | 87.6963 | -87.2060 | -0.6502 | 26 | 50.0000 | 2.1004 |
| `600989/SSE` | 宝丰能源 | 新策略：无分钟数据日线 fallback | 100704.72 | 0.7047 | 87.6963 | -86.9916 | -1.2260 | 57 | 44.4444 | 1.7098 |
| `600989/SSE` | 宝丰能源 | 新策略：日线 + 30m 确认 | 99565.22 | -0.4348 | 87.6963 | -88.1311 | -1.2194 | 18 | 62.5000 | 1.2651 |
| `600989/SSE` | 宝丰能源 | 新策略：日线 + 30m 确认 + 15m 风控 | 99474.54 | -0.5255 | 87.6963 | -88.2218 | -1.2212 | 20 | 55.5556 | 1.1430 |
| `603986/SSE` | 兆易创新 | 日线缠论结构基线 | 157302.04 | 57.3020 | 459.7579 | -402.4559 | -6.7301 | 105 | 51.0204 | 3.1668 |
| `603986/SSE` | 兆易创新 | 日线缠论量价融合基线 | 114584.31 | 14.5843 | 459.7579 | -445.1736 | -8.2670 | 129 | 41.9355 | 1.5751 |
| `603986/SSE` | 兆易创新 | 新策略：无分钟数据日线 fallback | 127333.98 | 27.3340 | 459.7579 | -432.4239 | -8.8831 | 111 | 41.8605 | 3.3158 |
| `603986/SSE` | 兆易创新 | 新策略：日线 + 30m 确认 | 125922.60 | 25.9226 | 459.7579 | -433.8353 | -6.5968 | 24 | 58.3333 | 5.3259 |
| `603986/SSE` | 兆易创新 | 新策略：日线 + 30m 确认 + 15m 风控 | 117634.09 | 17.6341 | 459.7579 | -442.1238 | -6.5968 | 24 | 58.3333 | 3.9428 |

## Aggregate View

| Strategy | Avg return % | Median return % | Avg excess % | Avg max DD % | Total trades | Symbols traded |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 日线缠论结构基线 | 9.6964 | 0.4001 | -116.8103 | -3.3310 | 426 | 6 |
| 日线缠论量价融合基线 | 2.8236 | 0.8328 | -123.6832 | -2.7331 | 382 | 6 |
| 新策略：无分钟数据日线 fallback | 4.1274 | 0.3070 | -122.3794 | -3.8445 | 457 | 6 |
| 新策略：日线 + 30m 确认 | 3.5843 | -0.3957 | -122.9224 | -2.4152 | 79 | 6 |
| 新策略：日线 + 30m 确认 + 15m 风控 | 2.2745 | -0.4410 | -124.2323 | -2.4155 | 81 | 6 |

## Interpretation

- The 30m confirmation layer sharply reduced turnover: 79 trades versus 426 for the daily Chan baseline and 457 for the new strategy's daily fallback. This is the intended direction for filtering noisy daily-only reversals.
- The same 30m gate improved average max drawdown versus the daily fallback, from `-3.8445%` to `-2.4152%`.
- The 15m risk layer did not improve aggregate return in this fixture set. It helped 中芯国际 versus 30m-only, was neutral on several names, and reduced 兆易创新's strong-trend result.
- The current public AKShare minute coverage is incomplete versus the fixed three-year daily window, especially for `15m`. Treat this as baseline validation for the multi-level plumbing and risk behavior, not as final parameter optimization.
- Next useful strategy work should either improve minute history depth or retune `min_confirm_score`, `min_risk_score`, and `minute_sell_mode` on fuller intraday coverage before promoting the multilevel strategy as a default replacement.

## Screenshot Acceptance

Browser plugin path was attempted first, but the in-app Browser runtime failed before navigation with missing request metadata field `sandboxPolicy`. Per the project screenshot workflow, validation fell back to headless Chrome/CDP.

Standard React platform screenshots:

```bash
node scripts/capture_app_screenshots.mjs --url http://localhost:5173 --out-dir docs/qa/screenshots --prefix 2026-06-21-chan-multilevel-reversal
```

Result:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_desktop_1440.png` (`1440x1024`)
- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_mobile_390.png` (`390x844`)

Interactive strategy-workshop check:

- Loaded `http://localhost:5173`.
- Selected `缠论多级别反转` / `ChanMultiLevelReversalStrategy`.
- Verified rendered text contains `确认级别`, `30m`, `风控级别`, `15m`, `confirm_then_risk`, and `reduce`.
- Verified no framework overlay and no relevant console `error`/`warn` entries.

Result:

- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_strategy-workshop_desktop_1440.png` (`1440x1024`)
- `docs/qa/screenshots/2026-06-21-chan-multilevel-reversal_strategy-params-visible_desktop_1440.png` (`1440x1024`)
