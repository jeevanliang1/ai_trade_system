#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

python -m streamlit run src/ai_trade_system/web/app.py
