#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-}:src"

if [ -x ".venv/bin/python" ]; then
  PYTHON=".venv/bin/python"
else
  PYTHON="python"
fi

"${PYTHON}" -m uvicorn ai_trade_system.api.app:app --host 127.0.0.1 --port "${API_PORT:-8000}" --reload
