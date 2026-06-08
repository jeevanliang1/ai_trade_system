#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

python -m ai_trade_system.cli paper \
  --data data/000001_daily.csv \
  --symbol 000001 \
  --fast 5 \
  --slow 20 \
  --size 100 \
  --cash 100000 \
  --log logs/paper_events.jsonl
