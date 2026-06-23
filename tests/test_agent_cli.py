from __future__ import annotations

import json
import sys
from pathlib import Path

from ai_trade_system.cli import main


def test_agent_cli_tools_and_task_lifecycle(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AI_TRADE_OPENCLAW_RESEARCH_COMMAND", raising=False)

    monkeypatch.setattr(sys, "argv", ["ai-trade", "agent", "tools", "--json"])
    main()
    tools_payload = json.loads(capsys.readouterr().out)
    assert {tool["name"] for tool in tools_payload["tools"]} >= {"system.snapshot", "agent.report"}

    monkeypatch.setattr(
        sys,
        "argv",
        ["ai-trade", "agent", "run", "帮我研究 000001", "--source", "cli", "--symbol", "000001", "--exchange", "SZSE", "--json"],
    )
    main()
    task_payload = json.loads(capsys.readouterr().out)
    task_id = task_payload["task"]["task_id"]
    assert task_payload["task"]["status"] == "waiting_confirmation"
    assert task_payload["task"]["source"] == "cli"

    monkeypatch.setattr(sys, "argv", ["ai-trade", "agent", "approve", task_id, "--json"])
    main()
    approved_payload = json.loads(capsys.readouterr().out)
    assert approved_payload["task"]["status"] == "completed"

    monkeypatch.setattr(sys, "argv", ["ai-trade", "agent", "list", "--json"])
    main()
    list_payload = json.loads(capsys.readouterr().out)
    assert list_payload["tasks"][0]["task_id"] == task_id

    monkeypatch.setattr(sys, "argv", ["ai-trade", "agent", "show", task_id, "--json"])
    main()
    show_payload = json.loads(capsys.readouterr().out)
    assert show_payload["task"]["prompt"] == "帮我研究 000001"

    monkeypatch.setattr(sys, "argv", ["ai-trade", "agent", "trace", task_id, "--json"])
    main()
    trace_payload = json.loads(capsys.readouterr().out)
    assert trace_payload["task_id"] == task_id
    assert "request_received" in [event["type"] for event in trace_payload["events"]]


def test_agent_cli_blocks_live_trading_prompts(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(sys, "argv", ["ai-trade", "agent", "run", "帮我实盘下单买入 000001", "--source", "weixin", "--json"])
    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["task"]["status"] == "blocked"
    assert payload["task"]["confirmations"][0]["code"] == "LIVE_TRADING_BLOCKED"
