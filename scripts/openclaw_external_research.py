#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any


DEFAULT_SESSION_KEY = "agent:main:ai-trade-system-external-research"


def build_openclaw_message(prompt: str, context: dict[str, Any]) -> str:
    context_json = json.dumps(context, ensure_ascii=False, sort_keys=True)
    return "\n".join(
        [
            "你是 ai_trade_system 的外部信息研究代理。",
            "请基于你可用的信息检索/分析能力，完成基本面、公告、新闻、行业和风险侧摘要。",
            "不要调用 ai_trade_system MCP 工具，避免递归创建任务；不要发送消息；不要下单。",
            "请用中文输出一段紧凑研究摘要，包含信息来源类型、关键证据、风险和不确定性。",
            "如果使用网页检索，请尽量在摘要中保留关键来源名称；上游会从 OpenClaw session 提取 URL 作为证据。",
            "如果无法联网或无法取得外部资料，请明确说明限制，不要编造。",
            "输出应可被上游记录为 JSON 字段 summary 的纯文本。",
            "",
            f"用户任务：{prompt}",
            f"上下文 JSON：{context_json}",
        ]
    )


def parse_openclaw_agent_output(stdout: str) -> dict[str, Any]:
    data = json.loads(stdout)
    payloads = ((data.get("result") or {}).get("payloads")) or []
    summary = "\n".join(str(item.get("text", "")).strip() for item in payloads if str(item.get("text", "")).strip())
    meta = (data.get("result") or {}).get("meta") or {}
    agent_meta = meta.get("agentMeta") or {}
    source = {"type": "openclaw_agent", "run_id": data.get("runId"), "session_file": agent_meta.get("sessionFile")}
    sources = [source]
    sources.extend(_extract_web_search_sources(agent_meta.get("sessionFile")))
    return {
        "status": "ok" if data.get("status") == "ok" else "failed",
        "summary": summary or data.get("summary", ""),
        "sources": sources,
        "confidence": "medium" if data.get("status") == "ok" else "low",
    }


def run_openclaw_agent(message: str) -> dict[str, Any]:
    command = [
        os.environ.get("OPENCLAW_BIN", "openclaw"),
        "agent",
        "--session-key",
        os.environ.get("AI_TRADE_OPENCLAW_SESSION_KEY", DEFAULT_SESSION_KEY),
        "--message",
        message,
        "--json",
        "--timeout",
        os.environ.get("AI_TRADE_OPENCLAW_TIMEOUT", "300"),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return {
            "status": "failed",
            "summary": completed.stderr.strip() or completed.stdout.strip() or "OpenClaw agent command failed",
            "sources": [],
            "confidence": "low",
        }
    try:
        return parse_openclaw_agent_output(completed.stdout)
    except Exception as exc:
        return {
            "status": "failed",
            "summary": f"OpenClaw agent output parse failed: {exc}",
            "sources": [],
            "confidence": "low",
        }


def _extract_web_search_sources(session_file: object) -> list[dict[str, str]]:
    if not isinstance(session_file, str) or not session_file:
        return []
    sources: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    try:
        with open(session_file, encoding="utf-8") as handle:
            lines = handle.readlines()
    except OSError:
        return []

    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        for record in _iter_url_records(event):
            url = str(record.get("url") or "").strip()
            if not url.startswith(("http://", "https://")) or url in seen_urls:
                continue
            seen_urls.add(url)
            source: dict[str, str] = {"type": str(record.get("type") or "session_url"), "url": url}
            title = str(record.get("title") or "").strip()
            site_name = str(record.get("siteName") or record.get("site_name") or "").strip()
            if title:
                source["title"] = title
            if site_name:
                source["site_name"] = site_name
            sources.append(source)
        for text in _iter_text_values(event):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            for result in _iter_search_results(payload):
                url = str(result.get("url") or "").strip()
                if not url.startswith(("http://", "https://")) or url in seen_urls:
                    continue
                seen_urls.add(url)
                source: dict[str, str] = {"type": "web_search", "url": url}
                title = str(result.get("title") or "").strip()
                site_name = str(result.get("siteName") or result.get("site_name") or "").strip()
                if title:
                    source["title"] = title
                if site_name:
                    source["site_name"] = site_name
                sources.append(source)
    return sources


def _iter_url_records(value: Any):
    if isinstance(value, dict):
        if isinstance(value.get("url"), str):
            yield value
        for item in value.values():
            yield from _iter_url_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_url_records(item)


def _iter_text_values(value: Any):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "text" and isinstance(item, str):
                yield item
            else:
                yield from _iter_text_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_text_values(item)


def _iter_search_results(value: Any):
    if isinstance(value, dict):
        results = value.get("results")
        if isinstance(results, list):
            for item in results:
                if isinstance(item, dict):
                    yield item
        for item in value.values():
            yield from _iter_search_results(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_search_results(item)


def main() -> int:
    try:
        request = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "failed", "summary": f"Invalid JSON input: {exc}", "sources": [], "confidence": "low"}, ensure_ascii=False))
        return 1
    prompt = str(request.get("prompt") or "")
    context = request.get("context") if isinstance(request.get("context"), dict) else {}
    payload = run_openclaw_agent(build_openclaw_message(prompt, context))
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
