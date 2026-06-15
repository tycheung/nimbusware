from __future__ import annotations

import json
from typing import Any

import httpx

from agent_core.models import EventType
from nimbusware_env.env_flags import env_str, env_truthy, nimbusware_ollama_base_url, nimbusware_use_llm_enabled


def _theater_config_from_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    for row in rows:
        if str(row.get("event_type") or "") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if not isinstance(meta, dict):
            continue
        theater = meta.get("theater")
        if isinstance(theater, dict):
            return theater
    return {}


def theater_enabled(rows: list[dict[str, Any]]) -> bool:
    cfg = _theater_config_from_rows(rows)
    if cfg:
        return bool(cfg.get("enabled", True))
    return True


def theater_max_message_chars(rows: list[dict[str, Any]], *, default: int = 1200) -> int:
    cfg = _theater_config_from_rows(rows)
    raw = cfg.get("max_message_chars") if cfg else None
    if isinstance(raw, int) and raw > 0:
        return raw
    return default


def theater_llm_summary_enabled(rows: list[dict[str, Any]]) -> bool:
    if env_truthy("NIMBUSWARE_THEATER_LLM_SUMMARY"):
        return True
    cfg = _theater_config_from_rows(rows)
    return bool(cfg.get("llm_summary")) if cfg else False


def _theater_llm_model() -> str:
    return (env_str("NIMBUSWARE_THEATER_LLM_MODEL") or "llama3.2").strip()


def _theater_lines_for_prompt(messages: list[dict[str, Any]], *, limit: int = 8) -> str:
    lines: list[str] = []
    for msg in messages[-limit:]:
        headline = str(msg.get("headline") or "").strip()
        body = str(msg.get("body_md") or msg.get("message") or "").strip()
        if headline and body:
            lines.append(f"{headline}: {body[:160]}")
        elif headline:
            lines.append(headline)
        elif body:
            lines.append(body[:200])
    return "\n".join(lines)


def try_llm_theater_summary(messages: list[dict[str, Any]]) -> str | None:
    if not nimbusware_use_llm_enabled():
        return None
    transcript = _theater_lines_for_prompt(messages)
    if not transcript.strip():
        return None
    url = nimbusware_ollama_base_url().rstrip("/") + "/api/chat"
    body = {
        "model": _theater_llm_model(),
        "messages": [
            {
                "role": "system",
                "content": "Summarize the run theater in one concise sentence for an operator.",
            },
            {"role": "user", "content": transcript},
        ],
        "stream": False,
        "format": "json",
    }
    try:
        r = httpx.post(url, json=body, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        msg = data.get("message") if isinstance(data, dict) else None
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, str):
            return None
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            summary = parsed.get("summary") or parsed.get("headline")
            if isinstance(summary, str) and summary.strip():
                return summary.strip()
        if content.strip():
            return content.strip()[:400]
    except (httpx.HTTPError, json.JSONDecodeError, ValueError, TypeError, OSError):
        return None
    return None


def _rules_digest(messages: list[dict[str, Any]]) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for msg in messages:
        kind = str(msg.get("message_kind") or "other")
        kinds[kind] = kinds.get(kind, 0) + 1
    recent = [
        str(msg.get("headline") or "").strip()
        for msg in messages[-6:]
        if str(msg.get("headline") or "").strip()
    ]
    parts = [f"{kind}={count}" for kind, count in sorted(kinds.items())]
    body = f"Digest ({len(messages)} lines): " + ", ".join(parts)
    if recent:
        body += ". Recent: " + "; ".join(recent[:5])
    last_seq = int(messages[-1].get("store_seq") or 0)
    return {
        "store_seq": last_seq,
        "event_id": "",
        "occurred_at": None,
        "refs": {},
        "actor_display": "System",
        "message_kind": "summary",
        "severity": "info",
        "headline": "Theater digest",
        "body_md": body,
    }


def apply_theater_paraphrase(
    messages: list[dict[str, Any]],
    *,
    enabled: bool,
    llm_summary: str | None = None,
) -> list[dict[str, Any]]:
    if not enabled or not messages:
        return messages
    summary = llm_summary if llm_summary is not None else try_llm_theater_summary(messages)
    if summary:
        last_seq = int(messages[-1].get("store_seq") or 0)
        digest = {
            "store_seq": last_seq,
            "event_id": "",
            "occurred_at": None,
            "refs": {},
            "actor_display": "System",
            "message_kind": "summary",
            "severity": "info",
            "headline": "Theater summary",
            "body_md": summary,
        }
        return [*messages, digest]
    return [*messages, _rules_digest(messages)]
