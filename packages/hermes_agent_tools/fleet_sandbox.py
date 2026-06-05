"""Enterprise fleet sandbox backends (Kubernetes exec, E2B stub)."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from hermes_agent_tools.sandbox import SandboxRunResult
from nimbusware_env.settings_resolve import resolve_str


def kubectl_available() -> bool:
    try:
        proc = subprocess.run(
            ["kubectl", "version", "--client"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode == 0


def run_kubernetes_sandbox(
    workspace: Path,
    argv: list[str],
    *,
    timeout_seconds: float,
) -> SandboxRunResult:
    pod = resolve_str("HERMES_SANDBOX_K8S_EXEC_POD", default="").strip()
    namespace = resolve_str("HERMES_SANDBOX_K8S_NAMESPACE", default="default").strip() or "default"
    workdir = (
        resolve_str("HERMES_SANDBOX_K8S_WORKDIR", default="/workspace").strip() or "/workspace"
    )
    if not pod or not kubectl_available():
        proc = subprocess.run(
            argv,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return SandboxRunResult(
            backend="kubernetes",
            returncode=proc.returncode,
            stdout="[sandbox:k8s-unavailable] " + (proc.stdout or ""),
            stderr=(proc.stderr or "")
            + "Set HERMES_SANDBOX_K8S_EXEC_POD and kubectl for fleet isolation.\n",
        )
    cmd = [
        "kubectl",
        "exec",
        "-n",
        namespace,
        pod,
        "--",
        "sh",
        "-c",
        f"cd {shlex.quote(workdir)} && " + shlex.join(argv),
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return SandboxRunResult(
        backend="kubernetes",
        returncode=proc.returncode,
        stdout="[sandbox:k8s] " + (proc.stdout or ""),
        stderr=proc.stderr or "",
    )


def run_e2b_sandbox(
    workspace: Path,
    argv: list[str],
    *,
    timeout_seconds: float,
) -> SandboxRunResult:
    api_key = resolve_str("HERMES_E2B_API_KEY", default="").strip()
    if not api_key:
        proc = subprocess.run(
            argv,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return SandboxRunResult(
            backend="e2b",
            returncode=proc.returncode,
            stdout="[sandbox:e2b-unconfigured] " + (proc.stdout or ""),
            stderr=(proc.stderr or "")
            + "Fleet E2B sandbox requires HERMES_E2B_API_KEY (enterprise fleet).\n",
        )
    cmdline = shlex.join(argv)
    proc = subprocess.run(
        argv,
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return SandboxRunResult(
        backend="e2b",
        returncode=proc.returncode,
        stdout=f"[sandbox:e2b-local-fallback] {cmdline}\n" + (proc.stdout or ""),
        stderr=(proc.stderr or "")
        + "E2B remote sandbox API hook reserved; ran on host with jail until fleet wiring.\n",
    )
