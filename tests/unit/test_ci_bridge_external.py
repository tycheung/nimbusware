from __future__ import annotations

from uuid import uuid4

import pytest

from orchestrator.ci_bridge.external_ci import notify_gate_decision_external


def test_external_ci_skipped_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CI_GITHUB_REPO", raising=False)
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("NIMBUSWARE_GITLAB_TOKEN", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CI_GITLAB_PROJECT", raising=False)
    out = notify_gate_decision_external(
        run_id=uuid4(),
        verdict="PASS",
        stage_name="bundle_compatibility",
    )
    assert out["status"] == "skipped"
    assert out["reason"] == "external_ci_not_configured"


def test_external_ci_gitlab_posts_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("NIMBUSWARE_CI_GITHUB_REPO", raising=False)
    monkeypatch.setenv("NIMBUSWARE_GITLAB_TOKEN", "glpat-test")
    monkeypatch.setenv("NIMBUSWARE_CI_GITLAB_PROJECT", "acme/widget")
    monkeypatch.setenv("NIMBUSWARE_CI_HEAD_SHA", "abc123")
    captured: dict[str, object] = {}

    def fake_post_json(url: str, body: dict, **kwargs: object) -> dict:
        captured["url"] = url
        captured["body"] = body
        captured["auth_header"] = kwargs.get("auth_header")
        return {}

    monkeypatch.setattr(
        "orchestrator.ci_bridge.external_ci._post_json",
        fake_post_json,
    )
    out = notify_gate_decision_external(
        run_id=uuid4(),
        verdict="PASS",
        stage_name="integrator.gate",
    )
    assert out["status"] == "posted"
    assert out["provider"] == "gitlab"
    assert "acme%2Fwidget" in str(captured["url"])
    assert captured["body"] == {
        "state": "success",
        "name": "nimbusware/integrator.gate",
        "description": "Verdict: PASS",
        "sha": "abc123",
    }
    assert captured["auth_header"] == "PRIVATE-TOKEN"
