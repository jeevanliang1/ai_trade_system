# Signal Radar Volume Momentum Design

Date: 2026-06-19

## Goal

Add a second Signal Radar scoring mode that ranks A-share candidates by the same volume-price momentum semantics as `VolumeConfirmedMomentumStrategy`. The existing Chan/RSI research ranking must remain the default mode, and scans must continue to use only local persisted market data.

## Chosen Approach

Extend `/api/research/signals/batch` with a `score_mode` request field:

- `research`: current Chan/RSI research score behavior. This remains the default for backward compatibility.
- `volume_momentum`: a deterministic volume-price momentum ranking derived from local daily bars.

The React Signal Radar page should expose this as a compact scoring-mode control with Chinese labels:

- `Chan/RSI研究分`
- `量价动量`

The mode switch changes the scan payload, result title, table columns, detail card content, and CSV export fields, but it does not trigger any automatic download or live trading action.

## Backend Contract

`ResearchSignalBatchRequest` adds:

- `score_mode: Literal["research", "volume_momentum"] = "research"`

`ResearchSignalBatchResponse` adds:

- `score_mode`: the resolved scoring mode.

Each `ResearchSignalBatchRow` may add:

- `momentum`: nullable volume-momentum diagnostics when `score_mode` is `volume_momentum`.

The diagnostic object should include:

- `momentum_pct`: latest close versus the configured momentum lookback, in percent.
- `volume_ratio`: latest volume divided by the configured average-volume baseline.
- `trend_pass`: whether latest close is above the trend average.
- `entry_ready`: whether price momentum, volume expansion, and trend filter all pass.
- `latest_reason`: a plain reason such as `volume_confirmed_momentum_entry`, `momentum_not_enough`, `volume_not_enough`, or `trend_filter_failed`.

Existing `score` fields remain compatible with the table contract:

- `total_score`: non-negative ranking score where higher means more attractive volume-price momentum.
- `direction`: `bullish` when all entry conditions pass, `neutral` when incomplete or mixed, and `bearish` only for materially negative momentum.
- `confidence`: normalized confidence for the row.
- `summary`: Chinese summary suitable for cards and CSV exports.
- `chan_score` and `rsi_score`: kept as `0` for compatibility in volume-momentum mode.

## Data Path Rules

Batch scans must resolve stock CSV files through the managed data layout:

`data/market/a_share/{exchange}/{code}/{code}_{exchange}_daily_{adjust}_latest.csv`

Use `data_manager.data_file_for_stock` and the request's `adjust` setting to derive this path. Do not reintroduce `data/{code}_daily.csv` for stock-aware scan flows.

For `universe = "local_csv"`, only include catalog candidates whose managed latest CSV exists.

For missing rows, return the same managed CSV path so the existing "prepare data" handoff can put the exact target into shared Data Center settings.

## Volume Momentum Ranking

The first slice should use the current strategy defaults unless future UI tuning adds explicit controls:

- `momentum_window = 20`
- `min_momentum_pct = 0.08`
- `volume_window = 20`
- `volume_multiplier = 1.5`
- `trend_window = 60`

For each candidate with enough bars:

1. Compare latest close to the close `momentum_window` bars ago.
2. Compare latest volume to the average of the prior `volume_window` bars.
3. Compare latest close to the average of the prior `trend_window` closes.
4. Compute a non-negative score from momentum strength, volume expansion, and trend pass.
5. Rank volume-momentum rows by `total_score` descending, keeping missing-data rows after scanned rows.

Rows with insufficient history should remain visible with a blocker rather than being silently dropped.

## Frontend Contract

Signal Radar should:

- Keep `research` as the default mode.
- Submit `score_mode` on every batch scan.
- Show a mode-specific result title: `研究评分排行` or `量价动量排行`.
- Render volume-momentum diagnostics in the table and detail cards when present.
- Export `momentum_pct`, `volume_ratio`, `trend_pass`, and `latest_reason` columns in CSV.
- Update the static copy to say scans read managed local market-data CSVs and do not auto-download or trade.
- Preserve scan history, export, and missing-data handoff behavior.

## Tests

Use test-first implementation.

Backend tests should cover:

- Default requests still resolve to `score_mode = "research"`.
- `volume_momentum` scans rank candidates from canonical managed CSV paths.
- Missing candidates return canonical managed CSV paths for Data Center handoff.
- `local_csv` universe uses managed CSV existence rather than legacy `data/{code}_daily.csv`.

Frontend tests should cover:

- Default Signal Radar scans submit `score_mode = "research"`.
- Selecting `量价动量` submits `score_mode = "volume_momentum"` and renders momentum diagnostics.
- Missing-data handoff uses the canonical managed CSV path returned by the API.
- CSV export includes the new momentum diagnostic columns.

## Out Of Scope

- New live trading or broker integration.
- Auto-downloading data during a scan.
- Intraday, tick, short-selling, leverage, or multi-timeframe ranking.
- Optimizing strategy thresholds against benchmarks in this slice.
- Adding a separate strategy parameter-tuning UI to Signal Radar.
