from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
RUN_ALL = ROOT_DIR / "scripts" / "run_all.sh"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_check(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", str(RUN_ALL), "--check"],
        cwd=ROOT_DIR,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def _base_env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PATH": str(tmp_path),
            "AI_TRADE_SKIP_PORT_CHECK": "1",
        }
    )
    return env


def test_run_all_check_reports_missing_npm_with_recommended_fix(tmp_path: Path) -> None:
    python = tmp_path / "python"
    _write_executable(python, "#!/bin/bash\nexit 0\n")
    _write_executable(tmp_path / "node", "#!/bin/bash\necho v20.0.0\n")

    env = _base_env(tmp_path)
    env["AI_TRADE_PYTHON"] = str(python)

    result = _run_check(env)

    assert result.returncode == 1
    assert "原因：未找到 npm，无法安装或启动 Vite 前端。" in result.stdout
    assert "建议：安装 Node.js 20 LTS 或更高版本" in result.stdout


def test_run_all_check_reports_missing_python_api_dependencies(tmp_path: Path) -> None:
    python = tmp_path / "python"
    _write_executable(
        python,
        """#!/bin/bash
if [[ "$*" == *"fastapi"* || "$*" == *"ai_trade_system.api.app"* ]]; then
  echo "No module named fastapi" >&2
  exit 1
fi
exit 0
""",
    )
    _write_executable(tmp_path / "node", "#!/bin/bash\necho v20.0.0\n")
    _write_executable(tmp_path / "npm", "#!/bin/bash\necho 10.0.0\n")

    env = _base_env(tmp_path)
    env["AI_TRADE_PYTHON"] = str(python)

    result = _run_check(env)

    assert result.returncode == 1
    assert "原因：Python API 依赖不可用" in result.stdout
    assert '建议：在项目根目录执行：python -m pip install -e ".[api,data]"' in result.stdout


def test_run_app_delegates_to_run_all() -> None:
    run_app = (ROOT_DIR / "scripts" / "run_app.sh").read_text(encoding="utf-8")

    assert "run_all.sh" in run_app


def test_vite_proxy_uses_api_port_environment() -> None:
    vite_config = (ROOT_DIR / "frontend" / "vite.config.ts").read_text(encoding="utf-8")

    assert "process.env.API_PORT" in vite_config
