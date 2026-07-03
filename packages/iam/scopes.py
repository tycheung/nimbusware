from __future__ import annotations

MAKER_USER_SCOPE = "maker_user"
MAKER_ADMIN_SCOPE = "maker_admin"

DEFAULT_USER_SCOPES = frozenset({MAKER_USER_SCOPE})
DEFAULT_ADMIN_SCOPES = frozenset({MAKER_USER_SCOPE, MAKER_ADMIN_SCOPE})


def normalize_scopes(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return (MAKER_USER_SCOPE,)
    out = sorted({str(x).strip().lower() for x in raw if str(x).strip()})
    return tuple(out) if out else (MAKER_USER_SCOPE,)


def scopes_include(raw: object, scope: str) -> bool:
    return scope.strip().lower() in set(normalize_scopes(raw))


def has_maker_user(scopes: tuple[str, ...]) -> bool:
    return MAKER_USER_SCOPE in scopes


def has_maker_admin(scopes: tuple[str, ...]) -> bool:
    return MAKER_ADMIN_SCOPE in scopes
