from __future__ import annotations

from pathlib import Path

from nimbusware_orchestrator.slice_contract import run_slice_contract_check


def test_slice_contract_passes_with_openapi(tmp_path: Path) -> None:
    (tmp_path / "openapi.yaml").write_text("openapi: 3.0.0\n", encoding="utf-8")
    result = run_slice_contract_check(tmp_path)
    assert result.passed
    assert "openapi.yaml" in result.detail


def test_slice_contract_fails_without_artifact(tmp_path: Path) -> None:
    result = run_slice_contract_check(tmp_path)
    assert not result.passed
