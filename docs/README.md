# AI Documentation Index

This directory is the durable project memory for humans and future AI agents. Use it for stable requirements, decisions, rules, workflows, verification knowledge, operational procedures, and handoff context.

## Existing Project Documents

- `../README.md`: setup, install commands, CLI examples for data download, backtest, paper trading, strategy guidance, and live gateway direction.
- `architecture.md`: module map, data flow, and future vn.py integration direction.
- `context/pending-features.md`: durable pending feature list and next recommended feature for continuation prompts.
- `rules/feature-backlog-continuation.md`: feature decomposition and backlog maintenance rule.
- `rules/strategy-benchmark-backtest.md`: mandatory fixed 中芯国际/五粮液 benchmark backtest rule for strategy changes.
- `../strategies/README.md`: custom strategy workspace guidance.

## Directory Map

- `prd/`: product requirements, iteration status, and PRD snapshots. Do not store temporary brainstorming notes here.
- `rules/`: long-lived team rules and AI collaboration rules. Do not duplicate implementation details from source files.
- `decisions/`: important product, technical, and architecture decisions. Prefer one dated decision per file.
- `skills/`: reusable in-repository AI workflows or transferable skills. Do not store one-off prompts here.
- `prompts/`: reusable prompts, review templates, and generation templates. Do not store project requirements here.
- `qa/`: acceptance checklists, test records, screenshot conclusions, known risks, and validation patterns.
- `runbooks/`: deployment, preview, troubleshooting, data initialization, and other operational procedures.
- `context/`: stable project context, glossary, data models, design expectations, and compact handoff notes for new conversations.

## Required Close-Out

Every accepted task must run the auto-sedimentation audit:

- Workflow: `auto-sedimentation-skill.md`
- Close-out rule: `rules/auto-sedimentation-closeout.md`
- Feature backlog rule: `rules/feature-backlog-continuation.md`
- Strategy benchmark rule: `rules/strategy-benchmark-backtest.md`
- Pending feature handoff: `context/pending-features.md`
- Future AI entry rules: `../AGENTS.md`
