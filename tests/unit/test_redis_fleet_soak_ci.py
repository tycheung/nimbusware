from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SLOW = _REPO / ".github" / "workflows" / "slow_tests.yml"
_RUNBOOK = _REPO / "scripts" / "runbooks" / "e2e_redis_fleet_soak_runbook.md"


def _load_runner():
    path = _REPO / "scripts" / "ops" / "run_redis_fleet_soak_ci.py"
    spec = importlib.util.spec_from_file_location("run_redis_fleet_soak_ci", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_slow_tests_workflow_includes_redis_fleet_soak() -> None:
    text = _SLOW.read_text(encoding="utf-8")
    assert "redis-fleet-soak:" in text
    assert "run_redis_fleet_soak_ci.py" in text
    assert "NIMBUSWARE_REDIS_FLEET_URLS" in text


def test_slow_tests_workflow_includes_factory_weekly() -> None:
    text = _SLOW.read_text(encoding="utf-8")
    assert "factory-weekly:" in text
    assert "run_factory_weekly_ci.py" in text


def test_redis_fleet_soak_runbook_documents_ci() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    assert "slow_tests.yml" in text
    assert "redis-fleet-soak" in text
    assert "NIMBUSWARE_REDIS_FLEET_URLS" in text


def test_redis_fleet_soak_ci_runner_skips_without_redis(monkeypatch) -> None:
    mod = _load_runner()
    monkeypatch.setattr(mod, "redis_reachable", lambda _url: False)
    summary = mod.run_redis_fleet_soak()
    assert summary["skipped"] is True
    assert summary["reason"] == "redis_unreachable"


def test_redis_fleet_soak_ci_runner_invokes_pytest(monkeypatch) -> None:
    mod = _load_runner()
    calls: list[list[str]] = []

    class _Proc:
        returncode = 0

    def _fake_run(cmd, **kwargs):  # noqa: ANN001
        calls.append(list(cmd))
        return _Proc()

    monkeypatch.setattr(mod, "redis_reachable", lambda _url: True)
    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    summary = mod.run_redis_fleet_soak()
    assert summary["passed"] is True
    assert summary["node_count"] == 1
    assert calls
    assert any("test_redis_dispatch_worker_stack.py" in part for part in calls[0])


def test_redis_fleet_urls_reads_fleet_env(monkeypatch) -> None:
    mod = _load_runner()
    monkeypatch.setenv(
        "NIMBUSWARE_REDIS_FLEET_URLS",
        "redis://127.0.0.1:6379/0,redis://127.0.0.1:6380/0",
    )
    assert mod.redis_fleet_urls() == [
        "redis://127.0.0.1:6379/0",
        "redis://127.0.0.1:6380/0",
    ]


def test_redis_fleet_soak_runs_all_fleet_nodes(monkeypatch) -> None:
    mod = _load_runner()
    seen: list[str] = []

    class _Proc:
        returncode = 0

    def _fake_run(cmd, **kwargs):  # noqa: ANN001
        env = kwargs.get("env") or {}
        seen.append(str(env.get("NIMBUSWARE_REDIS_URL")))
        return _Proc()

    monkeypatch.setenv(
        "NIMBUSWARE_REDIS_FLEET_URLS",
        "redis://127.0.0.1:6379/0,redis://127.0.0.1:6380/0",
    )
    monkeypatch.setattr(mod, "redis_reachable", lambda _url: True)
    monkeypatch.setattr(mod.subprocess, "run", _fake_run)
    summary = mod.run_redis_fleet_soak()
    assert summary["passed"] is True
    assert summary["node_count"] == 2
    assert seen == ["redis://127.0.0.1:6379/0", "redis://127.0.0.1:6380/0"]


def test_redis_fleet_soak_runner_main_prints_json_on_skip(monkeypatch, capsys) -> None:
    mod = _load_runner()
    monkeypatch.setattr(mod, "redis_reachable", lambda _url: False)
    assert mod.main() == 0
    out = capsys.readouterr().out.strip().splitlines()[0]
    payload = json.loads(out)
    assert payload["skipped"] is True
