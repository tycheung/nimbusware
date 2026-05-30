from __future__ import annotations

import httpx

from nimbusware_client.http import admin_headers, admin_token_headers, api_base, get_json, user_headers


def test_api_base_default(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_API_BASE", raising=False)
    assert api_base() == "http://127.0.0.1:8000/v1"


def test_user_headers_empty_without_env(monkeypatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_API_KEY", raising=False)
    assert user_headers() == {}


def test_admin_headers_uses_env_token(monkeypatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "test-token")
    assert admin_headers()["X-Nimbusware-Admin-Token"] == "test-token"


def test_admin_token_headers_from_ui_input() -> None:
    assert admin_token_headers("  secret  ") == {
        "X-Nimbusware-Admin-Token": "secret",
    }
    assert admin_token_headers("") == {}
    assert admin_token_headers("   ") == {}


def test_get_json_passes_query_params(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"ok": "1"}

    class _FakeClient:
        def __init__(self, *, timeout: float) -> None:
            captured["timeout"] = timeout

        def __enter__(self) -> _FakeClient:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def request(
            self,
            method: str,
            url: str,
            *,
            params: dict[str, str] | None = None,
            json: dict[str, object] | None = None,
            headers: dict[str, str] | None = None,
        ) -> _FakeResponse:
            captured["method"] = method
            captured["url"] = url
            captured["params"] = params
            captured["headers"] = headers
            return _FakeResponse()

    monkeypatch.setattr(httpx, "Client", _FakeClient)
    monkeypatch.delenv("NIMBUSWARE_API_BASE", raising=False)
    assert get_json("/runs", params={"limit": "10"}) == {"ok": "1"}
    assert captured["method"] == "GET"
    assert captured["url"] == "http://127.0.0.1:8000/v1/runs"
    assert captured["params"] == {"limit": "10"}
