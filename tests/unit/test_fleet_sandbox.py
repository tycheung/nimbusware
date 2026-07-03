from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from agent_tools.fleet_sandbox import run_e2b_sandbox, run_kubernetes_sandbox
from agent_tools.sandbox import resolve_sandbox_backend, run_subprocess_in_sandbox


def test_resolve_sandbox_backend_accepts_fleet_backends(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SANDBOX_BACKEND", "kubernetes")
    assert resolve_sandbox_backend() == "kubernetes"
    monkeypatch.setenv("NIMBUSWARE_SANDBOX_BACKEND", "e2b")
    assert resolve_sandbox_backend() == "e2b"


def test_kubernetes_sandbox_unconfigured_fails_closed(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    result = run_kubernetes_sandbox(
        ws,
        ["python", "-c", "print('hi')"],
        timeout_seconds=30.0,
    )
    assert result.backend == "kubernetes"
    assert result.returncode == 127
    assert "refusing to run without pod isolation" in result.stderr


def test_e2b_sandbox_unconfigured_fails_closed(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    result = run_e2b_sandbox(ws, ["python", "-c", "print(1)"], timeout_seconds=30.0)
    assert result.backend == "e2b"
    assert result.returncode == 127
    assert "NIMBUSWARE_E2B_API_KEY" in result.stderr


def test_e2b_sandbox_remote_when_key_and_sdk_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "main.py").write_text("print('ok')\n", encoding="utf-8")
    monkeypatch.setenv("NIMBUSWARE_E2B_API_KEY", "e2b_test_key")

    class FakeResult:
        exit_code = 0
        stdout = "remote ok"
        stderr = ""

    class FakeCommands:
        def run(self, cmd: str, *, cwd: str | None = None, timeout: int | None = None):
            assert "python" in cmd
            assert cwd == "/home/user/workspace"
            return FakeResult()

    class FakeFiles:
        def write(self, path: str, content: bytes) -> None:
            assert path.startswith("/home/user/workspace/")

    class FakeSandbox:
        commands = FakeCommands()
        files = FakeFiles()

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    class FakeSandboxClass:
        @staticmethod
        def create(**_kwargs: object) -> FakeSandbox:
            return FakeSandbox()

    fake_e2b = types.ModuleType("e2b")
    fake_e2b.Sandbox = FakeSandboxClass  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "e2b", fake_e2b)

    result = run_e2b_sandbox(ws, ["python", "-c", "print(1)"], timeout_seconds=30.0)
    assert result.backend == "e2b"
    assert "[sandbox:e2b]" in result.stdout
    assert "remote ok" in result.stdout
    assert "e2b-local-fallback" not in result.stdout


def test_e2b_sandbox_import_missing_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("NIMBUSWARE_E2B_API_KEY", "e2b_test_key")
    monkeypatch.delitem(sys.modules, "e2b", raising=False)

    result = run_e2b_sandbox(ws, ["python", "-c", "print(9)"], timeout_seconds=30.0)
    assert result.backend == "e2b"
    assert result.returncode == 127
    assert "e2b" in result.stderr.lower()


def test_run_subprocess_routes_kubernetes_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_SANDBOX_BACKEND", "kubernetes")
    ws = tmp_path / "ws"
    ws.mkdir()
    proc = run_subprocess_in_sandbox(ws, ["python", "-c", "print(2)"], timeout_seconds=30.0)
    assert proc.backend == "kubernetes"
