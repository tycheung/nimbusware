from __future__ import annotations

from nimbusware_orchestrator.integration_adapter_scaffold import (
    validate_integration_manifest,
    validate_manifest_for_run,
)


def test_validate_integration_manifest_rejects_stub() -> None:
    errs = validate_integration_manifest(
        {"run_id": "x", "target_adapter_kind": "api_bridge", "stub_only": True},
    )
    assert errs


def test_validate_integration_manifest_rejects_unknown_kind() -> None:
    errs = validate_integration_manifest(
        {"run_id": "x", "target_adapter_kind": "custom", "stub_only": False},
    )
    assert any("unknown" in e for e in errs)


def test_validate_integration_manifest_rejects_invalid_kind_chars() -> None:
    errs = validate_integration_manifest(
        {"run_id": "x", "target_adapter_kind": "../escape", "stub_only": False},
    )
    assert errs


def test_validate_manifest_for_run_mismatch() -> None:
    manifest = {
        "run_id": "run-a",
        "target_adapter_kind": "api_bridge",
        "stub_only": False,
    }
    errs = validate_manifest_for_run(manifest, run_id="run-b", kind="api_bridge")
    assert any("run_id" in e for e in errs)
    errs_kind = validate_manifest_for_run(manifest, run_id="run-a", kind="compatibility_shim")
    assert any("target_adapter_kind" in e for e in errs_kind)
