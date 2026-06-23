from __future__ import annotations

import os
from pathlib import Path

_LOADED_ENV_PATHS: set[Path] = set()


def load_local_env(path: str | Path = ".env.local", *, override: bool = False) -> None:
    """Load simple KEY=VALUE pairs from a local env file if present."""

    env_path = Path(path).resolve()
    if env_path in _LOADED_ENV_PATHS and not override:
        return

    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = _strip_env_value(value.strip())
            if key and (override or key not in os.environ):
                os.environ[key] = value
    _LOADED_ENV_PATHS.add(env_path)


def env_value(name: str, default: str | None = None) -> str | None:
    load_local_env()
    return os.environ.get(name, default)


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
