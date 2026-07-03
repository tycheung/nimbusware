from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.dev_env_session import load_session


def tail_dev_env_logs(workspace: Path, *, max_chars: int = 4000) -> dict[str, str]:
    ws = workspace.resolve()
    session = load_session(ws)
    artifacts = ws / ".nimbusware" / "put_artifacts"
    stdout = ""
    stderr = ""
    manifest_path = artifacts / "manifest.json"
    if manifest_path.is_file():
        import json

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(manifest, dict):
                stdout = str(manifest.get("stdout_tail") or "")[-max_chars:]
                stderr = str(manifest.get("stderr_tail") or "")[-max_chars:]
        except (OSError, json.JSONDecodeError):
            pass
    for name, target in (("stdout.log", stdout), ("stderr.log", stderr)):
        path = artifacts / name
        if path.is_file() and not target:
            try:
                if name == "stdout.log":
                    stdout = path.read_text(encoding="utf-8", errors="replace")[-max_chars:]
                else:
                    stderr = path.read_text(encoding="utf-8", errors="replace")[-max_chars:]
            except OSError:
                pass
    base_url = session.base_url if session else ""
    return {
        "stdout_tail": stdout,
        "stderr_tail": stderr,
        "base_url": base_url,
        "health": session.health if session else "unknown",
    }


def dev_env_theater_excerpt(workspace: Path) -> dict[str, Any]:
    logs = tail_dev_env_logs(workspace)
    headline = "Dev environment healthy"
    if logs.get("stderr_tail"):
        headline = "Dev environment stderr tail available"
    return {
        "headline": headline,
        "logs": logs,
    }
