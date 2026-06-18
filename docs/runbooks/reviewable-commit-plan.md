# Reviewable Commit Plan

This plan splits the current large migration into reviewable commits without
staging or committing automatically. Re-check `git status --short --untracked-files=all`
before running any command below, because hourly automation and manual edits may
change the worktree between runs.

## Current Snapshot

Observed changed areas:

- Product UI and API: Signal Radar page, batch research signal API, API client types, shell navigation, and styles.
- Error handling coverage: frontend task failure tests and API route coverage.
- Documentation and rules: README, architecture, continuation rules, pending backlog, web-console runbook, QA evidence, and runbook index.
- Local automation: launchd plist, hourly continuation shell script, and its runbook.

No `src/ai_trade_system/web/app.py` or `data/000001_daily.csv` changes were present in the current snapshot.

## Suggested Commit Order

### 1. Signal Radar API and Backend Contract

Purpose: introduce the batch research signal route and backend behavior before wiring the React page.

Stage:

```bash
git add src/ai_trade_system/api/app.py \
  src/ai_trade_system/api/schemas.py \
  src/ai_trade_system/api/service.py \
  tests/test_api_routes.py
git commit -m "Add signal radar batch research API"
```

Verify before commit:

```bash
python -m pytest tests/test_api_routes.py
```

Review focus:

- `/api/research/signals/batch` accepts `catalog`, `local_csv`, and `current` universes.
- Missing CSV candidates remain visible with `MISSING_CSV` blockers.
- Existing route contracts still pass.

### 2. Signal Radar React Workspace

Purpose: add the visible Signal Radar workspace, API client hook, navigation entry, types, and page styling.

Stage:

```bash
git add frontend/src/api/client.ts \
  frontend/src/api/client.test.ts \
  frontend/src/pages/SignalRadarPage.tsx \
  frontend/src/pages/SignalRadarPage.test.tsx \
  frontend/src/shell/AppShell.tsx \
  frontend/src/shell/AppShell.test.tsx \
  frontend/src/styles.css \
  frontend/src/types.ts
git commit -m "Add Signal Radar workspace"
```

Verify before commit:

```bash
cd frontend
npm test -- client.test.ts SignalRadarPage.test.tsx AppShell.test.tsx
npm run build
```

Review focus:

- The navigation count changes from eight to nine workspaces.
- Scan history, CSV export, universe selection, and missing-data handoff are visible in tests and UI.
- Styles remain scoped to Signal Radar classes.

### 3. API Failure-State Coverage

Purpose: keep error-state behavior reviewable separately from feature UI.

Stage:

```bash
git add frontend/src/shell/AppShell.tasks.test.tsx
git commit -m "Cover frontend API failure states"
```

Verify before commit:

```bash
cd frontend
npm test -- AppShell.tasks.test.tsx
```

Review focus:

- Failed data load, backtest, AI research, and risk evaluation calls leave the UI usable.
- Error messages surface backend `detail` text through the shared API error formatter.

### 4. Project Documentation and Continuation Rules

Purpose: capture durable product, architecture, QA, and continuation knowledge.

Stage:

```bash
git add AGENTS.md \
  README.md \
  docs/architecture.md \
  docs/context/pending-features.md \
  docs/rules/feature-backlog-continuation.md \
  docs/qa/2026-06-14-signal-radar-five-feature-qa.md \
  docs/runbooks/README.md \
  docs/runbooks/web-console.md \
  docs/runbooks/reviewable-commit-plan.md
git commit -m "Document Signal Radar and continuation workflow"
```

Verify before commit:

```bash
test -s docs/context/pending-features.md
test -s docs/runbooks/web-console.md
test -s docs/runbooks/reviewable-commit-plan.md
rg -n "Signal Radar|信号雷达|Next Recommended Feature|API 错误响应契约" README.md docs AGENTS.md
```

Review focus:

- `docs/context/pending-features.md` keeps exactly one next recommended feature.
- Five-feature continuation mode is documented in both `AGENTS.md` and `docs/rules/feature-backlog-continuation.md`.
- Browser screenshot evidence path is recorded in QA docs.

### 5. Local Hourly Continuation Automation

Purpose: isolate machine-local automation from product/runtime changes so it can be included, edited, or omitted independently.

Stage:

```bash
git add docs/runbooks/hourly-codex-continuation.md \
  launchd/com.jeevan.ai-trade-system.hourly-continue.plist \
  scripts/hourly_continue_project.sh
git commit -m "Add hourly Codex continuation automation"
```

Verify before commit:

```bash
bash -n scripts/hourly_continue_project.sh
plutil -lint launchd/com.jeevan.ai-trade-system.hourly-continue.plist
test -s docs/runbooks/hourly-codex-continuation.md
```

Review focus:

- The automation runs with `--ask-for-approval never` and `--sandbox danger-full-access`; reviewers should decide whether this belongs in the repository.
- Runtime logs remain under `logs/automation/` and should stay untracked.

## Final Batch Verification

After the commits are created, run:

```bash
python -m pytest
cd frontend
npm test
npm run build
```

For browser-visible changes, capture the React platform screenshots with the documented headless workflow and include the screenshot paths in the PR or close-out note.

## Do Not Commit Automatically When

- `git status` shows new files not listed above.
- A file has both user edits and automation edits that cannot be separated confidently.
- Tests fail for reasons unrelated to the staged group.
- The owner has not decided whether the local launchd automation belongs in version control.
