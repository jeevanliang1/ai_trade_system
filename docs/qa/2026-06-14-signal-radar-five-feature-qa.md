# Signal Radar Five-Feature QA - 2026-06-14

## Scope

This QA note covers the five-feature continuation pass that extended Signal Radar and added API/frontend regression coverage.

Completed user-facing areas:

- Signal Radar scan universe selector: catalog, local CSV only, and current symbol.
- Missing-data handoff from a radar result card into shared Data Center settings.
- Scan history plus CSV export for the current ranked radar result.
- Frontend failure-state coverage for data load, backtest, and AI research API errors.
- API route coverage for strategy template/source editing, paper run/events, and portfolio preview contracts.

## Verification

Commands:

```bash
PYTHONPATH=src python -m pytest
cd frontend && npm test -- --run
cd frontend && npm run build
```

Observed results:

- Python: 79 passed.
- Frontend: 15 files, 75 tests passed.
- Build: TypeScript plus Vite production build succeeded.

## Browser Evidence

Manual browser QA used the React platform at `http://127.0.0.1:5174/` with `API_PORT=8765 FRONTEND_PORT=5174 ./scripts/run_all.sh`.

Verified visible state:

- `信号雷达` workspace opened successfully.
- `扫描范围` selected `仅本地CSV`.
- `批量扫描` produced a ranked result.
- `历史扫描` appeared after the scan.
- `导出CSV` appeared and used a `data:text/csv` href.

Screenshot:

```text
/tmp/ai_trade_system_signal_radar_five_feature_browser.png
```
