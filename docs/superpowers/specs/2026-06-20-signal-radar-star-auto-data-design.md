# Signal Radar STAR Auto Data Design

Date: 2026-06-20

## Goal

Add first-class STAR Market scanning to Signal Radar, with automatic local qfq data preparation and maintenance before scanning.

## Current State

Signal Radar already supports batch scanning over:

- `catalog`: catalog search candidates
- `local_csv`: candidates that already have managed local CSV files
- `current`: the current selected symbol

It can rank candidates by `research`, `volume_momentum`, or `chan_structure` score modes. It only reads local managed CSV files under `data/market/a_share/{exchange}/{code}/` and currently reports missing CSV blockers instead of downloading data.

The existing `data_manager` already owns canonical A-share market data paths, latest CSV files, increment snapshots, manifest metadata, and stale-skip behavior. This enhancement should reuse that system.

## User Problem

The user wants broad STAR Market scans, not just manually entering `688` and scanning up to 50 candidates. They also want the system to automatically download and maintain the data needed for that scan.

## Design

### Universe

Add a new Signal Radar universe value:

- `star`: all catalog stocks where `exchange == "SSE"` and `code` starts with `688`.

`query` remains optional. If provided, it further filters the STAR universe by code prefix or name search. This preserves current search behavior while making STAR Market a first-class scope.

### Scan Size

Raise the batch scan limit upper bound from `50` to `300`.

Reasoning:

- This is enough for broad STAR scans in local usage.
- It avoids introducing background job infrastructure in this slice.
- The request remains bounded and easier to test.

### Automatic Data Maintenance

Add request fields to `ResearchSignalBatchRequest`:

- `auto_update_data: bool = False`
- `if_stale: bool = True`
- `adjust: str | None = None`

When `auto_update_data` is true:

1. Resolve the candidate universe.
2. For each candidate, compute the canonical managed qfq path with `data_manager.data_file_for_stock`.
3. If `if_stale` is true and the manifest already reaches the requested end date, skip downloading that stock.
4. Otherwise download daily bars with the existing AKShare-backed data path and persist through `data_manager`.
5. Continue scanning all candidates even if some downloads fail.
6. Attach per-row data maintenance metadata and blockers.

The scan still only ranks stocks that have readable local CSV after the update step. Failed downloads produce `missing_data` rows with a clear blocker.

### API Shape

`/api/research/signals/batch` response gains:

```json
{
  "data_update": {
    "enabled": true,
    "total": 120,
    "updated": 30,
    "skipped": 80,
    "failed": 10,
    "adjust": "qfq",
    "start_date": "20230620",
    "end_date": "20260620"
  }
}
```

Each row gains optional `data_status`:

```json
{
  "status": "updated | skipped | failed | not_requested",
  "message": "updated managed CSV",
  "rows": 726,
  "start": "2023-06-20",
  "end": "2026-06-20",
  "path": "data/market/a_share/SSE/688001/688001_SSE_daily_qfq_latest.csv"
}
```

### Frontend

Signal Radar adds:

- Scan range option: `科创板`
- Scan quantity max: `300`
- Toggle: `扫描前自动更新数据`
- Data update summary metrics when present: updated, skipped, failed
- Data status fields in detail cards and CSV export

The page should keep the current dense operational layout. No landing-page or decorative redesign is needed.

### Data Boundaries

- Use existing managed paths under `data/market/a_share/{exchange}/{code}/`.
- Use qfq by default through current platform settings unless request `adjust` overrides it.
- Do not add machine-local scheduling files.
- Do not add live trading or broker behavior.
- Do not commit downloaded market data generated during tests.

### Error Handling

- Per-stock download failures do not fail the entire scan.
- If catalog is missing and universe is `star`, return an empty result with `scanned=0`.
- If AKShare is unavailable during auto update, rows should carry failed data status and blockers; the API should still return a normal response where possible.
- Invalid universe values remain rejected by request validation.

## Testing

Backend tests should cover:

- STAR universe returns only `SSE` `688xxx` candidates.
- `query` further filters STAR candidates.
- `auto_update_data` calls the data maintenance path and then scans the resulting CSV.
- A failed update produces a row blocker instead of aborting the whole batch.
- Raised `limit` accepts values above 50 and rejects values above 300.

Frontend tests should cover:

- STAR universe option appears.
- Auto-update toggle is sent in the batch request.
- Data update summary renders when returned by the API.

## QA

Record a QA note under `docs/qa/` with:

- Targeted backend/frontend commands.
- Full `pytest`, `npm test`, and `npm run build` results.
- A manual or mocked STAR scan evidence note.
- Browser screenshot paths for Signal Radar with STAR range and auto-update visible.

This does not modify strategy logic, so the fixed six-stock strategy benchmark rule does not apply.

## Out Of Scope

- Background job queue.
- Progress streaming while a scan is running.
- Scheduling daily market-data jobs.
- Multi-symbol portfolio rotation.
- Strategy tuning or strategy benchmark changes.
