from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nimbusware_agent_tools.sandbox import (
    build_docker_run_argv,
    docker_cli_available,
    resolve_sandbox_backend,
    resolve_sandbox_docker_image,
    run_subprocess_in_sandbox,
)
from nimbusware_agent_tools.tools import tool_run_shell


def test_resolve_sandbox_backend_defaults_none(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SANDBOX_BACKEND", raising=False)
    assert resolve_sandbox_backend() == "none"


def test_resolve_sandbox_backend_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SANDBOX_BACKEND", "docker")
    assert resolve_sandbox_backend() == "docker"


def test_resolve_sandbox_docker_image_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_SANDBOX_DOCKER_IMAGE", raising=False)
    assert resolve_sandbox_docker_image() == "python:3.11-slim"


def test_build_docker_run_argv(tmp_path: Path) -> None:
    argv = build_docker_run_argv(tmp_path, ["python", "-c", "print(1)"], image="alpine")
    assert argv[0:2] == ["docker", "run"]
    assert "--network" in argv
    assert "none" in argv
    assert f"{tmp_path.resolve()}:/workspace" in argv
    assert "alpine" in argv
    assert argv[-3:] == ["python", "-c", "print(1)"]


def test_docker_unavailable_falls_back_local(tmp_path: Path) -> None:
    with patch("nimbusware_agent_tools.sandbox.docker_cli_available", return_value=False):
        with patch("nimbusware_agent_tools.sandbox.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
            result = run_subprocess_in_sandbox(
                tmp_path,
                ["python", "-c", "print(1)"],
                timeout_seconds=30.0,
                backend="docker",
            )
    assert result.backend == "docker"
    assert "[sandbox:docker-unavailable]" in result.stdout
    assert "Docker CLI unavailable" in result.stderr
    mock_run.assert_called_once()
    assert mock_run.call_args.kwargs.get("cwd") == tmp_path


def test_docker_backend_invokes_container(tmp_path: Path) -> None:
    with patch("nimbusware_agent_tools.sandbox.docker_cli_available", return_value=True):
        with patch("nimbusware_agent_tools.sandbox.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
            result = run_subprocess_in_sandbox(
                tmp_path,
                ["python", "-c", "print(1)"],
                timeout_seconds=30.0,
                backend="docker",
            )
    assert result.backend == "docker"
    assert "[sandbox:docker]" in result.stdout
    docker_argv = mock_run.call_args.args[0]
    assert docker_argv[0] == "docker"
    assert docker_argv[1] == "run"


def test_stub_backend_tags_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_SANDBOX_BACKEND", "stub")
    if Path("python").exists() or Path("python3").exists():
        result = tool_run_shell(tmp_path, "python", ["-c", "print('ok')"])
        assert "[sandbox:stub]" in result.output or result.ok


def test_run_subprocess_in_sandbox_none_prefix(tmp_path: Path) -> None:
    proc = run_subprocess_in_sandbox(
        tmp_path,
        ["python", "-c", "print(1)"],
        timeout_seconds=30.0,
        backend="none",
    )
    assert proc.backend == "none"
    assert not proc.stdout.startswith("[sandbox:")


def test_docker_cli_available_false_on_missing_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "nimbusware_agent_tools.sandbox.subprocess.run",
        MagicMock(side_effect=FileNotFoundError),
    )
    assert docker_cli_available() is False
