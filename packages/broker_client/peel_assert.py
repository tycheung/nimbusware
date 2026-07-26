"""Shared broker compute peel assert helpers (`sak489-d` / `sak490-f` / `sak498-h` / `sak499-f`).

Consolidates assert/is/normalize helpers used by ``BrokerClient`` and compute routes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

BROKER_MEMORY_ONLY = "broker_memory_only"
BROKER_SANDBOX_ONLY = "broker_sandbox_only"
BROKER_TOOLS_ONLY = "broker_tools_only"
BROKER_RESEARCH_ONLY = "broker_research_only"
BROKER_EGRESS_ONLY = "broker_egress_only"
BROKER_LLM_UNAVAILABLE = "broker_llm_unavailable"


def build_http_miss(
    error: str,
    *,
    feature: str,
    miss_extra: dict[str, Any] | None = None,
    via: str = "broker_miss",
    status: str | None = None,
) -> dict[str, Any]:
    """Standard HTTP peel miss body for routes, SSE, and export (`sak490-f` / `sak494-j`)."""
    out: dict[str, Any] = {"via": via, "error": error, "feature": feature}
    if status is not None:
        out["status"] = status
    if miss_extra:
        out.update(miss_extra)
    return out


def is_compute_miss(raw: Any) -> bool:
    if not isinstance(raw, dict):
        return False
    if raw.get("via") == "broker_miss":
        return True
    if raw.get("status") == "degraded":
        return True
    if "error" in raw and raw.get("error") is not None:
        err = str(raw.get("error") or "")
        if err:
            return True
    return False


def _is_feature_domain_miss(
    raw: Any,
    *,
    domain_code: str,
    keywords: tuple[str, ...],
) -> bool:
    """Shared domain peel miss detector (`sak496-i`)."""
    if not isinstance(raw, dict):
        return False
    if raw.get("code") == domain_code:
        return True
    if is_compute_miss(raw):
        return True
    feat = raw.get("feature")
    if isinstance(feat, str):
        low = feat.lower()
        if any(kw in low for kw in keywords):
            if raw.get("via") == "broker_miss":
                return True
            err = raw.get("error")
            if err is not None and str(err):
                return True
    return False


def _assert_domain_ok(
    raw: Any,
    *,
    feature: str,
    is_miss: Callable[[Any], bool],
) -> dict[str, Any]:
    """Domain assert: peel miss or error dict raises (`sak496-i`)."""
    if not isinstance(raw, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {raw!r}")
    if is_miss(raw):
        raise RuntimeError(
            f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
        )
    if "error" in raw and raw.get("error") is not None:
        raise RuntimeError(f"broker_miss: {feature}: {raw.get('error')!r}")
    return raw


def is_memory_miss(raw: Any) -> bool:
    return _is_feature_domain_miss(raw, domain_code=BROKER_MEMORY_ONLY, keywords=("memory",))


def is_memory_store_or_miss(raw: Any) -> bool:
    return isinstance(raw, dict) and is_memory_miss(raw)


def is_sandbox_miss(raw: Any) -> bool:
    return _is_feature_domain_miss(raw, domain_code=BROKER_SANDBOX_ONLY, keywords=("sandbox",))


def is_tools_miss(raw: Any) -> bool:
    return _is_feature_domain_miss(raw, domain_code=BROKER_TOOLS_ONLY, keywords=("tools", "shell"))


def is_research_miss(raw: Any) -> bool:
    return _is_feature_domain_miss(raw, domain_code=BROKER_RESEARCH_ONLY, keywords=("research",))


def is_egress_miss(raw: Any) -> bool:
    return _is_feature_domain_miss(raw, domain_code=BROKER_EGRESS_ONLY, keywords=("egress",))


def is_llm_miss(raw: Any) -> bool:
    return _is_feature_domain_miss(raw, domain_code=BROKER_LLM_UNAVAILABLE, keywords=("llm",))


def assert_memory_ok(
    raw: Any,
    *,
    feature: str,
    list_key: str = "hits",
) -> dict[str, Any]:
    """Memory search assert: peel miss or error dict raises; empty hits ok (`sak495-g`).

    Empty list ``[]`` is success; ``null``/missing list or ``via=broker_miss`` is a miss.
    """
    if not isinstance(raw, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {raw!r}")
    if is_memory_miss(raw):  # sak495-g
        raise RuntimeError(
            f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
        )
    if "error" in raw and raw.get("error") is not None:
        raise RuntimeError(f"broker_miss: {feature}: {raw.get('error')!r}")
    val = raw.get(list_key)
    if not isinstance(val, list):  # sak495-g: null/missing list is miss; ``[]`` ok
        raise RuntimeError(f"broker_miss: {feature}: missing or non-list key {list_key!r}")
    return raw


def normalize_domain_tool_result(result: Any) -> dict[str, Any]:
    """Unwrap MCP ``tools/call`` content JSON / InvokeResp into a flat dict."""
    import json

    if not isinstance(result, dict):
        return {"result": result}
    content = result.get("content")
    if not isinstance(content, list) or not content:
        return result
    texts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            texts.append(str(block.get("text") or ""))
    if not texts:
        return result
    joined = "".join(texts)
    if result.get("isError"):
        return {"error": joined or "tool error", "via": "broker_miss", **result}
    try:
        parsed: Any = json.loads(joined)
    except json.JSONDecodeError:
        return {**result, "text": joined}
    if not isinstance(parsed, dict):
        return {**result, "result": parsed}
    # InvokeResp: hoist ``result`` fields for domain asserts (hits, text, …).
    inner = parsed.get("result")
    if isinstance(inner, dict):
        out = dict(inner)
        for key in ("status", "invoke_id", "error", "code", "message"):
            if key in parsed and key not in out:
                out[key] = parsed[key]
        if out.get("status") == "error" and out.get("error") is None:
            out["error"] = out.get("message") or out.get("code") or "invoke error"
        return out
    if parsed.get("status") == "error" and "error" not in parsed:
        parsed = {
            **parsed,
            "error": parsed.get("message") or parsed.get("code") or "invoke error",
        }
    return parsed


def normalize_tool_result(result: Any) -> dict[str, Any]:
    """Backward-compat alias for ``normalize_domain_tool_result`` (`sak498-g`)."""
    return normalize_domain_tool_result(result)


def assert_sandbox_ok(
    raw: Any,
    *,
    feature: str = "sandbox_exec",
) -> dict[str, Any]:
    """Sandbox assert: peel miss or error dict raises (`sak496-i` / `sak498-g`)."""
    return _assert_domain_ok(raw, feature=feature, is_miss=is_sandbox_miss)


def assert_tools_ok(
    raw: Any,
    *,
    feature: str = "shell",
) -> dict[str, Any]:
    """Tools assert: peel miss or error dict raises (`sak496-i` / `sak498-g`)."""
    return _assert_domain_ok(raw, feature=feature, is_miss=is_tools_miss)


def assert_research_ok(
    raw: Any,
    *,
    feature: str = "research_fetch",
) -> dict[str, Any]:
    """Research assert: peel miss or error dict raises (`sak496-i` / `sak498-g`)."""
    return _assert_domain_ok(raw, feature=feature, is_miss=is_research_miss)


def assert_egress_ok(
    raw: Any,
    *,
    feature: str = "egress",
) -> dict[str, Any]:
    """Egress assert: peel miss or error dict raises (`sak496-i` / `sak498-g`)."""
    return _assert_domain_ok(raw, feature=feature, is_miss=is_egress_miss)


def assert_llm_ok(
    raw: Any,
    *,
    feature: str = "llm",
) -> dict[str, Any]:
    """LLM assert: peel miss or error dict raises (`sak496-i` / `sak498-g`)."""
    return _assert_domain_ok(raw, feature=feature, is_miss=is_llm_miss)


def is_domain_peel_miss(raw: Any) -> bool:
    """Non-capacity peel miss across compute + domain offers (`sak497-j`)."""
    return (
        is_compute_miss(raw)
        or is_memory_miss(raw)
        or is_llm_miss(raw)
        or is_sandbox_miss(raw)
        or is_tools_miss(raw)
        or is_research_miss(raw)
        or is_egress_miss(raw)
    )


def format_domain_miss_message(raw: Any, *, fallback: str = "broker_miss") -> str:
    """Format domain peel miss banner text (`sak497-j`)."""
    if not isinstance(raw, dict):
        return fallback
    err = raw.get("error")
    if err is not None and str(err):
        return str(err)
    feat = raw.get("feature")
    if feat is not None and str(feat):
        return str(feat)
    via = raw.get("via")
    if via is not None and str(via):
        return str(via)
    return fallback


def assert_capacity_ok(
    raw: Any,
    *,
    feature: str,
) -> dict[str, Any]:
    """Capacity/health assert: peel miss or error dict raises (`sak486-i`)."""
    if not isinstance(raw, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {raw!r}")
    if is_compute_miss(raw):  # sak486-i
        raise RuntimeError(
            f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
        )
    if "error" in raw and raw.get("error") is not None:
        raise RuntimeError(f"broker_miss: {feature}: {raw.get('error')!r}")
    return raw


def assert_broker_compute_ok(
    raw: Any,
    *,
    feature: str,
    list_key: str | None = None,
) -> dict[str, Any]:
    """Raise on broker error dicts so callers map to ``broker_miss`` (`sak437-a` / `sak441-a`).

    Any ``error`` key is a miss — including ``error`` + empty ``nodes``/``work`` lists
    (never treat as empty success). When ``list_key`` is set, the value must be a list
    (``null`` / missing / non-list is a miss — no silent ``[]``).
    """
    if not isinstance(raw, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {raw!r}")
    if is_compute_miss(raw):  # sak483-i / sak488-i
        raise RuntimeError(
            f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
        )
    if "error" in raw:
        raise RuntimeError(f"broker_miss: {feature}: {raw.get('error')!r}")
    if list_key is not None:
        val = raw.get(list_key)
        if not isinstance(val, list):  # sak488-i: null/missing list is miss; ``[]`` ok
            raise RuntimeError(f"broker_miss: {feature}: missing or non-list key {list_key!r}")
    return raw


def assert_broker_compute_record_ok(
    raw: Any,
    *,
    feature: str,
    record_key: str = "node",
    allow_none: bool = False,
) -> dict[str, Any]:
    """Raise when a single ``node``/``work`` record is missing or peel miss (`sak438-a` / `sak487-i`).

    Rejects ``via=broker_miss`` (and degraded/error bodies) before record shape checks.
    """
    if not isinstance(raw, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {raw!r}")
    if is_compute_miss(raw):  # sak487-i
        raise RuntimeError(
            f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
        )
    if "error" in raw:
        raise RuntimeError(f"broker_miss: {feature}: {raw.get('error')!r}")
    rec = raw.get(record_key)
    if isinstance(rec, dict):
        return raw
    if allow_none and rec is None:
        return raw
    # Top-level work/node body (id present, no nested key).
    if record_key == "work" and raw.get("id") is not None and "action" not in raw:
        return raw
    if record_key == "node" and (raw.get("id") is not None or raw.get("node_id") is not None):
        if "nodes" not in raw:
            return raw
    raise RuntimeError(f"broker_miss: {feature}: missing {record_key} record")


def is_claim_empty_queue_error(raw: Any) -> bool:
    """True when claim response is an empty-queue poll (not a hard miss) (`sak439-c` / `sak488-i`).

    ``via=broker_miss`` / degraded bodies are never empty polls — callers must raise.
    """
    if not isinstance(raw, dict):
        return False
    if raw.get("via") == "broker_miss" or raw.get("status") == "degraded":  # sak488-i
        return False
    if raw.get("work") is not None:
        return False
    err = str(raw.get("error") or "")
    if not err:
        # Explicit null work without error = empty poll.
        return "error" not in raw
    low = err.lower()
    return "empty" in low or "no work" in low


def normalize_claim_work_response(raw: Any, *, feature: str = "claim") -> dict[str, Any]:
    """Normalize claim response: empty queue → ``work: None``; else assert record (`sak439-c` / `sak488-i`).

    Preserves worker poll semantics (empty → null work, via=broker).
    ``via=broker_miss`` always raises — even when ``error`` mentions an empty queue.
    """
    if not isinstance(raw, dict):
        raise RuntimeError(f"broker_miss: {feature}: non-dict response: {raw!r}")
    if raw.get("via") == "broker_miss" or raw.get("status") == "degraded":  # sak488-i
        raise RuntimeError(
            f"broker_miss: {feature}: {raw.get('error') or raw.get('feature') or raw.get('via') or 'miss'!r}"
        )
    if is_claim_empty_queue_error(raw):
        return {"work": None, "via": "broker"}
    return assert_broker_compute_record_ok(
        raw,
        feature=feature,
        record_key="work",
        allow_none=True,
    )
