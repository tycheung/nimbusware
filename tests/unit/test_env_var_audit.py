from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from nimbusware_env.settings_catalog import CATALOG, SettingScope


def test_audit_operator_env_passes() -> None:
    repo = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts" / "audit_operator_env.py")],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout


def test_catalog_has_internal_and_install_scopes() -> None:
    scopes = {d.scope for d in CATALOG.values()}
    assert SettingScope.INTERNAL in scopes
    assert SettingScope.INSTALL in scopes
    assert len(CATALOG) >= 100


def test_env_over_yaml_resolved_honors_explicit_env(
    monkeypatch,
) -> None:
    from nimbusware_env.settings_resolve import env_over_yaml_resolved

    monkeypatch.delenv("HERMES_STUB_IMPLEMENTATION_CRITICS", raising=False)
    assert env_over_yaml_resolved("HERMES_STUB_IMPLEMENTATION_CRITICS", True) is True
    monkeypatch.setenv("HERMES_STUB_IMPLEMENTATION_CRITICS", "1")
    assert env_over_yaml_resolved("HERMES_STUB_IMPLEMENTATION_CRITICS", False) is True


def test_catalog_tri_state_parallel_writers(monkeypatch) -> None:
    from nimbusware_env.env_flags import env_force_on

    monkeypatch.setenv("HERMES_PARALLEL_WRITERS", "1")
    assert env_force_on("HERMES_PARALLEL_WRITERS") is True
