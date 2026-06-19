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
