from __future__ import annotations

from maker.deploy_target_enforcement import (
    deploy_target_from_manifest,
    validate_credential_scopes,
    validate_manifest_deploy_target,
)


def test_deploy_target_from_manifest_ecs() -> None:
    manifest = {"stacks": {"deploy": "terraform_aws_ecs"}}
    assert deploy_target_from_manifest(manifest) == "aws-ecs"


def test_validate_manifest_deploy_target_denied(tmp_path, monkeypatch) -> None:
    policy_path = tmp_path / "configs" / "enterprise" / "fleet_deploy_policies.yaml"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(
        "version: 1\ntenants:\n  default:\n    allowed_deploy_targets:\n      - aws-static-site\n",
        encoding="utf-8",
    )
    manifest = {"stacks": {"deploy": "terraform_aws_ecs"}}
    ok, detail = validate_manifest_deploy_target(
        manifest,
        tenant_slug="default",
        setup_bundle="enterprise",
        repo_root=tmp_path,
    )
    assert ok is False
    assert detail is not None
    assert "aws-ecs" in detail


def test_validate_credential_scopes_allows_non_enterprise() -> None:
    ok, detail = validate_credential_scopes(
        {"aws_profile": "prod"},
        setup_bundle="default",
    )
    assert ok is True
    assert detail is None
