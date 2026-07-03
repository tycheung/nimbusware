from __future__ import annotations

from pathlib import Path

import pytest

from config.tenant_policy_store import (
    _tenant_key,
    audit_redaction,
    load_tenant_collab_policy,
    load_tenant_model_policy,
    save_tenant_collab_policy,
    save_tenant_model_policy,
)
from maker.consumer_test_scaffold import scaffold_consumer_tests


def test_scaffold_consumer_tests(tmp_path: Path) -> None:
    result = scaffold_consumer_tests(tmp_path)
    assert (tmp_path / "tests/test_smoke.py").is_file()
    assert (tmp_path / "tests/e2e/smoke.spec.ts").is_file()
    assert result["created"]


def test_audit_redaction_masks_secrets() -> None:
    out = audit_redaction({"api_key": "sk-secret", "label": "ok"})
    assert out["api_key"] == "[redacted]"
    assert out["label"] == "ok"


def test_audit_redaction_nested_and_regex() -> None:
    out = audit_redaction(
        {
            "nested": {"token": "x", "label": "ok"},
            "list": [{"secret": "y"}],
            "note": "uses sk-live-abc",
        },
    )
    assert out["nested"]["token"] == "[redacted]"
    assert out["list"][0]["secret"] == "[redacted]"
    assert out["note"] == "[redacted]"


def test_audit_redaction_list_scalar_passthrough() -> None:
    out = audit_redaction({"list": ["plain", {"token": "x"}]})
    assert out["list"][0] == "plain"
    assert out["list"][1]["token"] == "[redacted]"


def test_tenant_key_requires_slug() -> None:
    with pytest.raises(ValueError):
        _tenant_key("collab", "  ")


def test_tenant_collab_policy_file_fallback(tmp_path: Path) -> None:
    doc = save_tenant_collab_policy("ops", {"version": 1, "write_may_start_runs": True})
    assert doc["write_may_start_runs"] is True


def test_tenant_model_policy_file_fallback() -> None:
    doc = save_tenant_model_policy("ops", {"version": 1, "allow_cloud": False})
    assert doc["allow_cloud"] is False
    loaded = load_tenant_model_policy("ops")
    assert loaded.get("allow_cloud") is False


def test_load_tenant_collab_policy_file_fallback() -> None:
    save_tenant_collab_policy("ops", {"version": 1, "max_session_participants": 4})
    loaded = load_tenant_collab_policy("ops")
    assert loaded.get("max_session_participants") == 4


def test_maybe_scaffold_safe_coding_workspace_skips_when_present(tmp_path: Path) -> None:
    from maker.consumer_test_scaffold import (
        SMOKE_SPEC_REL,
        maybe_scaffold_safe_coding_workspace,
        scaffold_consumer_tests,
    )

    scaffold_consumer_tests(tmp_path)
    assert maybe_scaffold_safe_coding_workspace(tmp_path) is None
    (tmp_path / SMOKE_SPEC_REL).unlink()
    result = maybe_scaffold_safe_coding_workspace(tmp_path)
    assert result is not None
    assert (tmp_path / SMOKE_SPEC_REL).is_file()
