# AI Quant Platform Design

Date: 2026-06-13

## Goal

Upgrade the current Streamlit scaffold into a complete, operable A-share quantitative research platform. The platform must support data inspection, custom strategies, strategy composition, backtesting, paper-trading replay, risk controls, and an LLM-assisted research workflow that combines technical indicators with information-side evidence. It remains a research and paper-trading system; live order routing is still out of scope.

## Research Basis

Mature quant platforms converge on a small set of product capabilities:

- Modular strategy pipeline: asset universe, alpha or signal generation, portfolio construction, execution simulation, and risk management.
- Data center: historical data download/import, data quality checks, and local storage.
- Strategy workbench: strategy code, parameters, indicators, signal preview, and reusable strategy templates.
- Backtesting and analysis: equity curve, drawdown, trades, benchmark comparison, metrics, and parameter experiments.
- Risk and protection layer: order sizing, exposure limits, drawdown controls, cooldowns, and rejected-order explanations.
- Paper-trading or dry-run mode: replay or forward-test strategies without live capital.
- AI-assisted research: structured evidence gathering, technical and sentiment analysis, decision synthesis, and auditable recommendations.

The implementation will borrow the modular separation used by larger platforms without importing heavyweight trading frameworks.

## Chosen Visual Direction

Use the generated **Strategy Research Workbench** concept as the primary visual target:

```text
docs/superpowers/assets/ai-quant-platform-research-workbench.png
```

Design qualities:

- Bright professional research cockpit, not a marketing page.
- Persistent left navigation with clear product sections.
- Top command bar with market, connection, date, task, and settings status.
- Three-zone workbench: strategy controls on the left, charts/results in the center, AI/risk inspector on the right.
- Tables, inputs, charts, and compact controls are first-class UI; decorative imagery is not used.
- Palette: light neutral surface, graphite text, subtle grid lines, green/red market semantics, blue primary actions, amber risk warnings.
- Corners stay tight, around 6-8px. Avoid nested cards and oversized rounded blocks.

## Product Surface

### 总览

Purpose: show the state of the quant platform before the user drills into a task.

Must show:

- Data availability and last trading day.
- Active strategy and selected symbol.
- Latest backtest summary.
- Paper-trading log status.
- AI research status and latest structured view.
- Risk status.

### 数据中心

Purpose: manage A-share daily data and verify whether local data is usable.

Must support:

- Symbol, exchange, start date, end date, adjust mode, and CSV path controls.
- AKShare download using the existing fallback source logic.
- Existing CSV loading.
- Data coverage metrics, latest close, volume, turnover, and row preview.
- Data quality summary: empty file, missing rows if detectable, date range, and symbol count.

### 策略工坊

Purpose: create, edit, parameterize, and preview strategies.

Must support:

- Discover built-in and `strategies/*.py` strategies.
- Create user strategy templates.
- Edit trusted user strategy source.
- Render constructor parameters as inputs.
- Preview buy/sell signals against loaded bars.
- Show selected strategy metadata and warnings that user strategy code executes locally.

### 组合实验室

Purpose: combine multiple strategies before running experiments.

Must support:

- Add multiple discovered strategies to a portfolio.
- Configure strategy weights.
- Choose signal aggregation mode: weighted vote, equal weight, or first active signal.
- Enable or disable AI score adjustment.
- Preview effective allocation and combined signal counts.

The first implementation can use one symbol and one shared bar series, matching the current engine. The module boundary must allow future multi-symbol expansion.

### 回测中心

Purpose: run single-strategy and portfolio-strategy backtests.

Must support:

- Initial cash, commission, slippage, max order cash, and date-range controls.
- Run single strategy or current portfolio.
- Equity curve, drawdown curve, price chart with signal markers, trade table, and metric summary.
- Metrics: total return, annualized return, max drawdown, win rate, trade count, profit factor when computable, final equity, cash, exposure proxy.

### AI研究员

Purpose: make the LLM-assisted quant workflow explicit and auditable.

Must support:

- Mock provider by default, with a provider interface that can later call real APIs.
- Inputs: latest indicator snapshot, recent bars summary, strategy signals, portfolio weights, risk thresholds, and information-side notes.
- Information-side notes can be entered manually in the UI until real news connectors exist.
- Prompt mode selector: conservative, balanced, aggressive.
- Output a structured `LLMInsight`:
  - symbol
  - horizon
  - direction: bullish, bearish, neutral
  - confidence: 0-100
  - suggested action: buy, sell, hold, reduce, observe
  - technical evidence list
  - information-side evidence list
  - risk warnings
  - prompt version
  - provider name
  - created timestamp
