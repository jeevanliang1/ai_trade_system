from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_script_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "openclaw_external_research.py"
    spec = importlib.util.spec_from_file_location("openclaw_external_research", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_openclaw_message_includes_prompt_context_and_no_recursion_rule():
    module = _load_script_module()

    message = module.build_openclaw_message("研究 000001 基本面", {"symbol": "000001", "exchange": "SZSE"})

    assert "研究 000001 基本面" in message
    assert "000001" in message
    assert "不要调用 ai_trade_system MCP" in message
    assert "JSON" in message


def test_parse_openclaw_agent_output_returns_research_payload():
    module = _load_script_module()
    raw = json.dumps(
        {
            "runId": "run-1",
            "status": "ok",
            "result": {
                "payloads": [{"text": "基本面摘要"}],
                "meta": {"agentMeta": {"sessionFile": "/tmp/session.jsonl"}},
            },
        }
    )

    payload = module.parse_openclaw_agent_output(raw)

    assert payload["status"] == "ok"
    assert payload["summary"] == "基本面摘要"
    assert payload["confidence"] == "medium"
    assert payload["sources"] == [{"type": "openclaw_agent", "run_id": "run-1", "session_file": "/tmp/session.jsonl"}]


def test_parse_openclaw_agent_output_extracts_web_search_sources_from_session_file(tmp_path: Path):
    module = _load_script_module()
    session_file = tmp_path / "session.jsonl"
    lines = [
        json.dumps({"type": "message", "message": {"role": "assistant", "content": [{"type": "toolCall", "name": "web_search"}]}}, ensure_ascii=False),
        json.dumps(
            {
                "type": "message",
                "message": {
                    "role": "tool",
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "results": [
                                        {
                                            "title": "中芯国际公告",
                                            "url": "https://example.com/688981/report",
                                            "siteName": "example.com",
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
    ]
    session_file.write_text("\n".join(lines), encoding="utf-8")
    raw = json.dumps(
        {
            "runId": "run-1",
            "status": "ok",
            "result": {
                "payloads": [{"text": "基本面摘要"}],
                "meta": {"agentMeta": {"sessionFile": session_file.as_posix()}},
            },
        }
    )

    payload = module.parse_openclaw_agent_output(raw)

    assert {
        "type": "web_search",
        "title": "中芯国际公告",
        "url": "https://example.com/688981/report",
        "site_name": "example.com",
    } in payload["sources"]


def test_parse_openclaw_agent_output_extracts_direct_session_url_sources(tmp_path: Path):
    module = _load_script_module()
    session_file = tmp_path / "session.jsonl"
    session_file.write_text(
        json.dumps(
            {
                "type": "message",
                "message": {
                    "content": [
                        {
                            "type": "browser_page",
                            "title": "中芯国际投资者关系",
                            "url": "https://example.com/investor/688981",
                        }
                    ]
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    raw = json.dumps(
        {
            "runId": "run-1",
            "status": "ok",
            "result": {
                "payloads": [{"text": "基本面摘要"}],
                "meta": {"agentMeta": {"sessionFile": session_file.as_posix()}},
            },
        }
    )

    payload = module.parse_openclaw_agent_output(raw)

    assert {
        "type": "browser_page",
        "title": "中芯国际投资者关系",
        "url": "https://example.com/investor/688981",
    } in payload["sources"]
