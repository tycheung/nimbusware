from __future__ import annotations

_ROUTES: dict[str, str] = {
    "/health": "ok",
    "/v1/contacts": "[]",
}


def route(path: str) -> str | None:
    return _ROUTES.get(path)
