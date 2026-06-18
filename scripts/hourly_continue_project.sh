#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="/Users/jeevanliang/Desktop/github/ai_trade_system"
CODEX_BIN="/Applications/Codex.app/Contents/Resources/codex"
LOG_DIR="${PROJECT_DIR}/logs/automation"
LOCK_DIR="${LOG_DIR}/hourly_continue.lock"
PROMPT="继续完成项目"

mkdir -p "${LOG_DIR}"

if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') skipped: previous hourly Codex task is still running" >> "${LOG_DIR}/hourly_continue.log"
  exit 0
fi

cleanup() {
  rmdir "${LOCK_DIR}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

STAMP="$(date '+%Y%m%d-%H%M%S')"
JSON_LOG="${LOG_DIR}/codex-${STAMP}.jsonl"
LAST_MESSAGE="${LOG_DIR}/codex-${STAMP}-last-message.md"

{
  echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') start: ${PROMPT}"
  echo "project: ${PROJECT_DIR}"
  echo "json_log: ${JSON_LOG}"
  echo "last_message: ${LAST_MESSAGE}"
} >> "${LOG_DIR}/hourly_continue.log"

cd "${PROJECT_DIR}"

"${CODEX_BIN}" exec \
  --cd "${PROJECT_DIR}" \
  --sandbox danger-full-access \
  --ask-for-approval never \
  --json \
  --output-last-message "${LAST_MESSAGE}" \
  "${PROMPT}" \
  >> "${JSON_LOG}" 2>> "${LOG_DIR}/hourly_continue.err"

echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') done: ${PROMPT}" >> "${LOG_DIR}/hourly_continue.log"
