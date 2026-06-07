"""Integration adapter scaffold tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nimbusware_orchestrator.integration_adapter_scaffold import (
    execute_target_adapter_integration,
    probe_http_endpoint,
    validate_integration_manifest,
)


def test_validate_integration_manifest_rejects_stub_only() -> None:
    errs = validate_integration_manifest(
        {
            "run_id": "r1",
            "target_adapter_kind": "api_bridge",
            "stub_only": True,
        },
    )
    assert any("stub_only" in e for e in errs)


def test_execute_target_adapter_integration_manifest_invalid(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text("{not-json", encoding="utf-8")
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "manifest_invalid"


def test_execute_target_adapter_integration_manifest_rejected(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps(
            {
                "run_id": "r1",
                "target_adapter_kind": "api_bridge",
                "stub_only": True,
            },
        ),
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "manifest_rejected"
    assert out.get("validation_errors")


def test_execute_target_adapter_integration_rolled_back_on_sync_error(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps({"run_id": "r1", "target_adapter_kind": "api_bridge", "stub_only": False}),
        encoding="utf-8",
    )
    (ws / "target_state.json").write_text('{"connected": true, "prior": 1}\n', encoding="utf-8")
    (ws / "adapter_api_bridge.py").write_text(
        """
class ApiBridgeAdapter:
    kind = "api_bridge"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
    def connect(self):
        return True
    def sync_target(self):
        raise RuntimeError("sync failed")
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "rolled_back"
    assert "sync failed" in str(out.get("rollback_reason", ""))
    restored = json.loads((ws / "target_state.json").read_text(encoding="utf-8"))
    assert restored.get("prior") == 1


