# Chan confirmation T3 consumption design

Date: 2026-06-19

## Goal

Make `ChanStructureStrategy` confirmation mode consume Chan third buy/third sell signals in addition to first-buy/first-sell divergence confirmation signals.

## Context

Fixed benchmark scans for 中芯国际 `688981/SSE` and 五粮液 `000858/SZSE` show no latest-bar `CHAN_STRUCT_BUY_CONFIRM` or `CHAN_STRUCT_SELL_CONFIRM` events at the current default analyzer parameters, while third-buy/third-sell structure signals appear repeatedly. In Chan terminology, third buy/sell is itself a confirmation-style setup after price leaves a pivot and retests without returning to the pivot range. Treating T3 as confirmation-mode eligible is more coherent than lowering the global score threshold or allowing all lower-confidence T2 repairs.

## Behavioral Contract

1. `signal_mode="confirmation"` should allow:
   - `CHAN_STRUCT_BUY_T1_DIVERGENCE`
   - `CHAN_STRUCT_SELL_T1_DIVERGENCE`
   - `CHAN_STRUCT_BUY_CONFIRM`
   - `CHAN_STRUCT_SELL_CONFIRM`
   - `CHAN_STRUCT_BUY_T3`
   - `CHAN_STRUCT_SELL_T3`
2. `CHAN_STRUCT_BUY_T2` and `CHAN_STRUCT_SELL_T2` remain structure-mode signals only.
3. `signal_mode="structure"` continues to allow T2 and T3.
4. Default `all` behavior stays unchanged because it already allows every Chan structure signal.
5. Registry description should clarify that confirmation mode includes divergence confirmation and T3 pivot retest confirmations.

## Verification

- Add failing unit tests that patched `scan_chan_structure` returns T3 buy/sell signals and `ChanStructureStrategy(signal_mode="confirmation")` trades them.
- Keep the existing T2 filter test so confirmation mode still rejects T2-only structure signals.
- Run fixed benchmark backtests for 中芯国际 and 五粮液 using default all, confirmation, confirmation lifecycle, and structure lifecycle configs.
