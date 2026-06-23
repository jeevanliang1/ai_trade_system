# AKShare Minute Data QA

## Scope

Implemented first-class `timeframe` support for AKShare market data:

- `daily` remains the default.
- Minute periods: `1m`, `5m`, `15m`, `30m`, `60m`.
- `Bar` now carries optional `timestamp` plus `timeframe`.
- CSV read/write remains backward-compatible with legacy daily files.
- Managed market-data files include the timeframe in latest and increment filenames.
- API, CLI, React Data Center, Stock Config, backtest, paper trading, and signal preview paths propagate the selected timeframe.

## AKShare Limitation

The upstream AKShare minute interface supports 1/5/15/30/60 minute periods, but `1m` historical depth and复权 behavior are limited by the public source. The system persists what AKShare returns and does not synthesize unavailable long-range 1-minute bars.

## Verification

Commands run:

```bash
python -m pytest tests/test_market_data.py tests/test_data_manager.py tests/test_api_routes.py::test_download_data_route_supports_minute_timeframe -q
```

Result: `15 passed`.

```bash
AI_TRADE_LLM_PROVIDER=mock python -m pytest -q
```

Result: `263 passed`.

```bash
npm --prefix frontend test
```

Result: `21 passed`, `101 passed`.

```bash
npm --prefix frontend run build
```

Result: production build succeeded.

Note: plain `python -m pytest -q` in this local environment selected `DeepSeekLLMProvider` from local environment configuration and failed an existing Mock-provider assertion. Re-running with `AI_TRADE_LLM_PROVIDER=mock` isolates tests from machine-local LLM settings.

## Screenshot Acceptance

Browser plugin status: attempted first, but the Browser runtime failed to start because the Node REPL request metadata was missing `sandboxPolicy`. Fell back to the repository headless Chrome/CDP screenshot workflow.

Commands run:

```bash
node scripts/capture_app_screenshots.mjs --url http://localhost:5173 --out-dir docs/qa/screenshots --prefix 2026-06-21-akshare-minute-data
```

Result:

- `docs/qa/screenshots/2026-06-21-akshare-minute-data_desktop_1440.png`
- `docs/qa/screenshots/2026-06-21-akshare-minute-data_mobile_390.png`

Interactive flow verified with headless Chrome/CDP:

1. Load `http://localhost:5173`.
2. Open `数据中心`.
3. Switch `行情周期` to `15m`.
4. Generate demo data.
5. Verify the rendered state has `timeframeValue: "15m"`, `metricPeriod: "15m"`, `下载15分钟数据`, `timestamp` and `timeframe` table columns, no framework error overlay, and no console error/warn entries.

Result:

- `docs/qa/screenshots/2026-06-21-akshare-minute-data_demo-15m_desktop_1440.png`
- `docs/qa/screenshots/2026-06-21-akshare-minute-data_demo-15m_mobile_390.png`
- `docs/qa/screenshots/2026-06-21-akshare-minute-data_demo-15m_mobile-timeframe_390.png`

## Strategy Benchmark Rule

Skipped fixed six-stock strategy benchmark because this change does not alter strategy signal logic, thresholds, exits, sizing, filters, or registry defaults. It changes market-data granularity and plumbing only.
