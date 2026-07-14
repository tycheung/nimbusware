from __future__ import annotations

from pathlib import Path

import pytest

from env.run_app import start_servers


def test_start_servers_rejects_default_admin_token_on_public_bind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    with pytest.raises(RuntimeError, match="dev default"):
        start_servers(root=tmp_path, api_host="0.0.0.0", api_port=18000)


def test_start_servers_sets_nimbusware_api_port(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "integration-test-token")
    monkeypatch.delenv("NIMBUSWARE_API_PORT", raising=False)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))

    spawned: list[list[str]] = []

    def _fake_spawn(cmd: list[str], *, cwd: Path, env: dict[str, str]):  # type: ignore[no-untyped-def]
        spawned.append(cmd)
        assert env.get("NIMBUSWARE_API_PORT")
        assert env.get("PORT") == env["NIMBUSWARE_API_PORT"]

        class _Proc:
            returncode = None

            def poll(self) -> None:
                return None

            def wait(self, timeout: float | None = None) -> None:
                return None

            def kill(self) -> None:
                return None

        return _Proc()

    monkeypatch.setattr("env.run_app._spawn", _fake_spawn)
    monkeypatch.setattr("env.run_app._wait_for_http", lambda url, timeout_seconds=120.0: None)
    monkeypatch.setattr("env.run_app._pick_free_port", lambda host: 34567)

    console_url, api_url, env = start_servers(root=tmp_path, api_host="127.0.0.1")
    assert env["NIMBUSWARE_API_PORT"] == "34567"
    assert "34567" in api_url
    assert "34567" in console_url
    assert spawned
