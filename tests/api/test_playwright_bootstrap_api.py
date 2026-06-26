from __future__ import annotations

from fastapi.testclient import TestClient

from nimbusware_maker.playwright_bootstrap import (
    playwright_bootstrap_status,
    run_playwright_bootstrap,
)


def test_playwright_bootstrap_status_shape() -> None:
    body = playwright_bootstrap_status()
    assert body["status"] in {"ready", "missing", "installing", "error"}
    assert "plain_summary" in body


def test_playwright_bootstrap_post_ready_short_circuit(monkeypatch) -> None:
    monkeypatch.setattr(
        "nimbusware_maker.playwright_bootstrap.playwright_bootstrap_status",
        lambda: {"status": "ready", "plain_summary": "ready"},
    )
    body = run_playwright_bootstrap()
    assert body["status"] == "ready"


def test_playwright_bootstrap_get_api(client: TestClient) -> None:
    res = client.get("/v1/platform/playwright-bootstrap")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] in {"ready", "missing", "installing", "error"}
    assert "plain_summary" in body
