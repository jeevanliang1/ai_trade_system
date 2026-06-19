# STAR Market Full Data Download QA - 2026-06-20

## Scope

This QA note records the full local persistence pass for the STAR-market universe used by Signal Radar and later strategy scans.

- Universe source: local A-share catalog.
- Filter: `exchange == "SSE"` and code starts with `688`.
- Requested range: `20230619` to `20260619`.
- Adjustment: `qfq`.
- Canonical storage: `data/market/a_share/SSE/{code}/`.
- Summary artifact: `logs/data_updates/star_market_full_update_20260620.json`.

This task only downloads and verifies market data. It does not modify strategy logic or add a new strategy, so the fixed six-stock strategy benchmark rule was not triggered.

## Download Command

Command shape:

```bash
PYTHONPATH=src python - <<'PY'
# Iterates over all catalog stocks where exchange == "SSE" and code.startswith("688")
# Calls ai_trade_system.data_manager.update_stock_data(
#   stock, start_date="20230619", end_date="20260619", adjust="qfq", if_stale=True
# )
# Writes logs/data_updates/star_market_full_update_20260620.json
PY
```

## Result Summary

| Metric | Value |
| --- | ---: |
| Catalog STAR candidates | 608 |
| Summary file rows | 608 |
| Local `688*` data directories | 608 |
| Non-empty latest CSV records | 608 |
| Updated | 582 |
| Skipped from usable local CSV | 26 |
| Failed | 0 |
| Minimum local rows | 17 |
| Maximum local rows | 726 |
| Data directory size | 53M |

Latest local data end distribution:

| Local data end | Count |
| --- | ---: |
| 2026-06-18 | 605 |
| 2026-04-30 | 1 |
| 2026-06-16 | 1 |
| 2026-06-11 | 1 |

The requested `20260619` endpoint is after the latest available local trading data for most symbols. Existing CSVs are treated as reusable when the incremental provider request has no usable newer bars.

Short-history symbols below 60 rows are newly listed or recently covered by the catalog:

| Code | Name | Rows | Local data end |
| --- | --- | ---: | --- |
| 688635 | 长进光子 | 17 | 2026-06-18 |
| 688781 | 视涯科技 | 58 | 2026-06-18 |
| 688808 | 联讯仪器 | 37 | 2026-06-18 |
| 688811 | 有研复材 | 47 | 2026-06-18 |
| 688813 | 泰金新能 | 54 | 2026-06-18 |
| 688820 | 盛合晶微 | 40 | 2026-06-18 |

## Verification

Summary inspection:

```bash
python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path("logs/data_updates/star_market_full_update_20260620.json").read_text(encoding="utf-8"))
summary = data["summary"]
print(summary)
print("file_count", len(data["files"]))
print("nonzero_latest_rows", sum(1 for item in data["files"] if int(item.get("latest_rows") or 0) > 0))
print("failed_codes", [item["code"] for item in data["files"] if item.get("status") == "failed"])
PY
```

Result:

```text
total=608, updated=582, skipped=26, failed=0
file_count 608
nonzero_latest_rows 608
failed_codes []
```

Directory count:

```bash
find data/market/a_share/SSE -maxdepth 1 -type d -name '688*' | wc -l
```

Result: `608`.

Data size:

```bash
du -sh data/market/a_share/SSE
```

Result: `53M`.

Ignore check:

```bash
git status --ignored --short data/market/a_share/SSE logs/data_updates | head -80
```

Result:

```text
!! data/market/
!! logs/
```

The persisted market data and raw update summary are intentionally local ignored artifacts, while this QA note is the versioned evidence.

## Browser QA

Not run for this data-maintenance operation. No browser-renderable surface was changed in this task.
