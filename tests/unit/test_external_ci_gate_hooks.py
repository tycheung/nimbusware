from __future__ import annotations

from uuid import uuid4

import pytest

from nimbusware_orchestrator.ci_bridge.external_ci import attach_external_ci_metadata


def test_attach_external_ci_metadata_skipped_without_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CI_GITHUB_REPO", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    meta: dict = {"slice_id": "s1"}
    out = attach_external_ci_metadata(
        meta,
        run_id=uuid4(),
        verdict="FAIL",
        stage_name="slice.gate",
    )
    assert out is meta
    assert "external_ci" not in meta


def test_attach_external_ci_metadata_posts_gitlab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CI_GITHUB_REPO", raising=False)
    monkeypatch.setenv("NIMBUSWARE_GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("NIMBUSWARE_CI_GITLAB_PROJECT", "acme/widget")
    monkeypatch.setenv("NIMBUSWARE_CI_HEAD_SHA", "abc123")
    monkeypatch.setattr(
        "nimbusware_orchestrator.ci_bridge.external_ci._post_json",
        lambda *a, **k: {},
    )
    meta: dict = {}
    attach_external_ci_metadata(
        meta,
        run_id=uuid4(),
        verdict="PASS",
        stage_name="factory.gate",
    )
    assert meta["external_ci"]["status"] == "posted"
    assert meta["external_ci"]["provider"] == "gitlab"
