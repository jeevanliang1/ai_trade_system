from __future__ import annotations

import json
import shlex
import subprocess
import sys
from typing import Any

from ai_trade_system.config import env_value


class OpenClawConnector:
    """Connector boundary for OpenClaw-driven external research."""

    def __init__(self, command: str | None = None, notify_command: str | None = None):
        self.command = _portable_python_command(
            command if command is not None else env_value("AI_TRADE_OPENCLAW_RESEARCH_COMMAND")
        )
        self.notify_command = _portable_python_command(
            notify_command if notify_command is not None else env_value("AI_TRADE_OPENCLAW_NOTIFY_COMMAND")
        )

    def research(self, prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        symbol = context.get("symbol") or "未指定"
        if not self.command:
            return {
                "status": "not_configured",
                "summary": f"OpenClaw 外部研究连接尚未配置；已记录 {symbol} 的外部资料待获取状态。",
                "sources": [],
                "confidence": "pending",
            }

        request = json.dumps({"prompt": prompt, "context": context}, ensure_ascii=False)
        completed = subprocess.run(
            self.command,
            input=request,
            text=True,
            shell=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return {
                "status": "failed",
                "summary": completed.stderr.strip() or "OpenClaw command failed",
                "sources": [],
                "confidence": "low",
            }
        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError:
            payload = {"summary": completed.stdout.strip(), "sources": []}
        return {
            "status": payload.get("status", "ok"),
            "summary": payload.get("summary", ""),
            "sources": payload.get("sources", []),
            "confidence": payload.get("confidence", "medium"),
        }

    def notify_task(self, task: Any) -> dict[str, Any]:
        task_payload = task.as_dict() if hasattr(task, "as_dict") else dict(task)
        message = self._task_notification_message(task_payload)
        report_path = task_payload.get("report_path")
        if not self.notify_command:
            return {
                "status": "not_configured",
                "summary": "OpenClaw 完成通知命令尚未配置；任务结果已保留在系统 Trace 和报告中。",
                "message": message,
            }

        request = json.dumps(
            {
                "message": message,
                "task_id": task_payload.get("task_id"),
                "status": task_payload.get("status"),
                "source": task_payload.get("source"),
                "prompt": task_payload.get("prompt"),
                "report_path": report_path,
                "task": task_payload,
            },
            ensure_ascii=False,
        )
        completed = subprocess.run(
            self.notify_command,
            input=request,
            text=True,
            shell=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return {
                "status": "failed",
                "summary": completed.stderr.strip() or "OpenClaw notification command failed",
                "message": message,
            }
        try:
            payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
        except json.JSONDecodeError:
            payload = {"summary": completed.stdout.strip()}
        return {
            "status": payload.get("status", "ok"),
            "summary": payload.get("summary", "OpenClaw 完成通知已提交。"),
            "message": payload.get("message", message),
        }

    def notify_message(self, message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        clean_message = str(message or "").strip()
        if not clean_message:
            return {"status": "failed", "summary": "通知内容为空。", "message": ""}
        if not self.notify_command:
            return {
                "status": "not_configured",
                "summary": "OpenClaw 完成通知命令尚未配置；周报已保存在本地缓存中。",
                "message": clean_message,
            }
        request = json.dumps(
            {
                "message": clean_message,
                "task_id": (context or {}).get("weekly_analysis_run_id"),
                "status": "completed",
                "source": (context or {}).get("source"),
                "prompt": "weekly_scan_deep_analysis",
                "task": {"context": context or {}},
            },
            ensure_ascii=False,
        )
        completed = subprocess.run(
            self.notify_command,
            input=request,
            text=True,
            shell=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            return {
                "status": "failed",
                "summary": completed.stderr.strip() or "OpenClaw notification command failed",
                "message": clean_message,
            }
        try:
            payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
        except json.JSONDecodeError:
            payload = {"summary": completed.stdout.strip()}
        return {
            "status": payload.get("status", "ok"),
            "summary": payload.get("summary", "OpenClaw 完成通知已提交。"),
            "message": payload.get("message", clean_message),
        }

    def _task_notification_message(self, task_payload: dict[str, Any]) -> str:
        share_message = self._share_message(task_payload)
        if share_message:
            return share_message
        status = task_payload.get("status") or "unknown"
        summary = task_payload.get("result_summary") or "任务状态已更新。"
        if status == "waiting_confirmation":
            prefix = "AI交易系统任务需要确认"
        elif status == "completed":
            prefix = "AI交易系统任务已完成"
        elif status == "failed":
            prefix = "AI交易系统任务失败"
        elif status == "blocked":
            prefix = "AI交易系统任务已阻断"
        else:
            prefix = "AI交易系统任务状态更新"
        report_path = task_payload.get("report_path")
        suffix = f"\n报告路径：{report_path}" if report_path else ""
        return f"{prefix}：{summary}{suffix}"

    def _share_message(self, task_payload: dict[str, Any]) -> str | None:
        for step in reversed(task_payload.get("steps", [])):
            if step.get("tool_name") != "share.weixin":
                continue
            output = step.get("output") if isinstance(step.get("output"), dict) else {}
            message = str(output.get("message") or "").strip()
            if message:
                return message
        return None


def _portable_python_command(command: str | None) -> str | None:
    if not command:
        return command
    try:
        parts = shlex.split(command)
    except ValueError:
        return command
    if parts and parts[0] == "python":
        parts[0] = sys.executable
        return shlex.join(parts)
    return command
