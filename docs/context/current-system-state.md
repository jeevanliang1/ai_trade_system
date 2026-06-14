# Current System State

Date: 2026-06-13

## Product Scope

This repository is a self-hosted A-share quant research and paper-trading platform scaffold.

Current scope:

- Public A-share daily data download through AKShare.
- Local A-share stock catalog loaded from `data/a_share_stocks.csv`.
- Stock name/code search in CLI and React Web.
- CSV data storage and replay.
- Pure Python strategy interface.
- Technical indicator snapshots.
- Single-symbol portfolio strategy aggregation.
- Local backtesting.
- Backtest analytics and risk guardrail summaries.
- Paper trading event logs.
- React AI quant platform workbench backed by local FastAPI.
- Legacy Streamlit AI quant platform workbench retained for migration fallback.
- Mock LLM research module that combines technical indicators, information-side notes, and risk context.
- Future vn.py/broker gateway extension points.

Out of scope for now:

- Live trading.
- Broker login or order routing.
- Multi-account operation.
- Multi-symbol portfolio allocation.
- Real LLM API calls by default.

## Web Platform

Run the default React web platform with:

```bash
./scripts/run_app.sh
```

Default URL:

```text
http://localhost:5173
```

The local API runs at `http://127.0.0.1:8000`. The legacy Streamlit console can still be started with `./scripts/run_web.sh` and opens at `http://localhost:8501`.

The React web platform includes:

- Data download and CSV inspection.
- Stock search by code or Chinese name, with automatic exchange selection when the local catalog is present.
- Demo data generation when AKShare or a real CSV is unavailable.
- Strategy management and source editing for `strategies/*.py`.
- Signal preview.
- Strategy portfolio composition with weighted vote, equal vote, and first active modes.
- Strategy-selectable backtesting.
- Portfolio-strategy backtesting.
- Equity, drawdown, trade, metric, and risk views.
- Mock AI researcher with prompt mode, information-side notes, technical indicator snapshot, confidence, evidence, and risk warnings.
- Strategy-selectable paper trading.

## Strategy Model

Strategies inherit `ai_trade_system.strategy.Strategy` and implement:

```python
def on_bar(self, bar) -> list[Signal]:
    ...
```

The strategy registry discovers:

- Built-in strategies in `src/ai_trade_system/strategies/`.
- User strategies in `strategies/`.

Constructor parameters are rendered as web inputs. A constructor parameter named `symbol` defaults to the sidebar symbol.

## Portfolio Model

`PortfolioStrategy` wraps multiple `StrategyAllocation` entries and still implements the same `Strategy` interface. This lets existing backtest and paper trading services run a composed strategy without changing the event loop.

Supported modes:

- `weighted_vote`: compare weighted buy and sell scores.
- `equal_vote`: compare one vote per enabled strategy.
- `first_active`: use the first enabled strategy signal.

## AI Research Model

The LLM workflow is intentionally auditable:

- `latest_indicator_snapshot` summarizes technical state.
- Users enter information-side notes manually in the Web platform.
- `MockLLMProvider` returns a structured `LLMInsight`.
- AI output is displayed as research evidence and can lightly adjust portfolio scoring when explicitly enabled.
- It does not place live orders.

## Data Download Notes

AKShare download uses fallback sources:

```text
Eastmoney -> Tencent -> Sina
```

This fallback exists because the current server network can block Eastmoney historical requests while Tencent/Sina may still work.

## Stock Catalog Notes

The local stock catalog lives at:

```text
data/a_share_stocks.csv
```

It is refreshed explicitly with:

```bash
PYTHONPATH=src python -m ai_trade_system.cli stocks refresh --output data/a_share_stocks.csv
```

Application startup does not refresh the catalog automatically, so Web remains usable offline. If the catalog is missing, the Web controls fall back to manual symbol and exchange inputs.