- AI output must be research advice only. It may influence portfolio scoring when the user enables it, but it must pass deterministic risk controls and must not create live orders.

### 纸面交易

Purpose: replay CSV bars through strategy or portfolio logic and inspect event logs.

Must support:

- Run replay using current strategy or current portfolio.
- JSONL event log output.
- Order event table, equity event table, final equity, and rejection reasons.

### 风控

Purpose: centralize risk assumptions and make protection behavior visible.

Must support:

- Max order cash.
- Max position shares.
- Minimum cash.
- Max drawdown threshold.
- Optional cooldown after drawdown breach.
- Risk status summary and reasoned warnings.

## Architecture

Keep the strategy core pure Python and add focused modules under `src/ai_trade_system/`:

- `indicators.py`: computes indicator series and latest technical snapshot from bars.
- `analytics.py`: computes equity, return, drawdown, and trade statistics.
- `portfolio.py`: defines portfolio strategy entries, signal aggregation, and portfolio strategy adapter.
- `llm.py`: defines mock provider, prompt builder, evidence snapshots, and `LLMInsight`.
- `risk.py`: centralizes high-level risk guardrail evaluation beyond the existing `PaperBroker` order checks.
- `web/components.py`: shared Streamlit styling, metrics, panel helpers, and data renderers.
- `web/app.py`: compose the professional multi-tab workbench.

Existing modules remain authoritative:

- `market.py`: `Bar` and `Signal`.
- `strategy.py`: strategy interface.
- `strategy_registry.py`: discovery and user strategy source management.
- `paper.py`: paper broker and basic order-level risk.
- `backtest.py`: event-style backtest, extended for portfolio adapters where useful.
- `paper_service.py`: CSV replay paper-trading service.

## Data Flow

```text
CSV / AKShare
  -> Bar[]
  -> indicators + latest technical snapshot
  -> strategy signals
  -> portfolio aggregation
  -> risk guardrails
  -> backtest / paper replay
  -> analytics + charts + event logs

manual information notes + indicator snapshot + strategy context
  -> LLM prompt builder
  -> MockLLMProvider
  -> LLMInsight
  -> UI explanation + optional portfolio score adjustment
```

## LLM Operating Model

The LLM module is not a trading oracle. It is a structured research layer.

Rules:

- All LLM calls must receive explicit, bounded inputs from the platform.
- All outputs must be structured dataclasses, not free-form text blobs.
- Every insight must include evidence and risk warnings.
- Mock output must be deterministic enough for tests.
- Future API providers must implement the same provider interface.
- AI must not bypass `PaperBroker` or risk guardrails.

Initial mock behavior:

- If trend and momentum are positive and information notes are positive, return bullish.
- If drawdown or RSI overbought risk is high, lower confidence and add risk warnings.
- If information notes contain negative risk terms, return neutral or bearish depending on technical state.

## Testing Strategy

Add tests before production code:

- `tests/test_indicators.py`: indicator snapshot values and edge cases.
- `tests/test_analytics.py`: drawdown and metric calculations.
- `tests/test_portfolio.py`: weighted vote aggregation and portfolio strategy adapter behavior.
- `tests/test_llm.py`: prompt snapshot and deterministic mock insight.
- `tests/test_risk.py`: drawdown and guardrail status.
- Extend web view-model tests if new frame conversion helpers are added.

Run full verification:

```bash
python -m pytest
```

For UI changes, also run Streamlit and inspect the primary workflow in a browser:

```bash
./scripts/run_web.sh
```

## Acceptance Criteria

- The app opens as a polished, professional quant platform rather than a simple demo page.
- Users can download or load CSV data, inspect it, and see data health.
- Users can add and edit trusted strategies under `strategies/`.
- Users can select strategy parameters and preview signals.
- Users can compose multiple strategies with weights and aggregation rules.
- Users can run single-strategy and portfolio backtests.
- Users can see equity, drawdown, metrics, trades, and signal markers.
- Users can run paper-trading replay and inspect event logs.
- Users can generate a mock AI research insight from technical indicators and information-side notes.
- Users can see how AI output may influence portfolio scoring when enabled.
- Risk controls are visible and deterministic.
- No live trading behavior is introduced.
- Existing CLI behavior remains working.
- `python -m pytest` passes.

## Implementation Order

1. Add tested indicators, analytics, risk, portfolio, and LLM modules.
2. Extend view models for charts, metrics, AI insight, and portfolio tables.
3. Rebuild Streamlit UI around the chosen research-workbench layout.
4. Add docs updates for the new platform workflow.
5. Run tests and browser QA.

