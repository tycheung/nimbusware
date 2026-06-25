from __future__ import annotations

import subprocess
from pathlib import Path


def install_workspace_precommit(workspace: Path) -> dict[str, object]:
    root = workspace.resolve()
    if not root.is_dir():
        raise ValueError(f"workspace is not a directory: {root}")
    config = root / ".pre-commit-config.yaml"
    if not config.is_file():
        config.write_text(
            "repos:\n"
            "  - repo: https://github.com/astral-sh/ruff-pre-commit\n"
            "    rev: v0.9.6\n"
            "    hooks:\n"
            "      - id: ruff\n"
            "      - id: ruff-format\n",
            encoding="utf-8",
        )
    try:
        proc = subprocess.run(
            ["pre-commit", "install"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return {
            "workspace": str(root),
            "config_path": str(config),
            "installed": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[:500],
            "stderr": (proc.stderr or "")[:500],
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "workspace": str(root),
            "config_path": str(config),
            "installed": False,
            "error": str(exc)[:200],
        }
