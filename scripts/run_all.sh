#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="${BASH_SOURCE[0]}"
SCRIPT_DIR="${SCRIPT_PATH%/*}"
if [ "${SCRIPT_DIR}" = "${SCRIPT_PATH}" ]; then
  SCRIPT_DIR="."
fi
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
FRONTEND_DIR="${ROOT_DIR}/frontend"
API_PORT="${API_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MODE="run"
API_PID=""

usage() {
  printf '%s\n' "用法：./scripts/run_all.sh [--check]"
  printf '%s\n' ""
  printf '%s\n' "默认会先检查环境和依赖，然后启动 FastAPI 与 React/Vite。"
  printf '%s\n' "--check  只执行环境和依赖检查，不启动服务。"
}

info() {
  printf '%s\n' "==> $*"
}

fail() {
  local reason="$1"
  local recommendation="$2"
  printf '%s\n' ""
  printf '%s\n' "启动前检查失败"
  printf '%s\n' "原因：${reason}"
  printf '%s\n' "建议：${recommendation}"
  exit 1
}

cleanup() {
  if [ -n "${API_PID}" ]; then
    kill "${API_PID}" 2>/dev/null || true
  fi
}

resolve_python() {
  if [ -n "${AI_TRADE_PYTHON:-}" ]; then
    if [ -x "${AI_TRADE_PYTHON}" ]; then
      PYTHON_BIN="${AI_TRADE_PYTHON}"
      return
    fi
    if command -v "${AI_TRADE_PYTHON}" >/dev/null 2>&1; then
      PYTHON_BIN="$(command -v "${AI_TRADE_PYTHON}")"
      return
    fi
    fail "AI_TRADE_PYTHON 指向的 Python 不存在或不可执行：${AI_TRADE_PYTHON}" "设置正确的 AI_TRADE_PYTHON，或在项目根目录创建虚拟环境：python -m venv .venv && source .venv/bin/activate。"
  fi

  if [ -x "${ROOT_DIR}/.venv/bin/python" ]; then
    PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
    return
  fi
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
    return
  fi
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
    return
  fi

  fail "未找到 Python，无法启动 FastAPI 后端。" "安装 Python 3.10 或 3.11，然后执行：python -m venv .venv && source .venv/bin/activate && python -m pip install -e \".[api,data]\"。"
}

check_python() {
  resolve_python
  export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

  if ! "${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
    fail "Python 版本过低，项目要求 Python 3.10 或更高版本。" "使用 Python 3.10 或 3.11 创建虚拟环境：python3.11 -m venv .venv && source .venv/bin/activate。"
  fi

  local detail
  detail="$("${PYTHON_BIN}" -c 'import importlib, sys
missing = []
for module in ("fastapi", "uvicorn", "ai_trade_system.api.app"):
    try:
        importlib.import_module(module)
    except Exception as exc:
        missing.append(f"{module}: {exc}")
if missing:
    print("; ".join(missing), file=sys.stderr)
    raise SystemExit(1)
' 2>&1)" || fail "Python API 依赖不可用：${detail}" "在项目根目录执行：python -m pip install -e \".[api,data]\"；如果尚未创建虚拟环境，先执行：python -m venv .venv && source .venv/bin/activate。"
}

check_node() {
  if [ ! -d "${FRONTEND_DIR}" ]; then
    fail "未找到 frontend 目录，无法启动 React 前端。" "确认你在完整仓库中运行，或恢复 frontend/ 目录。"
  fi
  if [ ! -f "${FRONTEND_DIR}/package.json" ]; then
    fail "未找到 frontend/package.json，无法安装或启动前端依赖。" "恢复 frontend/package.json，或重新拉取前端工程文件。"
  fi
  if ! command -v node >/dev/null 2>&1; then
    fail "未找到 node，无法启动 Vite 前端。" "安装 Node.js 20 LTS 或更高版本；macOS 可执行：brew install node。"
  fi
  if ! command -v npm >/dev/null 2>&1; then
    fail "未找到 npm，无法安装或启动 Vite 前端。" "安装 Node.js 20 LTS 或更高版本；macOS 可执行：brew install node。"
  fi

  local node_version
  local node_major
  node_version="$(node -v 2>/dev/null || true)"
  node_major="${node_version#v}"
  node_major="${node_major%%.*}"
  if ! [[ "${node_major}" =~ ^[0-9]+$ ]]; then
    fail "无法读取 Node.js 版本：${node_version:-空输出}。" "重新安装 Node.js 20 LTS 或更高版本，然后重试。"
  fi
  if [ "${node_major}" -lt 20 ]; then
    fail "Node.js 版本过低：${node_version}，当前 Vite 前端建议使用 Node.js 20 LTS 或更高版本。" "升级 Node.js；macOS 可执行：brew install node 或使用 nvm install 20。"
  fi
}

