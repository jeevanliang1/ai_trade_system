# Chan Daily Anchor Default Scan Strategy QA

## Scope

Default scanning now uses the optimized `ChanMultiLevelReversalStrategy` daily-anchor preset:

```python
{
    "entry_mode": "daily_anchor",
    "confirm_timeframe": "60m",
    "risk_timeframe": "30m",
    "minute_missing_policy": "daily_only",
    "lower_level_policy": "confirm_only",
    "min_confirm_score": 28.0,
    "min_risk_score": 24.0,
    "minute_sell_mode": "reduce",
    "max_holding_bars": 30,
}
```

The routing changes cover:

- React Signal Radar default score mode.
- `/api/research/signals/batch` default `score_mode`.
- Automation weekly radar candidate scoring.
- Agent/OpenClaw `radar.scan` default score mode.
- Agent/OpenClaw default backtest/paper fallback strategy selection.

The scan score uses a `chan_structure_snapshot` evaluation so large batch scans stay fast. Full historical trading performance remains validated by the actual strategy backtest in `docs/qa/2026-06-21-chan-daily-anchor-multilevel-qa.md`.

## TDD Red Evidence

Command:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_api_routes.py::test_research_signals_batch_route_scans_local_csv_catalog \
  tests/test_api_routes.py::test_research_signals_batch_route_accepts_chan_multilevel_daily_anchor_mode \
  tests/test_agent_system_tools.py::test_default_strategy_selection_uses_chan_daily_anchor_preset \
  tests/test_agent_system_tools.py::test_radar_scan_tool_defaults_to_chan_multilevel_daily_anchor \
  tests/test_automation_radar.py::test_scan_star_radar_candidates_uses_chan_multilevel_daily_anchor_score -q
```

Observed failures before implementation:

- Batch scan default still returned `research`.
- Explicit `chan_multilevel_daily_anchor` score mode was rejected with HTTP 422.
- Agent default strategy still returned `DualMovingAverageStrategy`.
- Agent `radar.scan` still passed `research`.
- Automation radar did not call the multi-level daily-anchor score helper.

## Verification

Targeted backend:

```bash
PYTHONPATH=src python -m pytest tests/test_api_routes.py tests/test_agent_system_tools.py tests/test_automation_radar.py tests/test_automation_service.py -q
```

Result: `51 passed`.

Targeted frontend:

```bash
npm --prefix frontend test -- SignalRadarPage
```

Result: `1 passed`, `8 passed`.

Real local scan smoke:

```bash
PYTHONPATH=src python - <<'PY'
from time import perf_counter
from ai_trade_system.api.schemas import PlatformSettings, ResearchSignalBatchRequest
from ai_trade_system.api.service import batch_research_signals

settings = PlatformSettings(
    symbol="688981",
    exchange="SSE",
    start_date="20230619",
    end_date="20260619",
    adjust="qfq",
    timeframe="daily",
    csv_path="data/market/a_share/SSE/688981/688981_SSE_daily_qfq_latest.csv",
)
start = perf_counter()
payload = batch_research_signals(ResearchSignalBatchRequest(settings=settings, universe="current", limit=1, min_bars=60, lookback=160))
elapsed = perf_counter() - start
row = payload["rows"][0]
print({
    "elapsed_sec": round(elapsed, 3),
    "score_mode": payload["score_mode"],
    "available": payload["available"],
    "status": row["status"],
    "code": row["code"],
    "score_total": row["score"]["total_score"],
    "direction": row["score"]["direction"],
    "latest_signal_title": (row["latest_signal"] or {}).get("title"),
    "strategy_entry_mode": row["preview"]["strategy"]["entry_mode"] if row.get("preview") else None,
    "evaluation_method": row["preview"]["strategy"]["evaluation_method"] if row.get("preview") else None,
})
PY
```

Result:

```text
{'elapsed_sec': 0.009, 'score_mode': 'chan_multilevel_daily_anchor', 'available': 1, 'status': 'scanned', 'code': '688981', 'score_total': 78.0, 'direction': 'bullish', 'latest_signal_title': '缠论多级别日线锚定买入', 'strategy_entry_mode': 'daily_anchor', 'evaluation_method': 'chan_structure_snapshot'}
```

## Benchmark Note

No new strategy-performance benchmark was run for this routing change because strategy signal logic and the optimized preset did not change. The fixed-stock benchmark evidence for this exact preset is `docs/qa/2026-06-21-chan-daily-anchor-multilevel-qa.md`.

## Screenshot Acceptance

Browser path:

- In-app Browser runtime was available in the session but failed setup with `codex/sandbox-state-meta: missing field sandboxPolicy`.
- Fallback used Playwright `1.56.1` with system Chrome at `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`.

Rendered checks:

- Page identity: `http://127.0.0.1:5173/`, title `AI量化平台`.
- Not blank: body contains `信号雷达` and `评分模式`.
- Default selector value: `chan_multilevel_daily_anchor`.
- Default selector label: `缠论多级别日线锚定`.
- Interaction proof: switched scan universe to `current`, clicked `批量扫描`, API returned HTTP `200`, `score_mode=chan_multilevel_daily_anchor`, `rows=1`.
- Console health: no warning/error/pageerror events captured.

Screenshots:

- `docs/qa/screenshots/2026-06-21-chan-default-scan-strategy_desktop_1440.png`
- `docs/qa/screenshots/2026-06-21-chan-default-scan-strategy_scan-result_desktop_1440.png`
- `docs/qa/screenshots/2026-06-21-chan-default-scan-strategy_mobile_390.png`
