#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [ "${SCRIPT_DIR}" = "${SCRIPT_PATH}" ]; then
  SCRIPT_DIR="."
fi

exec "${SCRIPT_DIR}/run_all.sh" "$@"
