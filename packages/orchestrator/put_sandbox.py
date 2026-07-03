from __future__ import annotations

import shutil
from collections.abc import Sequence

from env.env_flags import env_str


def put_sandbox_mode() -> str:
    return env_str("NIMBUSWARE_PUT_SANDBOX").strip().lower()


def docker_available() -> bool:
    return shutil.which("docker") is not None


def wrap_put_preview_command(command: Sequence[str], *, port: int, workspace: str) -> list[str]:
    """Wrap local PUT preview command in Docker when NIMBUSWARE_PUT_SANDBOX=docker."""
    if put_sandbox_mode() != "docker" or not docker_available():
        return list(command)
    ws = workspace.replace("\\", "/")
    inner = " ".join(command)
    return [
        "docker",
        "run",
        "--rm",
        "-p",
        f"{port}:{port}",
        "-v",
        f"{ws}:/workspace",
        "-w",
        "/workspace",
        "python:3.11-slim",
        "bash",
        "-lc",
        inner,
    ]
