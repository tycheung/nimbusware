"""Desktop launcher smoke test (requires full stack)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from nimbusware_env.desktop_common import repo_root


@pytest.mark.integration
@pytest.mark.slow
def test_run_app_smoke_starts_api_and_streamlit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = repo_root(start=Path(__file__).resolve().parent)
    from nimbusware_env import run_app

    monkeypatch.delenv("NIMBUSWARE_API_PORT", raising=False)
    code = 1
    for _ in range(2):
        code = run_app.main(["--smoke", "--repo-root", str(root)])
        if code == 0:
            break
        time.sleep(1)
    assert code == 0
