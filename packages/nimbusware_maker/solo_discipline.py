from __future__ import annotations

from nimbusware_maker.collab_disciplines import (
    discipline_routes,
    normalize_discipline,
    parse_discipline_mentions,
)

__all__ = [
    "discipline_routes",
    "normalize_discipline",
    "parse_discipline_mentions",
    "solo_discipline_routes",
]


def solo_discipline_routes(
    message: str,
    *,
    solo_hat: str | None = None,
) -> list[dict[str, str]]:
    return discipline_routes(message, solo_hat=solo_hat)
