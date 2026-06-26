# Chan Strategy And Market Realtime Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove simple built-in strategies from the default product surface, keep Chan-centered strategies and Chan portfolio combinations, and prepare realtime monitoring for A-share, US-stock, and crypto signal feeds.

**Architecture:** Keep existing `Strategy.on_bar` and realtime event contracts. Narrow default strategy discovery to Chan built-ins, rebuild portfolio presets around those strategies, and introduce a realtime market-data source boundary so A-share uses AKShare while US/crypto can feed the same event model through testable demo adapters.

**Tech Stack:** Python FastAPI backend, existing strategy registry, existing realtime monitor service, React + TypeScript realtime workspace, pytest and Vitest for verification.

---

### Task 1: Chan-Only Default Strategy Surface

**Files:**
- Modify: `src/ai_trade_system/strategy_registry.py`
- Modify: `src/ai_trade_system/portfolio_presets.py`
- Test: `tests/test_strategy_registry.py`
- Test: `tests/test_builtin_popular_strategies.py`

- [ ] **Step 1: Write failing tests** asserting default discovery exposes only `ChanRsiResearchStrategy`, `ChanStructureStrategy`, `ChanVolumeFusionStrategy`, and `ChanMultiLevelReversalStrategy` as built-ins, while user strategies still load.
- [ ] **Step 2: Run targeted registry tests** with `python -m pytest tests/test_strategy_registry.py tests/test_builtin_popular_strategies.py::test_registry_includes_popular_builtin_strategies -q` and confirm the new assertions fail before implementation.
- [ ] **Step 3: Update registry and presets** by moving simple strategy specs out of `BUILTIN_STRATEGIES`, keeping implementation classes importable for historical tests, and rewriting default presets to Chan-centered combinations only.
- [ ] **Step 4: Re-run targeted tests** and keep the Chan strategy behavior tests green.

### Task 2: Realtime Market Data Source Boundary

**Files:**
- Create: `src/ai_trade_system/realtime_sources.py`
- Modify: `src/ai_trade_system/realtime.py`
- Modify: `src/ai_trade_system/api/schemas.py`
- Modify: `src/ai_trade_system/api/service.py`
- Test: `tests/test_realtime_monitor.py`

- [ ] **Step 1: Write failing tests** for routing A-share, US-stock, and crypto realtime polling through separate market-data source adapters.
- [ ] **Step 2: Run realtime tests** with `python -m pytest tests/test_realtime_monitor.py -q` and confirm failures identify the missing boundary.
- [ ] **Step 3: Implement `MarketDataSource` adapters** for existing AKShare A-share polling plus deterministic US/crypto demo bars that preserve the event model and make no trading-side effects.
- [ ] **Step 4: Add request/status fields** for `market`, `market_sources`, or equivalent source diagnostics so the API can show which market feed produced each event.
- [ ] **Step 5: Re-run realtime and API route tests**.

### Task 3: React Realtime Controls And Documentation

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/RealtimePage.tsx`
- Modify: `frontend/src/pages/RealtimePage.test.tsx`
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/context/pending-features.md`

- [ ] **Step 1: Write failing frontend tests** that the realtime page exposes market source choices for A-share, US stock, and crypto demo signals.
- [ ] **Step 2: Update frontend types/client/page** to pass selected market sources to `/api/realtime/start` and render market/source fields in status and events.
- [ ] **Step 3: Update docs** to record Chan-only default strategy surface, demo US/crypto realtime source boundaries, and next pending real-provider work.
- [ ] **Step 4: Run `python -m pytest`, frontend tests/build, then capture headless Chrome screenshots if the app can start.**
