from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import requests

from ai_trade_system.config import env_value


DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    model: str = DEFAULT_DEEPSEEK_MODEL
    timeout: float = 60.0

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def load_deepseek_config() -> DeepSeekConfig:
    return DeepSeekConfig(
        api_key=env_value("DEEPSEEK_API_KEY"),
        base_url=(env_value("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL) or DEFAULT_DEEPSEEK_BASE_URL).rstrip("/"),
        model=env_value("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL) or DEFAULT_DEEPSEEK_MODEL,
    )


class DeepSeekClient:
    def __init__(self, config: DeepSeekConfig | None = None, session: Any | None = None):
        self.config = config or load_deepseek_config()
        self.session = session or requests.Session()

    def chat_json(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 1024) -> dict[str, Any]:
        if not self.config.configured:
            return {
                "status": "not_configured",
                "provider": "deepseek",
                "model": self.config.model,
                "summary": "DeepSeek API key is not configured.",
                "data": {},
                "usage": {},
            }

        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
            "max_tokens": max_tokens,
        }
        try:
            response = self.session.post(
                f"{self.config.base_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.api_key}",
                },
                json=body,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("DeepSeek JSON response must be an object")
            return {
                "status": "ok",
                "provider": "deepseek",
                "model": self.config.model,
                "data": data,
                "usage": payload.get("usage", {}),
            }
        except Exception as exc:
            return {
                "status": "failed",
                "provider": "deepseek",
                "model": self.config.model,
                "summary": _safe_error(exc, self.config.api_key),
                "data": {},
                "usage": {},
            }


def _safe_error(exc: Exception, api_key: str | None) -> str:
    message = str(exc)
    if api_key:
        message = message.replace(api_key, "[redacted]")
    return message or exc.__class__.__name__
