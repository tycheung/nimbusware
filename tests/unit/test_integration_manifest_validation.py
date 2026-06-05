from __future__ import annotations

from nimbusware_orchestrator.integration_adapter_scaffold import validate_integration_manifest


def test_validate_integration_manifest_rejects_stub() -> None:
    errs = validate_integration_manifest(
        {"run_id": "x", "target_adapter_kind": "api_bridge", "stub_only": True},
    )
    assert errs
