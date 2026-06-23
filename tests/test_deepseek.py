from __future__ import annotations

import json

from ai_trade_system.deepseek import DeepSeekClient, DeepSeekConfig, load_deepseek_config


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(self.text)


class FakeSession:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls: list[dict] = []

    def post(self, url: str, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


def test_load_deepseek_config_reads_local_env_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env.local").write_text(
        "\n".join(
            [
                "DEEPSEEK_API_KEY=test-secret",
                "DEEPSEEK_BASE_URL=https://example.deepseek.test",
                "DEEPSEEK_MODEL=deepseek-v4-pro",
            ]
        ),
        encoding="utf-8",
    )

    config = load_deepseek_config()

    assert config.api_key == "test-secret"
    assert config.base_url == "https://example.deepseek.test"
    assert config.model == "deepseek-v4-pro"


def test_deepseek_client_requests_json_chat_completion_without_leaking_key():
    session = FakeSession(
        FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "tools": ["data.update", "radar.scan"],
                                    "summary": "计划已生成",
                                }
                            )
                        }
                    }
                ],
                "usage": {"total_tokens": 42},
            }
        )
    )
    client = DeepSeekClient(
        DeepSeekConfig(api_key="test-secret", base_url="https://api.deepseek.com", model="deepseek-v4-flash"),
        session=session,
    )

    payload = client.chat_json(
        system_prompt="只输出 JSON",
        user_prompt="更新数据并扫描",
        max_tokens=256,
    )

    assert payload["data"]["tools"] == ["data.update", "radar.scan"]
    assert payload["model"] == "deepseek-v4-flash"
    assert payload["usage"]["total_tokens"] == 42
    call = session.calls[0]
    assert call["url"] == "https://api.deepseek.com/chat/completions"
    assert call["headers"]["Authorization"] == "Bearer test-secret"
    assert call["json"]["response_format"] == {"type": "json_object"}
    assert "test-secret" not in json.dumps(payload, ensure_ascii=False)
