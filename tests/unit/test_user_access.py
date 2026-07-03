from __future__ import annotations

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from api import user as user_mod
from env.admin_token import DEFAULT_NIMBUSWARE_ADMIN_TOKEN


def _empty_request() -> Request:
    return Request({"type": "http", "headers": [], "method": "GET", "path": "/"})


def test_require_user_access_loopback_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(user_mod, "is_enterprise", lambda: False)
    monkeypatch.setattr(user_mod, "nimbusware_collab_enabled", lambda: False)
    monkeypatch.setenv("NIMBUSWARE_API_HOST", "127.0.0.1")
    user_mod.require_user_access(_empty_request(), x_nimbusware_admin_token=None)


def test_require_user_access_non_loopback_requires_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(user_mod, "is_enterprise", lambda: False)
    monkeypatch.setattr(user_mod, "nimbusware_collab_enabled", lambda: False)
    monkeypatch.setenv("NIMBUSWARE_API_HOST", "0.0.0.0")
    monkeypatch.setenv("NIMBUSWARE_ADMIN_TOKEN", "remote-user-token")
    with pytest.raises(HTTPException) as exc:
        user_mod.require_user_access(_empty_request(), x_nimbusware_admin_token=None)
    assert exc.value.status_code == 401

    user_mod.require_user_access(_empty_request(), x_nimbusware_admin_token="remote-user-token")


def test_require_user_access_enterprise_scopes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(user_mod, "is_enterprise", lambda: True)

    class _Ctx:
        api_scopes = frozenset({"maker_user"})

    monkeypatch.setattr(user_mod, "get_auth_context", lambda: _Ctx())
    user_mod.require_user_access(_empty_request(), x_nimbusware_admin_token=None)

    monkeypatch.setattr(user_mod, "get_auth_context", lambda: _Ctx())
    monkeypatch.setattr(
        user_mod,
        "has_maker_user",
        lambda scopes: False,
    )
    with pytest.raises(HTTPException) as exc:
        user_mod.require_user_access(
            _empty_request(),
            x_nimbusware_admin_token=DEFAULT_NIMBUSWARE_ADMIN_TOKEN,
        )
    assert exc.value.status_code == 403
