from __future__ import annotations

import re

_DISCIPLINE_TAXONOMY: dict[str, str] = {
    "frontend": "frontend_writer",
    "backend": "backend_writer",
    "qa": "test_writer",
    "architect": "architect",
    "pm": "planner",
    "devops": "integration_adapter_writer",
}

_ALIASES: dict[str, str] = {
    "fe": "frontend",
    "ui": "frontend",
    "be": "backend",
    "api": "backend",
    "test": "qa",
    "quality": "qa",
    "arch": "architect",
    "product": "pm",
    "ops": "devops",
    "infra": "devops",
}

_MENTION_RE = re.compile(r"@([a-zA-Z][\w-]*)")


def normalize_discipline(raw: str) -> str | None:
    key = str(raw or "").strip().lower().lstrip("@")
    if not key:
        return None
    if key in _DISCIPLINE_TAXONOMY:
        return key
    return _ALIASES.get(key)


def parse_discipline_mentions(message: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in _MENTION_RE.findall(str(message or "")):
        discipline = normalize_discipline(match)
        if discipline and discipline not in seen:
            seen.add(discipline)
            out.append(discipline)
    return out


def solo_discipline_routes(
    message: str,
    *,
    solo_hat: str | None = None,
) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    for discipline in parse_discipline_mentions(message):
        routes.append(
            {
                "discipline": discipline,
                "taxonomy_key": _DISCIPLINE_TAXONOMY[discipline],
                "source": "mention",
            },
        )
    if routes:
        return routes
    hat = normalize_discipline(solo_hat or "")
    if hat:
        return [
            {
                "discipline": hat,
                "taxonomy_key": _DISCIPLINE_TAXONOMY[hat],
                "source": "solo_hat",
            },
        ]
    return []
