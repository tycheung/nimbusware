from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

VALID_BACKENDS = frozenset({"none", "stub", "docker", "kubernetes", "e2b"})
DEFAULT_DOCKER_IMAGE = "python:3.11-slim"


@dataclass(frozen=True)
class SandboxRunResult:
    backend: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def combined_output(self) -> str:
        return (self.stdout or "") + (self.stderr or "")


def resolve_sandbox_backend() -> str:
    raw = os.environ.get("HERMES_SANDBOX_BACKEND", "none").strip().lower()
    if raw not in VALID_BACKENDS:
        return "none"
    return raw


def resolve_sandbox_docker_image() -> str:
    raw = os.environ.get("HERMES_SANDBOX_DOCKER_IMAGE", DEFAULT_DOCKER_IMAGE).strip()
    return raw or DEFAULT_DOCKER_IMAGE


def docker_cli_available() -> bool:
    try:
        proc = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def build_docker_run_argv(workspace: Path, argv: list[str], *, image: str) -> list[str]:
    ws = workspace.resolve()
    return [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "-v",
        f"{ws}:/workspace",
        "-w",
        "/workspace",
        image,
        *argv,
    ]


def run_subprocess_in_sandbox(
    workspace: Path,
    argv: list[str],
    *,
    timeout_seconds: float,
    backend: str | None = None,
) -> SandboxRunResult:
    chosen = backend or resolve_sandbox_backend()
    if chosen not in VALID_BACKENDS:
        chosen = "none"

    if chosen == "kubernetes":
        from hermes_agent_tools.fleet_sandbox import run_kubernetes_sandbox

        return run_kubernetes_sandbox(workspace, argv, timeout_seconds=timeout_seconds)

    if chosen == "e2b":
        from hermes_agent_tools.fleet_sandbox import run_e2b_sandbox

        return run_e2b_sandbox(workspace, argv, timeout_seconds=timeout_seconds)

    if chosen == "docker":
        if not docker_cli_available():
            proc = subprocess.run(
                argv,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            note = "[sandbox:docker-unavailable] "
            return SandboxRunResult(
                backend="docker",
                returncode=proc.returncode,
                stdout=note + (proc.stdout or ""),
                stderr=(proc.stderr or "")
                + "Docker CLI unavailable; ran without container isolation.\n",
            )
        image = resolve_sandbox_docker_image()
        docker_argv = build_docker_run_argv(workspace, argv, image=image)
        proc = subprocess.run(
            docker_argv,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        prefix = "[sandbox:docker] "
        return SandboxRunResult(
            backend="docker",
            returncode=proc.returncode,
            stdout=prefix + (proc.stdout or ""),
            stderr=proc.stderr or "",
        )

    proc = subprocess.run(
        argv,
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    prefix = f"[sandbox:{chosen}] " if chosen != "none" else ""
    return SandboxRunResult(
        backend=chosen,
        returncode=proc.returncode,
        stdout=prefix + (proc.stdout or ""),
        stderr=proc.stderr or "",
    )
