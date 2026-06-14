#!/usr/bin/env bash
set -euo pipefail

cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port "${FRONTEND_PORT:-5173}"
