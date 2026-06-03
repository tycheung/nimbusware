"""Canonical theater message hashing for golden regression tests."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from nimbusware_projections.builders.run_theater import build_run_theater_messages


def canonical_theater_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        row: dict[str, Any] = {
            "store_seq": int(msg.get("store_seq") or 0),
            "actor_display": str(msg.get("actor_display") or ""),
            "message_kind": str(msg.get("message_kind") or ""),
            "severity": str(msg.get("severity") or ""),
            "headline": str(msg.get("headline") or ""),
        }
        body = msg.get("body_md")
        if isinstance(body, str) and body.strip():
            row["body_md"] = body
        out.append(row)
    return out


def theater_messages_hash(rows: list[dict[str, Any]]) -> str:
    messages = build_run_theater_messages(rows)
    canonical = canonical_theater_messages(messages)
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
