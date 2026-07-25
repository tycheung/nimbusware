from __future__ import annotations

from typing import Any


def node_id_from_broker_record(node: dict[str, Any] | None) -> str:
    if not isinstance(node, dict):
        return ""
    return str(node.get("node_id") or node.get("id") or "")


def user_id_from_broker_node(item: dict[str, Any]) -> str:
    direct = item.get("user_id")
    if direct:
        return str(direct)
    label = str(item.get("label") or "")
    if label.startswith("user:"):
        return label.split(":", 1)[1].strip()
    caps = item.get("caps")
    if isinstance(caps, list):
        for cap in caps:
            s = str(cap)
            if s.startswith("user:"):
                return s.split(":", 1)[1].strip()
            if s.startswith("user_id="):
                return s.split("=", 1)[1].strip()
    elif isinstance(caps, dict):
        for key in ("user_id", "user"):
            if caps.get(key):
                return str(caps[key])
    return ""


def pick_broker_node_for_user(
    nodes: list[Any],
    user_id: str,
) -> dict[str, Any] | None:
    """Pick a broker node matching ``user_id``, else first dict node (`sak440-a/d`)."""
    uid = str(user_id)
    first: dict[str, Any] | None = None
    for item in nodes:
        if not isinstance(item, dict):
            continue
        if first is None:
            first = item
        if user_id_from_broker_node(item) == uid:
            return item
        label = str(item.get("label") or "")
        if label == f"user:{uid}":
            return item
    return first


def caps_dict_from_broker_node(item: dict[str, Any]) -> dict[str, Any]:
    caps = item.get("caps")
    if isinstance(caps, dict):
        return dict(caps)
    out: dict[str, Any] = {}
    if isinstance(caps, list):
        for cap in caps:
            s = str(cap)
            if s.startswith("user:") or s.startswith("user_id="):
                continue
            if "=" in s:
                k, v = s.split("=", 1)
                out[k] = v
            else:
                out[s] = True
    return out
