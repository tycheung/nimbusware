from __future__ import annotations

from typing import Any


def bundle_editor_tags_from_text(raw: str) -> list[str]:
    parts: list[str] = []
    for chunk in raw.replace("\n", ",").split(","):
        t = chunk.strip()
        if t:
            parts.append(t)
    return parts


def bundle_editor_validation_issues(
    bundle_id: str,
    *,
    require_id: bool = False,
) -> list[str]:
    issues: list[str] = []
    bid = bundle_id.strip()
    if require_id and not bid:
        issues.append("id: required for new bundle entries")
    if bid and len(bid) > 128:
        issues.append("id: max 128 characters")
    return issues


def bundle_editor_patch_payload(
    *,
    title: str | None,
    tags_text: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if title is not None:
        payload["title"] = title.strip() or None
    payload["tags"] = bundle_editor_tags_from_text(tags_text)
    return payload