def test_execute_target_adapter_integration_rolled_back_on_connect_fail(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "adapter_api_bridge.py").write_text(
        """
class ApiBridgeAdapter:
    kind = "api_bridge"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
    def connect(self):
        return False
    def sync_target(self):
        path = self._workspace_dir / "target_state.json"
        path.write_text('{"connected": false}', encoding="utf-8")
        return {"ok": True}
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "rolled_back"
    assert out.get("rollback_reason") == "connect_failed_after_sync"


def test_execute_target_adapter_integration_api_bridge_integrated(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps({"run_id": "r1", "target_adapter_kind": "api_bridge", "stub_only": False}),
        encoding="utf-8",
    )
    (ws / "adapter_api_bridge.py").write_text(
        """
class ApiBridgeAdapter:
    kind = "api_bridge"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
        self._run_id = run_id
    def connect(self):
        state_path = self._workspace_dir / "target_state.json"
        if not state_path.is_file():
            return False
        import json
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        return raw.get("connected") is True
    def sync_target(self):
        state_path = self._workspace_dir / "target_state.json"
        payload = {"connected": True, "action": "probe", "endpoint": "http://127.0.0.1:8080/health"}
        state_path.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
        return payload
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "integrated"
    assert out["target_connected"] is True
    assert out["target_sync_result"]["action"] == "probe"
    state = json.loads((ws / "target_state.json").read_text(encoding="utf-8"))
    assert state["connected"] is True


def test_execute_target_adapter_integration_compatibility_shim_integrated(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps(
            {"run_id": "r2", "target_adapter_kind": "compatibility_shim", "stub_only": False},
        ),
        encoding="utf-8",
    )
    (ws / "adapter_compatibility_shim.py").write_text(
        """
class CompatibilityShimAdapter:
    kind = "compatibility_shim"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
        self._run_id = run_id
    def connect(self):
        state_path = self._workspace_dir / "target_state.json"
        if not state_path.is_file():
            return False
        import json
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        return raw.get("connected") is True
    def sync_target(self):
        mapping_path = self._workspace_dir / "bundle_shim_map.json"
        payload = {"mapped": True, "shim_mode": "bundle_compatibility"}
        mapping_path.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
        state_path = self._workspace_dir / "target_state.json"
        state_path.write_text(__import__("json").dumps({"connected": True}), encoding="utf-8")
        return payload
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="compatibility_shim", run_id="r2")
    assert out["target_integration_status"] == "integrated"
    assert (ws / "bundle_shim_map.json").is_file()
    assert out["target_sync_result"]["mapped"] is True


def test_probe_http_endpoint_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        status_code = 200

        @property
        def is_success(self) -> bool:
            return True

        @property
        def text(self) -> str:
            return "ok"

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "text/plain"}

    def _fake_get(url: str, **kwargs: object) -> _Resp:
        assert url == "http://127.0.0.1:8080/health"
        return _Resp()

    monkeypatch.setattr("httpx.get", _fake_get)
    out = probe_http_endpoint("http://127.0.0.1:8080/health")
    assert out["reachable"] is True
    assert out["ok"] is True
    assert out["body_preview"] == "ok"
    assert out["attempts"] == 1


def test_probe_http_endpoint_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    class _Resp:
        status_code = 200

        @property
        def is_success(self) -> bool:
            return True

        @property
        def text(self) -> str:
            return "ok"

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "text/plain"}

    def _flaky_get(url: str, **kwargs: object) -> _Resp:
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ConnectError("refused")
        return _Resp()

    import httpx

    monkeypatch.setattr("httpx.get", _flaky_get)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    out = probe_http_endpoint("http://127.0.0.1:8080/health", max_attempts=3)
    assert out["reachable"] is True
    assert out["attempts"] == 2


def test_probe_http_endpoint_exponential_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    class _Resp:
        status_code = 200

        @property
        def is_success(self) -> bool:
            return True

        @property
        def text(self) -> str:
            return "ok"

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "text/plain"}

    def _flaky_get(url: str, **kwargs: object) -> _Resp:
        calls["n"] += 1
        if calls["n"] < 3:
            raise httpx.ConnectError("refused")
        return _Resp()

    import httpx

    monkeypatch.setattr("httpx.get", _flaky_get)
    monkeypatch.setattr("time.sleep", lambda sec: sleeps.append(sec))
    out = probe_http_endpoint(
        "http://127.0.0.1:8080/health",
        max_attempts=3,
        retry_delay=0.25,
    )
    assert out["reachable"] is True
    assert out["attempts"] == 3
    assert sleeps == [0.25, 0.5]


def test_probe_http_endpoint_env_max_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"n": 0}

    class _Resp:
        status_code = 200

        @property
        def is_success(self) -> bool:
            return True

        @property
        def text(self) -> str:
            return "ok"

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "text/plain"}

    def _always_fail(url: str, **kwargs: object) -> _Resp:
        calls["n"] += 1
        raise httpx.ConnectError("refused")

    import httpx

    monkeypatch.setenv("NIMBUSWARE_INTEGRATOR_PROBE_MAX_ATTEMPTS", "2")
    monkeypatch.setattr("httpx.get", _always_fail)
    monkeypatch.setattr("time.sleep", lambda _s: None)
    out = probe_http_endpoint("http://127.0.0.1:8080/health")
    assert out["reachable"] is False
    assert calls["n"] == 2
    assert out["attempts"] == 2


def test_probe_http_endpoint_no_retry_on_http_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    class _Resp:
        status_code = 503

        @property
        def is_success(self) -> bool:
            return False

        @property
        def text(self) -> str:
            return "down"

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "text/plain"}

    def _once(url: str, **kwargs: object) -> _Resp:
        calls["n"] += 1
        return _Resp()

    monkeypatch.setattr("httpx.get", _once)
    out = probe_http_endpoint("http://127.0.0.1:8080/health", max_attempts=3)
    assert out["reachable"] is True
    assert out["status_code"] == 503
    assert calls["n"] == 1
    assert out["attempts"] == 1


def test_execute_target_adapter_records_http_probe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Resp:
        status_code = 503

        @property
        def is_success(self) -> bool:
            return False

        @property
        def text(self) -> str:
            return '{"status":"degraded"}'

        @property
        def headers(self) -> dict[str, str]:
            return {"content-type": "application/json"}

    monkeypatch.setattr("httpx.get", lambda *args, **kwargs: _Resp())
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "manifest.json").write_text(
        json.dumps({"run_id": "r1", "target_adapter_kind": "api_bridge", "stub_only": False}),
        encoding="utf-8",
    )
    (ws / "adapter_api_bridge.py").write_text(
        """
class ApiBridgeAdapter:
    kind = "api_bridge"
    def __init__(self, workspace_dir, *, run_id: str):
        self._workspace_dir = workspace_dir
        self._run_id = run_id
    def connect(self):
        state_path = self._workspace_dir / "target_state.json"
        if not state_path.is_file():
            return False
        import json
        raw = json.loads(state_path.read_text(encoding="utf-8"))
        return raw.get("connected") is True
    def sync_target(self):
        state_path = self._workspace_dir / "target_state.json"
        payload = {
            "connected": True,
            "action": "probe",
            "endpoint": "http://127.0.0.1:8080/health",
        }
        state_path.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
        return payload
""",
        encoding="utf-8",
    )
    out = execute_target_adapter_integration(ws, kind="api_bridge", run_id="r1")
    assert out["target_integration_status"] == "integrated"
    assert out["http_probe"]["reachable"] is True
    assert out["http_probe"]["status_code"] == 503
    assert out["http_probe"]["body_preview"] == '{"status":"degraded"}'
    assert out["http_probe"]["attempts"] == 1
    state = json.loads((ws / "target_state.json").read_text(encoding="utf-8"))
    assert state["last_http_probe"]["status_code"] == 503
