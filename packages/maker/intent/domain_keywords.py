"""Extract domain-study keywords for self-evolve curriculum."""

from __future__ import annotations

import re
from typing import Any

# Phrases that are meta-intent, not the domain itself.
_STOP_PHRASES = (
    "self evolve",
    "self-evolve",
    "self evolution",
    "self-evolution",
    "get better",
    "improve yourself",
    "study other harnesses",
    "study other harness",
    "agentic harnesses",
    "diverse repos",
    "diverse projects",
    "learn from other agents",
    "meta research",
    "curriculum evolve",
    "please",
    "nimbusware",
)

_EXPLICIT_PATTERNS = (
    re.compile(
        r"(?:domain|keywords?|topic|industry|vertical)\s*[:=]\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
    re.compile(
        r"(?:learn|study|research|explore)\s+(?:about\s+)?(.+?)(?:\s+and\s+(?:self|get|improve|try)\b|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:look\s+at|focus\s+on|(?:self[-\s]?evolve|improve)\s+(?:on|for|about))\s+(.+)$",
        re.IGNORECASE,
    ),
)

_MAX_KEYWORDS = 12


def _clean_fragment(text: str) -> str:
    out = text.strip(" .,;:\"'")
    for phrase in _STOP_PHRASES:
        out = re.sub(re.escape(phrase), " ", out, flags=re.IGNORECASE)
    out = re.sub(r"\s+", " ", out).strip(" .,;:\"'")
    return out


def _tokenize_keywords(fragment: str) -> list[str]:
    cleaned = _clean_fragment(fragment)
    if not cleaned:
        return []
    # Prefer comma/semicolon lists; else keep multi-word domain phrases.
    if "," in cleaned or ";" in cleaned:
        parts = re.split(r"[,;]+", cleaned)
        tokens = [p.strip().lower() for p in parts if p.strip()]
    else:
        # Keep short domain phrases (2–4 words) as one keyword when possible.
        words = [w for w in re.split(r"\s+", cleaned.lower()) if w and len(w) > 1]
        if 2 <= len(words) <= 5:
            tokens = [" ".join(words)]
        else:
            tokens = words
    seen: set[str] = set()
    out: list[str] = []
    skip = {"and", "the", "for", "from", "with", "into", "about", "on"}
    for t in tokens:
        if t in seen or t in skip or len(t) < 2:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= _MAX_KEYWORDS:
            break
    return out


def extract_domain_keywords(text: str) -> list[str]:
    """Parse operator text into domain keywords (e.g. accounting software → ['accounting software'])."""
    prompt = (text or "").strip()
    if not prompt:
        return []
    # Explicit list in requirements style already handled by caller.
    for pat in _EXPLICIT_PATTERNS:
        m = pat.search(prompt)
        if m:
            found = _tokenize_keywords(m.group(1))
            if found:
                return found
    # Fallback: strip self-evolve boilerplate and treat remainder as domain.
    remainder = _clean_fragment(prompt)
    if not remainder or len(remainder) < 3:
        return []
    # If remaining text is mostly self-evolve noise, skip.
    lower = remainder.lower()
    if lower in {"harnesses", "repos", "projects", "agents"}:
        return []
    return _tokenize_keywords(remainder)


def attach_domain_keywords(
    requirements: dict[str, Any] | None,
    *,
    extra: list[str] | None = None,
) -> dict[str, Any] | None:
    """Ensure requirements carry domain_keywords for curriculum ticks."""
    if requirements is None and not extra:
        return None
    out = dict(requirements or {})
    existing = out.get("domain_keywords")
    collected: list[str] = []
    if isinstance(existing, list):
        collected.extend(str(x).strip().lower() for x in existing if str(x).strip())
    if extra:
        collected.extend(str(x).strip().lower() for x in extra if str(x).strip())
    prompt = str(out.get("business_prompt") or "")
    collected.extend(extract_domain_keywords(prompt))
    # Dedupe preserve order.
    seen: set[str] = set()
    keywords: list[str] = []
    for k in collected:
        if k not in seen:
            seen.add(k)
            keywords.append(k)
    if keywords:
        out["domain_keywords"] = keywords[:_MAX_KEYWORDS]
    return out


def domain_keywords_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    for row in rows:
        et = row.get("event_type")
        et_s = str(getattr(et, "value", et) or "")
        if et_s != "run.created":
            continue
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        req = meta.get("requirements") if isinstance(meta.get("requirements"), dict) else {}
        raw = req.get("domain_keywords")
        if isinstance(raw, list) and raw:
            return [str(x).strip().lower() for x in raw if str(x).strip()][:_MAX_KEYWORDS]
        prompt = str(req.get("business_prompt") or "")
        found = extract_domain_keywords(prompt)
        if found:
            return found
    return []
