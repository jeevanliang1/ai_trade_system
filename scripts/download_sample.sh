#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

python -m ai_trade_system.cli download \
  --symbol 000001 \
  --exchange SZSE \
  --start 20240101 \
  --end 20241231 \
  --output data/000001_daily.csv
