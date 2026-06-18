# Hourly Codex Continuation Task

This project can run an hourly local Codex continuation task through macOS `launchd`.

## Installed Agent

- Label: `com.jeevan.ai-trade-system.hourly-continue`
- Source plist: `launchd/com.jeevan.ai-trade-system.hourly-continue.plist`
- Installed plist: `~/Library/LaunchAgents/com.jeevan.ai-trade-system.hourly-continue.plist`
- Script: `scripts/hourly_continue_project.sh`
- Prompt: `继续完成项目`
- Interval: 3600 seconds

The script enters `/Users/jeevanliang/Desktop/github/ai_trade_system`, creates a lock directory under `logs/automation/`, and runs:

```bash
/Applications/Codex.app/Contents/Resources/codex exec \
  --cd /Users/jeevanliang/Desktop/github/ai_trade_system \
  --sandbox danger-full-access \
  --ask-for-approval never \
  --json \
  --output-last-message logs/automation/<timestamp>-last-message.md \
  "继续完成项目"
```

## Logs

Runtime logs are under `logs/automation/`, which is ignored by git:

- `hourly_continue.log`: starts, skips, and completions.
- `hourly_continue.err`: Codex stderr.
- `codex-<timestamp>.jsonl`: Codex JSON event stream.
- `codex-<timestamp>-last-message.md`: final assistant message from that run.
- `launchd.out` and `launchd.err`: launchd stdout/stderr files.

## Manage The Task

Check status:

```bash
launchctl print gui/$(id -u)/com.jeevan.ai-trade-system.hourly-continue
```

Run once immediately:

```bash
launchctl kickstart -k gui/$(id -u)/com.jeevan.ai-trade-system.hourly-continue
```

Unload:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.jeevan.ai-trade-system.hourly-continue.plist
```

Reload after editing the plist:

```bash
cp launchd/com.jeevan.ai-trade-system.hourly-continue.plist ~/Library/LaunchAgents/
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.jeevan.ai-trade-system.hourly-continue.plist 2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.jeevan.ai-trade-system.hourly-continue.plist
```

## Safety Notes

The task runs non-interactively with `--ask-for-approval never` and `--sandbox danger-full-access`, so it can edit files without prompting. Keep the lock in place to prevent overlapping hourly runs, and inspect `git status` plus the latest `logs/automation/*-last-message.md` before committing automated changes.
