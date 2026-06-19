# Signal Radar STAR Auto Data QA - 2026-06-20

## Scope

This QA pass covers the formal Signal Radar enhancement for broad STAR-market scanning and optional data maintenance:

- `universe=star` filters local A-share catalog candidates to SSE `688*` stocks.
- Batch scan limit accepts up to 300 candidates.
- `auto_update_data=true` runs candidate maintenance through `data_manager.update_stock_data` before scanning.
- Responses expose a `data_update` summary and per-row `data_status` only when maintenance is requested.
- React Signal Radar exposes the 科创板 scan range and the explicit “扫描前自动更新数据” toggle.

This work does not modify strategy signal logic or add a new strategy, so the fixed six-stock strategy benchmark rule was not triggered.

## Automated Verification

```bash
PYTHONPATH=src python -m pytest \
  tests/test_api_routes.py::test_research_signals_batch_route_scans_local_csv_catalog \
  tests/test_api_routes.py::test_research_signals_batch_route_can_scan_only_local_csv_universe \
  tests/test_api_routes.py::test_research_signals_batch_star_universe_filters_star_candidates \
  tests/test_api_routes.py::test_research_signals_batch_star_universe_honors_query \
  tests/test_api_routes.py::test_research_signals_batch_auto_updates_star_data_before_scan \
  tests/test_api_routes.py::test_research_signals_batch_auto_update_failure_returns_blocker \
  tests/test_api_routes.py::test_research_signals_batch_route_ranks_volume_momentum_from_managed_csv \
  tests/test_api_routes.py::test_research_signals_batch_route_ranks_chan_structure_from_managed_csv -q
```

Result: `8 passed in 0.84s`.

```bash
PYTHONPATH=src python -m pytest
```

Result: `189 passed in 4.49s`.

```bash
cd frontend && npm test -- --run SignalRadarPage
```

Result: `8 passed`.

```bash
cd frontend && npm test -- --run
```

Result: `18 passed`, `92 passed`.

```bash
cd frontend && npm run build
```

Result: TypeScript and Vite build completed successfully.

## Browser QA

Local app:

```bash
./scripts/run_app.sh
```

Target flow:

```text
http://127.0.0.1:5173/ -> 信号雷达 -> 扫描范围=科创板 -> 扫描前自动更新数据=checked
```

Browser checks:

| Check | Result |
| --- | --- |
| Page identity | `http://127.0.0.1:5173/`, title `AI量化平台` |
| Not blank | Signal Radar content and controls rendered |
| Framework overlay | None observed |
| Console health | 0 `error` / `warn` logs |
| Desktop interaction | selected scan range value `star`, auto-update checkbox `checked` |
| Mobile interaction | selected scan range value `star`, auto-update checkbox `checked` |
| Mobile overflow | `scrollWidth=390`, `clientWidth=390` |

Screenshot evidence:

- Desktop: `docs/qa/screenshots/2026-06-20-signal-radar-star-auto-data-desktop.png`
- Mobile: `docs/qa/screenshots/2026-06-20-signal-radar-star-auto-data-mobile.png`

## Real Small-Sample Smoke Test

Command shape:

```bash
PYTHONPATH=src python - <<'PY'
# Calls ai_trade_system.api.service.batch_research_signals directly with:
# universe="star", limit=5, score_mode="volume_momentum",
# auto_update_data=True, if_stale=True, adjust="qfq"
PY
```

Initial request range:

```text
start_date=20230619
end_date=20260619
```

Result:

| Metric | Value |
| --- | --- |
| Universe | `star` |
| Score mode | `volume_momentum` |
| Candidates | 5 |
| Available | 5 |
| Missing | 0 |
| Data update | `updated=5`, `skipped=0`, `failed=0` |

Rows:

| Rank | Code | Name | Rows | Local data end | Score | Scan status |
| --- | --- | --- | ---: | --- | ---: | --- |
| 1 | `688003` | 天准科技 | 726 | 2026-06-18 | 82.33 | scanned |
| 2 | `688001` | 华兴源创 | 726 | 2026-06-18 | 74.70 | scanned |
| 3 | `688002` | 睿创微纳 | 726 | 2026-06-18 | 50.52 | scanned |
| 4 | `688005` | 容百科技 | 723 | 2026-06-18 | 15.00 | scanned |
| 5 | `688004` | 博汇科技 | 726 | 2026-06-18 | 0.00 | scanned |

Persisted files:

```text
data/market/a_share/SSE/688001/688001_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/688002/688002_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/688003/688003_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/688004/688004_SSE_daily_qfq_latest.csv
data/market/a_share/SSE/688005/688005_SSE_daily_qfq_latest.csv
```

Repeatability check:

- Re-running the same effective range ending at the actual local data end `20260618` returned `updated=0`, `skipped=5`, `failed=0`, with all 5 rows scanned from local CSV.
- Re-running with requested `end_date=20260619` attempted to fetch the missing one-day range after the local `2026-06-18` end date; the provider returned no usable data for that day, so the maintenance summary was `failed=5`, while the scan still completed from existing local CSV. This is a maintenance-status edge case rather than a scan blocker.

## Freshness Edge Fix - 2026-06-20

Follow-up fix:

- `update_stock_data` now catches incremental fetch exceptions only when an existing local `latest.csv` is present.
- In that case it returns `status="skipped"` with the existing `latest_rows`, `latest_start`, `latest_end`, and path, and a message beginning `using existing local data`.
- First-time downloads with no local data still raise to the caller and remain true `failed` maintenance events.

Regression checks:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_data_manager.py \
  tests/test_api_routes.py::test_research_signals_batch_auto_update_skips_when_increment_fetch_fails_but_local_csv_exists \
  tests/test_api_routes.py::test_research_signals_batch_auto_update_failure_returns_blocker \
  tests/test_api_routes.py::test_research_signals_batch_auto_updates_star_data_before_scan -q
```

Result: `8 passed in 1.08s`.

Real small-sample repeat after the fix, using the same 5 persisted STAR stocks and requested `end_date=20260619`:

| Metric | Value |
| --- | --- |
| Candidates | 5 |
| Available | 5 |
| Missing | 0 |
| Data update | `updated=0`, `skipped=5`, `failed=0` |
| Row status | all `scanned` |
| Local data end | 2026-06-18 |

The rows keep the same ranking and scores from the initial smoke test while reporting maintenance as skipped from usable existing CSVs instead of failed.
