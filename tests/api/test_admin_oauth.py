"""Admin OIDC login routes."""

from __future__ import annotations

import os
import time

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("NIMBUSWARE_SKIP_PREFLIGHT", "1")

from nimbusware_api.app import app  # noqa: E402
from nimbusware_api.routes.admin_oauth import _SESSION_COOKIE, _sign_payload
from nimbusware_env.edition import ENTERPRISE_EDITION, ENV_EDITION

ADMIN_HEADERS = {
    "X-Nimbusware-Admin-Token": os.environ.get(
        "NIMBUSWARE_ADMIN_TOKEN", "nimbusware-dev-admin-token-SEARCH_AND_REPLACE_BEFORE_PROD"
    )
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_oauth_login_individual_404(client: TestClient) -> None:
    r = client.get("/v1/admin/oauth/login", follow_redirects=False)
    assert r.status_code == 404


def test_oauth_mock_flow(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_OIDC_ENABLED", "1")
    monkeypatch.setenv("NIMBUSWARE_OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("NIMBUSWARE_OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("NIMBUSWARE_OIDC_REDIRECT_URI", "http://testserver/v1/admin/oauth/callback")
    monkeypatch.setenv("NIMBUSWARE_OIDC_MOCK", "1")

    r = client.get("/v1/admin/oauth/login", follow_redirects=False)
    assert r.status_code == 302
    assert "/mock-authorize" in r.headers["location"]

    r2 = client.get(r.headers["location"], follow_redirects=False)
    assert r2.status_code == 302
    assert "callback" in r2.headers["location"]

    r3 = client.get(r2.headers["location"], follow_redirects=False)
    assert r3.status_code == 302
    assert r3.headers["location"].endswith("/v1/admin/app/")

    sess = client.get("/v1/admin/oauth/session")
    assert sess.status_code == 200
    assert sess.json()["authenticated"] is True


def test_oauth_callback_bad_state(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_OIDC_ENABLED", "1")
    monkeypatch.setenv("NIMBUSWARE_OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("NIMBUSWARE_OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("NIMBUSWARE_OIDC_REDIRECT_URI", "http://testserver/v1/admin/oauth/callback")
    monkeypatch.setenv("NIMBUSWARE_OIDC_MOCK", "1")

    client.get("/v1/admin/oauth/login", follow_redirects=False)
    r = client.get(
        "/v1/admin/oauth/callback?code=mock_oidc_code&state=wrong",
        follow_redirects=False,
    )
    assert r.status_code == 401


def _enable_enterprise_oidc_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_EDITION, ENTERPRISE_EDITION)
    monkeypatch.setenv("NIMBUSWARE_OIDC_ENABLED", "1")
    monkeypatch.setenv("NIMBUSWARE_OIDC_ISSUER", "https://idp.example.com")
    monkeypatch.setenv("NIMBUSWARE_OIDC_CLIENT_ID", "test-client")
    monkeypatch.setenv("NIMBUSWARE_OIDC_REDIRECT_URI", "http://testserver/v1/admin/oauth/callback")
    monkeypatch.setenv("NIMBUSWARE_OIDC_MOCK", "1")


def test_oauth_callback_pkce_missing(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_enterprise_oidc_mock(monkeypatch)
    r = client.get(
        "/v1/admin/oauth/callback?code=mock_oidc_code&state=any",
        follow_redirects=False,
    )
    assert r.status_code == 400
    assert r.json()["code"] == "oidc_pkce_missing"


def test_oauth_session_expired(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_enterprise_oidc_mock(monkeypatch)
    expired = _sign_payload({"ok": True, "exp": time.time() - 60})
    client.cookies.set(_SESSION_COOKIE, expired)
    sess = client.get("/v1/admin/oauth/session")
    assert sess.status_code == 200
    assert sess.json()["authenticated"] is False


def test_oauth_session_tampered_hmac(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_enterprise_oidc_mock(monkeypatch)
    client.cookies.set(_SESSION_COOKIE, "not.valid.signature")
    sess = client.get("/v1/admin/oauth/session")
    assert sess.status_code == 200
    assert sess.json()["authenticated"] is False


def test_oauth_logout_clears_session(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_enterprise_oidc_mock(monkeypatch)
    r = client.get("/v1/admin/oauth/login", follow_redirects=False)
    r2 = client.get(r.headers["location"], follow_redirects=False)
    client.get(r2.headers["location"], follow_redirects=False)
    assert client.get("/v1/admin/oauth/session").json()["authenticated"] is True

    out = client.post("/v1/admin/oauth/logout")
    assert out.status_code == 200
    assert client.get("/v1/admin/oauth/session").json()["authenticated"] is False
