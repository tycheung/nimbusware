from __future__ import annotations

from pathlib import Path

import pytest

from env.run_app import start_servers


def test_start_servers_rejects_default_admin_token_on_public_bind(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("NIMBUSWARE_REPO_ROOT", str(tmp_path))
    with pytest.raises(RuntimeError, match="dev default"):
        start_servers(root=tmp_path, api_host="0.0.0.0", api_port=18000)
