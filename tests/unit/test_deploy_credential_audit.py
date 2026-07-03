from __future__ import annotations

from maker.deploy_credential_vault import append_deploy_audit_event


def test_deploy_audit_event_writes_jsonl(tmp_path) -> None:
    append_deploy_audit_event(
        "deploy.credentials.updated",
        user_id="user-123",
        tenant_slug="default",
        deploy_target="aws-ecs",
        scopes=["aws"],
        repo_root=tmp_path,
    )
    path = tmp_path / ".nimbusware" / "platform" / "deploy_audit.jsonl"
    assert path.is_file()
    line = path.read_text(encoding="utf-8").strip()
    assert "deploy.credentials.updated" in line
    assert "user-123" not in line
