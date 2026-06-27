from __future__ import annotations

from pathlib import Path

from nimbusware_maker.deploy_credential_vault import (
    load_deploy_credentials,
    save_deploy_credentials,
)
from nimbusware_maker.terraform_validate import validate_workspace_terraform


def test_validate_workspace_skips_without_tf(tmp_path: Path) -> None:
    ws = tmp_path / "app"
    ws.mkdir()
    (ws / "main.py").write_text("print('hi')\n", encoding="utf-8")
    result = validate_workspace_terraform(ws)
    assert result["status"] == "skipped"
    assert result["files_checked"] == 0


def test_deploy_credentials_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "nimbusware_maker.deploy_credential_vault.find_repo_root",
        lambda: tmp_path,
    )
    saved = save_deploy_credentials(
        "user-1",
        aws_profile="staging",
        github_repo="acme/app",
        workflow_path=".github/workflows/deploy.yml",
        repo_root=tmp_path,
    )
    assert saved["aws_profile"] == "staging"
    loaded = load_deploy_credentials("user-1", repo_root=tmp_path)
    assert loaded["github_repo"] == "acme/app"
