from __future__ import annotations

from pathlib import Path

import pytest

from hermes_agent_tools.fleet_sandbox import run_e2b_sandbox, run_kubernetes_sandbox
from hermes_agent_tools.sandbox import resolve_sandbox_backend, run_subprocess_in_sandbox


def test_resolve_sandbox_backend_accepts_fleet_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_SANDBOX_BACKEND", "kubernetes")
    assert resolve_sandbox_backend() == "kubernetes"
    monkeypatch.setenv("HERMES_SANDBOX_BACKEND", "e2b")
    assert resolve_sandbox_backend() == "e2b"


def test_kubernetes_sandbox_unconfigured_fallback(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    if (ws / "ok.txt").exists():
        pass
    else:
        (ws / "ok.txt").write_text("1", encoding="utf-8")
    result = run_kubernetes_sandbox(
        ws,
        ["python", "-c", "print('hi')"],
        timeout_seconds=30.0,
    )
    assert result.backend == "kubernetes"
    assert "k8s-unavailable" in result.stdout or result.returncode == 0


def test_e2b_sandbox_unconfigured_fallback(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    result = run_e2b_sandbox(ws, ["python", "-c", "print(1)"], timeout_seconds=30.0)
    assert result.backend == "e2b"
    assert "e2b-unconfigured" in result.stdout or "e2b-local-fallback" in result.stdout


def test_run_subprocess_routes_kubernetes_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HERMES_SANDBOX_BACKEND", "kubernetes")
    ws = tmp_path / "ws"
    ws.mkdir()
    proc = run_subprocess_in_sandbox(ws, ["python", "-c", "print(2)"], timeout_seconds=30.0)
    assert proc.backend == "kubernetes"
