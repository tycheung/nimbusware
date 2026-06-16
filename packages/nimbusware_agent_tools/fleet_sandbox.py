from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from nimbusware_agent_tools.sandbox import SandboxRunResult
from nimbusware_env.settings_resolve import resolve_str

_E2B_WORKSPACE_ROOT = "/home/user/workspace"
_E2B_MAX_FILE_BYTES = 512_000


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
    pod = resolve_str("NIMBUSWARE_SANDBOX_K8S_EXEC_POD", default="").strip()
    namespace = (
        resolve_str("NIMBUSWARE_SANDBOX_K8S_NAMESPACE", default="default").strip() or "default"
    )
    workdir = (
        resolve_str("NIMBUSWARE_SANDBOX_K8S_WORKDIR", default="/workspace").strip() or "/workspace"
    )
    if not pod or not kubectl_available():
        return SandboxRunResult(
            backend="kubernetes",
            returncode=127,
            stdout="",
            stderr=(
                "Kubernetes sandbox unavailable; refusing to run without pod isolation. "
                "Set NIMBUSWARE_SANDBOX_K8S_EXEC_POD and ensure kubectl is on PATH, "
                "or choose another NIMBUSWARE_SANDBOX_BACKEND.\n"
            ),
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


def _sandbox_unavailable(
    *,
    backend: str,
    stderr_note: str,
) -> SandboxRunResult:
    return SandboxRunResult(
        backend=backend,
        returncode=127,
        stdout="",
        stderr=stderr_note,
    )


def _sync_workspace_to_e2b(sandbox: object, workspace: Path, remote_root: str) -> None:
    files_api = getattr(sandbox, "files", None)
    if files_api is None or not hasattr(files_api, "write"):
        return
    for path in workspace.rglob("*"):
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > _E2B_MAX_FILE_BYTES:
            continue
        rel = path.relative_to(workspace).as_posix()
        remote = f"{remote_root}/{rel}"
        files_api.write(remote, path.read_bytes())


def _run_e2b_remote(
    workspace: Path,
    argv: list[str],
    *,
    timeout_seconds: float,
    api_key: str,
) -> SandboxRunResult:
    import importlib

    sandbox_mod = importlib.import_module("e2b")
    Sandbox = sandbox_mod.Sandbox

    template = resolve_str("NIMBUSWARE_E2B_TEMPLATE", default="").strip() or None
    create_kwargs: dict[str, object] = {}
    if template:
        create_kwargs["template"] = template

    prev_key = os.environ.get("E2B_API_KEY")
    os.environ["E2B_API_KEY"] = api_key
    cmd = shlex.join(argv)
    try:
        with Sandbox.create(**create_kwargs) as sandbox:
            _sync_workspace_to_e2b(sandbox, workspace, _E2B_WORKSPACE_ROOT)
            result = sandbox.commands.run(
                cmd,
                cwd=_E2B_WORKSPACE_ROOT,
                timeout=max(1, int(timeout_seconds)),
            )
            exit_code = int(getattr(result, "exit_code", 0) or 0)
            stdout = getattr(result, "stdout", "") or ""
            stderr = getattr(result, "stderr", "") or ""
            return SandboxRunResult(
                backend="e2b",
                returncode=exit_code,
                stdout="[sandbox:e2b] " + stdout,
                stderr=stderr,
            )
    finally:
        if prev_key is None:
            os.environ.pop("E2B_API_KEY", None)
        else:
            os.environ["E2B_API_KEY"] = prev_key


def run_e2b_sandbox(
    workspace: Path,
    argv: list[str],
    *,
    timeout_seconds: float,
) -> SandboxRunResult:
    api_key = resolve_str("NIMBUSWARE_E2B_API_KEY", default="").strip()
    if not api_key:
        return _sandbox_unavailable(
            backend="e2b",
            stderr_note=("Fleet E2B sandbox requires NIMBUSWARE_E2B_API_KEY (enterprise fleet).\n"),
        )

    try:
        return _run_e2b_remote(
            workspace,
            argv,
            timeout_seconds=timeout_seconds,
            api_key=api_key,
        )
    except ImportError:
        return _sandbox_unavailable(
            backend="e2b",
            stderr_note=("Install optional `e2b` package for remote fleet sandbox execution.\n"),
        )
    except Exception as exc:
        return _sandbox_unavailable(
            backend="e2b",
            stderr_note=f"E2B remote sandbox failed ({exc}); refusing host fallback.\n",
        )
