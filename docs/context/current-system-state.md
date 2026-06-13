# Current System State

Date: 2026-06-08

## Product Scope

This repository is a self-hosted A-share quant research and paper-trading scaffold.

Current scope:

- Public A-share daily data download through AKShare.
- CSV data storage and replay.
- Pure Python strategy interface.
- Local backtesting.
- Paper trading event logs.
- Streamlit web console.
- Future vn.py/broker gateway extension points.

Out of scope for now:

- Live trading.
- Broker login or order routing.
- Multi-account operation.
- Multi-symbol portfolio allocation.

## Web Console

Run the web console with:

```bash
./scripts/run_web.sh
```

Default URL:

```text
http://localhost:8501
```

The web console includes:

- Data download and CSV inspection.
- Strategy management and source editing for `strategies/*.py`.
- Signal preview.
- Strategy-selectable backtesting.
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

## Data Download Notes

AKShare download uses fallback sources:

```text
Eastmoney -> Tencent -> Sina
```

This fallback exists because the current server network can block Eastmoney historical requests while Tencent/Sina may still work.