check_frontend_dependencies() {
  if [ -d "${FRONTEND_DIR}/node_modules" ]; then
    return
  fi

  info "未发现 frontend/node_modules，正在执行 npm install..."
  if ! (cd "${FRONTEND_DIR}" && npm install); then
    fail "npm install 失败，前端依赖未安装完成。" "检查网络和 npm registry，或手动执行：cd frontend && npm install。"
  fi
}

check_port() {
  local name="$1"
  local port="$2"

  if [ "${AI_TRADE_SKIP_PORT_CHECK:-}" = "1" ]; then
    return
  fi

  local detail
  detail="$("${PYTHON_BIN}" -c 'import socket, sys
name, raw_port = sys.argv[1], sys.argv[2]
try:
    port = int(raw_port)
except ValueError:
    print(f"{name}={raw_port} 不是有效端口。", file=sys.stderr)
    raise SystemExit(1)
if not 1 <= port <= 65535:
    print(f"{name}={port} 超出有效端口范围 1-65535。", file=sys.stderr)
    raise SystemExit(1)
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("127.0.0.1", port))
except OSError:
    print(f"{name}={port} 已被占用（127.0.0.1:{port}）。", file=sys.stderr)
    raise SystemExit(1)
finally:
    sock.close()
' "${name}" "${port}" 2>&1)" || fail "${detail}" "结束占用该端口的进程，或换端口启动：API_PORT=8001 FRONTEND_PORT=5174 ./scripts/run_all.sh。"
}

preflight() {
  info "检查 Python 与 FastAPI 依赖"
  check_python
  info "检查 Node.js/npm 与前端工程"
  check_node
  check_frontend_dependencies
  info "检查端口可用性"
  check_port "API_PORT" "${API_PORT}"
  check_port "FRONTEND_PORT" "${FRONTEND_PORT}"
}

wait_for_port() {
  local port="$1"
  local service="$2"
  local pid="$3"
  local deadline=$((SECONDS + 20))

  while [ "${SECONDS}" -lt "${deadline}" ]; do
    if ! kill -0 "${pid}" 2>/dev/null; then
      wait "${pid}" || true
      fail "${service} 进程提前退出，端口 ${port} 未启动监听。" "先运行 ./scripts/run_all.sh --check 查看依赖问题；若检查通过，再查看上方 ${service} 日志。"
    fi
    if "${PYTHON_BIN}" -c 'import socket, sys
sock = socket.socket()
sock.settimeout(0.2)
try:
    sock.connect(("127.0.0.1", int(sys.argv[1])))
except OSError:
    raise SystemExit(1)
finally:
    sock.close()
' "${port}" >/dev/null 2>&1; then
      return
    fi
    sleep 1
  done

  fail "${service} 在 20 秒内没有监听端口 ${port}。" "查看上方 ${service} 日志；常见原因是依赖安装不完整或端口被启动后抢占。"
}

run_services() {
  trap cleanup EXIT INT TERM
  info "启动 FastAPI：http://127.0.0.1:${API_PORT}"
  "${ROOT_DIR}/scripts/run_api.sh" &
  API_PID=$!
  wait_for_port "${API_PORT}" "FastAPI" "${API_PID}"
  info "FastAPI 已就绪"
  info "启动 React/Vite：http://localhost:${FRONTEND_PORT}"
  info "按 Ctrl+C 可停止前端，并自动清理后端进程"
  (cd "${FRONTEND_DIR}" && npm run dev -- --host 127.0.0.1 --port "${FRONTEND_PORT}")
}

for arg in "$@"; do
  case "${arg}" in
    --check|--preflight)
      MODE="check"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      fail "未知参数：${arg}" "使用 ./scripts/run_all.sh 或 ./scripts/run_all.sh --check。"
      ;;
  esac
done

cd "${ROOT_DIR}"
preflight

if [ "${MODE}" = "check" ]; then
  info "环境和依赖检查通过"
  exit 0
fi

run_services
