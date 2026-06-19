# STAR Full Radar Scan Top10 - 2026-06-20

## Scope

This QA note records a full local Signal Radar scan over the persisted STAR-market data.

- Universe: local A-share catalog stocks where `exchange == "SSE"` and code starts with `688`.
- Input data: `data/market/a_share/SSE/{code}/{code}_SSE_daily_qfq_latest.csv`.
- Adjustment: `qfq`.
- Scan size: 608 stocks.
- Missing data: 0 stocks.
- Network data update: not run; this scan reads the already persisted local CSV files.
- Raw ignored scan artifact: `logs/radar/star_full_radar_scan_20260620.json`.

The current API request schema caps one batch at 300 candidates. To cover all 608 STAR stocks in one pass, this run reused the existing radar scoring functions directly over every local CSV:

- Primary: Chan structure score from `_chan_structure_score`.
- Assistant: volume-price momentum score from `_volume_momentum_score`.
- Composite buy scan score: `max(chan_score, 0) + volume_score * 0.35`.

This task does not modify strategy logic or add a strategy, so the fixed six-stock strategy benchmark rule was not triggered.

## Scan Summary

| Metric | Value |
| --- | ---: |
| Total candidates | 608 |
| Scanned | 608 |
| Missing CSV | 0 |
| Below 60 bars | 6 |
| Bullish Chan structures | 230 |
| Bearish Chan structures | 153 |
| Volume-entry-ready stocks | 28 |

Latest local data end distribution:

| Local data end | Count |
| --- | ---: |
| 2026-06-18 | 605 |
| 2026-04-30 | 1 |
| 2026-06-11 | 1 |
| 2026-06-16 | 1 |

## Top10 Buy-Oriented Radar Results

The table below is a buy-candidate ranking, not a direct order instruction. Chan T2 is treated as lower-certainty starter-position evidence; Chan T3 is treated as higher-certainty add-position evidence. Volume-price momentum can raise confidence when `entry_ready=true`.

| Rank | Code | Name | Composite | Chan | Signal | Volume | Momentum | Volume Ratio | Reason |
| ---: | --- | --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| 1 | 688733 | 壹石通 | 102.5865 | 72.0 | 缠论二买 | 87.39 | 31.2865% | 1.6196x | T2 starter-position signal plus confirmed volume-price momentum. |
| 2 | 688072 | 拓荆科技 | 95.7545 | 72.0 | 缠论二买 | 67.87 | 21.1481% | 0.8016x | Strong T2 structure and trend pass, but volume confirmation is insufficient. |
| 3 | 688371 | XD菲沃泰 | 78.6710 | 72.0 | 缠论二买 | 19.06 | -2.4390% | 1.2031x | Strong T2 structure, but price momentum is not enough. |
| 4 | 688671 | 碧兴物联 | 77.3515 | 44.0 | 缠论三买 | 95.29 | 22.3857% | 2.2161x | T3 higher-certainty structure plus confirmed volume-price momentum. |
| 5 | 688206 | 概伦电子 | 77.2500 | 72.0 | 缠论二买 | 15.00 | -1.5889% | 0.5174x | Strong T2 structure, but momentum and volume confirmation are weak. |
| 6 | 688502 | 茂莱光学 | 77.2500 | 72.0 | 缠论二买 | 15.00 | -0.6836% | 0.9988x | Strong T2 structure with trend pass, but momentum is below trigger. |
| 7 | 688001 | 华兴源创 | 70.1450 | 44.0 | 缠论三买 | 74.70 | 21.4468% | 1.3040x | T3 higher-certainty structure and trend pass; volume is not enough for full momentum confirmation. |
| 8 | 688531 | 日联科技 | 68.9900 | 44.0 | 缠论三买 | 71.40 | 22.5606% | 0.7821x | T3 higher-certainty structure and positive momentum, but volume confirmation is missing. |
| 9 | 688353 | 华盛锂电 | 63.0000 | 28.0 | 缠论二买 | 100.00 | 25.8122% | 2.7020x | T2 starter-position signal with the strongest volume-price confirmation in the top10. |
| 10 | 688333 | 铂力特 | 62.1005 | 28.0 | 缠论二买 | 97.43 | 23.9945% | 2.1223x | T2 starter-position signal plus strong momentum and volume confirmation. |

## Strategy Reading

- Strongest combined candidate: `688733 壹石通`, because it has the highest Chan score among buy signals and also passes volume-price momentum confirmation.
- Cleanest high-certainty Chan candidate: `688671 碧兴物联`, because it is a T3 buy and also has confirmed volume-price momentum.
- Best volume-confirmed T2 candidates: `688733 壹石通`, `688353 华盛锂电`, and `688333 铂力特`.
- Structure-only watch candidates: `688072 拓荆科技`, `688371 XD菲沃泰`, `688206 概伦电子`, and `688502 茂莱光学`; they rank high structurally, but the assistant momentum layer is not fully confirmed.
- No top10 stock received extra confidence from divergence evidence in this run; the top10 are driven by T2/T3 structure plus volume/trend confirmation.

## Verification

Command shape:

```bash
PYTHONPATH=src python - <<'PY'
# Load all SSE 688* stocks from the local catalog.
# Read each qfq latest CSV from data/market/a_share/SSE/{code}/.
# Reuse _chan_structure_score and _volume_momentum_score.
# Persist ignored raw output to logs/radar/star_full_radar_scan_20260620.json.
PY
```

Result:

```text
total=608
scanned=608
missing=0
insufficient=6
bullish_chan=230
bearish_chan=153
volume_entry_ready=28
raw_output=logs/radar/star_full_radar_scan_20260620.json
```

## Browser QA

Not run for this CLI/data-analysis operation. No browser-renderable project surface was changed in this task.
