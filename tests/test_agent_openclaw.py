from __future__ import annotations

import json
import sys

from ai_trade_system.agent.models import AgentStep, AgentTask
from ai_trade_system.agent.openclaw import OpenClawConnector
from scripts.openclaw_notify_user import build_openclaw_command


def test_openclaw_connector_sends_task_notification_command(tmp_path):
    output_path = tmp_path / "notification.json"
    script_path = tmp_path / "capture_notification.py"
    script_path.write_text(
        """
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")
""".strip(),
        encoding="utf-8",
    )
    connector = OpenClawConnector(command="", notify_command=f"{sys.executable} {script_path} {output_path}")
    task = AgentTask(
        task_id="agt_notify",
        source="weixin",
        prompt="这周的股票扫描分析结论输出给我",
        status="completed",
        result_summary="已准备微信分享结果。",
        report_path="data/agent/reports/agt_notify.json",
    )
    task.steps.append(
        AgentStep(
            tool_name="share.weixin",
            title="准备微信分享文本",
            status="completed",
            summary="微信分享文本已准备。",
            output={"message": "完整微信分享文本\n1. 中芯国际：扫描与研究结论"},
        )
    )

    result = connector.notify_task(task)

    assert result["status"] == "ok"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["task"]["task_id"] == "agt_notify"
    assert payload["task"]["status"] == "completed"
    assert payload["message"] == "完整微信分享文本\n1. 中芯国际：扫描与研究结论"
    assert payload["report_path"] == "data/agent/reports/agt_notify.json"


def test_openclaw_connector_research_command_uses_current_python_when_path_has_no_python(monkeypatch, tmp_path):
    monkeypatch.setenv("PATH", "")
    script_path = tmp_path / "capture_research.py"
    script_path.write_text(
        """
import json
import sys

payload = json.loads(sys.stdin.read())
print(json.dumps({
    "status": "ok",
    "summary": f"研究完成：{payload['context']['symbol']}",
    "sources": ["fixture"],
    "confidence": "high",
}, ensure_ascii=False))
""".strip(),
        encoding="utf-8",
    )
    connector = OpenClawConnector(command=f"python {script_path}", notify_command="")

    result = connector.research("请研究候选股", {"symbol": "688733"})

    assert result == {
        "status": "ok",
        "summary": "研究完成：688733",
        "sources": ["fixture"],
        "confidence": "high",
    }


def test_openclaw_connector_notify_command_uses_current_python_when_path_has_no_python(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("PATH", "")
    output_path = tmp_path / "notification.json"
    script_path = tmp_path / "capture_notification.py"
    script_path.write_text(
        """
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")
""".strip(),
        encoding="utf-8",
    )
    connector = OpenClawConnector(command="", notify_command=f"python {script_path} {output_path}")
    task = AgentTask(
        task_id="agt_notify_python",
        source="weixin",
        prompt="这周的股票扫描分析结论输出给我",
        status="completed",
        result_summary="已准备微信分享结果。",
    )

    result = connector.notify_task(task)

    assert result["status"] == "ok"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["task_id"] == "agt_notify_python"
    assert payload["status"] == "completed"


def test_openclaw_connector_sends_direct_message_notification_context(tmp_path):
    output_path = tmp_path / "direct_notification.json"
    script_path = tmp_path / "capture_direct_notification.py"
    script_path.write_text(
        """
from pathlib import Path
import sys

Path(sys.argv[1]).write_text(sys.stdin.read(), encoding="utf-8")
""".strip(),
        encoding="utf-8",
    )
    connector = OpenClawConnector(command="", notify_command=f"{sys.executable} {script_path} {output_path}")

    result = connector.notify_message(
        "周报正文",
        {"source": "feishu", "reply_channel": "openclaw-feishu", "weekly_analysis_run_id": "analysis-2026-W25"},
    )

    assert result["status"] == "ok"
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["message"] == "周报正文"
    assert payload["task_id"] == "analysis-2026-W25"
    assert payload["task"]["context"]["reply_channel"] == "openclaw-feishu"


def test_openclaw_notify_user_builds_delivery_command(monkeypatch):
    monkeypatch.setenv("OPENCLAW_BIN", "/usr/local/bin/openclaw")
    payload = {
        "message": "最终分享文本",
        "task_id": "agt_delivery",
        "status": "completed",
        "task": {
            "context": {
                "reply_channel": "openclaw-weixin",
                "reply_to": "wx_user",
                "session_key": "agent:main:wechat-session",
            }
        },
    }

    command = build_openclaw_command(payload)

    assert command[:4] == ["/usr/local/bin/openclaw", "agent", "--agent", "main"]
    assert "--deliver" in command
    assert "最终分享文本" in command[command.index("--message") + 1]
    assert command[command.index("--reply-channel") + 1] == "openclaw-weixin"
    assert command[command.index("--reply-to") + 1] == "wx_user"
    assert command[command.index("--session-key") + 1] == "agent:main:wechat-session"
