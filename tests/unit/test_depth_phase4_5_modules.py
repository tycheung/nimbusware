from __future__ import annotations

from pathlib import Path

from nimbusware_config.tenant_policy_store import audit_redaction, save_tenant_collab_policy
from nimbusware_maker.consumer_test_scaffold import scaffold_consumer_tests


def test_scaffold_consumer_tests(tmp_path: Path) -> None:
    result = scaffold_consumer_tests(tmp_path)
    assert (tmp_path / "tests/test_smoke.py").is_file()
    assert (tmp_path / "tests/e2e/smoke.spec.ts").is_file()
    assert result["created"]


def test_audit_redaction_masks_secrets() -> None:
    out = audit_redaction({"api_key": "sk-secret", "label": "ok"})
    assert out["api_key"] == "[redacted]"
    assert out["label"] == "ok"


def test_tenant_collab_policy_file_fallback(tmp_path: Path) -> None:
    doc = save_tenant_collab_policy("ops", {"version": 1, "write_may_start_runs": True})
    assert doc["write_may_start_runs"] is True
