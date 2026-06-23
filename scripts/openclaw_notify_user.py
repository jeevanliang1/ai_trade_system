#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


def build_openclaw_command(payload: dict[str, Any]) -> list[str]:
    task = payload.get("task") if isinstance(payload.get("task"), dict) else {}
    context = task.get("context") if isinstance(task.get("context"), dict) else {}
    message = str(payload.get("message") or "").strip()
    if not message:
        message = f"AI交易系统任务 {payload.get('task_id', '')} 状态：{payload.get('status', 'unknown')}"

    command = [
        os.environ.get("OPENCLAW_BIN", "openclaw"),
        "agent",
        "--agent",
        str(context.get("openclaw_agent") or os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_AGENT", "main")),
        "--message",
        build_delivery_prompt(message, payload),
        "--deliver",
        "--json",
        "--timeout",
        os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_TIMEOUT", "300"),
    ]
    optional_args = {
        "--reply-channel": context.get("reply_channel") or os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_REPLY_CHANNEL"),
        "--reply-to": context.get("reply_to") or os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_REPLY_TO"),
        "--reply-account": context.get("reply_account") or os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_REPLY_ACCOUNT"),
        "--session-id": context.get("session_id") or os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_SESSION_ID"),
        "--session-key": context.get("session_key") or os.environ.get("AI_TRADE_OPENCLAW_NOTIFY_SESSION_KEY"),
    }
    for flag, value in optional_args.items():
        if value:
            command.extend([flag, str(value)])
    return command


def build_delivery_prompt(message: str, payload: dict[str, Any]) -> str:
    task_id = payload.get("task_id") or "unknown"
    status = payload.get("status") or "unknown"
    return "\n".join(
        [
            "你是 OpenClaw 的消息投递代理。",
            "请把下面的 AI交易系统结果原样发送给用户，不要调用 ai_trade_system MCP 工具，不要继续分析，不要下单。",
            f"task_id={task_id} status={status}",
            "",
            message,
        ]
    )


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "failed", "summary": f"Invalid JSON input: {exc}"}, ensure_ascii=False))
        return 1

    command = build_openclaw_command(payload)
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        print(
            json.dumps(
                {"status": "failed", "summary": completed.stderr.strip() or completed.stdout.strip() or "OpenClaw delivery failed"},
                ensure_ascii=False,
            )
        )
        return 1
    try:
        data = json.loads(completed.stdout) if completed.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {"summary": completed.stdout.strip()}
    print(json.dumps({"status": data.get("status", "ok"), "summary": data.get("summary", "OpenClaw delivery submitted")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
