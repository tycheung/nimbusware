from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from research.pattern_index import pattern_index_path


def infer_domain_tag(requirements: dict[str, Any] | None) -> str:
    if not isinstance(requirements, dict):
        return "general"
    prompt = str(requirements.get("business_prompt") or "").strip().lower()
    if not prompt:
        return "general"
    for token in (
        "golf",
        "inventory",
        "scheduling",
        "fintech",
        "auth",
        "crm",
        "todo",
        "dashboard",
        "api",
    ):
        if token in prompt:
            return token
    return "general"


def domain_brief_summary(requirements: dict[str, Any] | None, *, domain_tag: str) -> str:
    prompt = ""
    if isinstance(requirements, dict):
        prompt = str(requirements.get("business_prompt") or "").strip()
    if prompt:
        journeys = _extract_journey_phrases(prompt)
        if journeys:
            joined = "; ".join(journeys[:6])
            return (
                f"Domain ({domain_tag}): operator journeys — {joined}. "
                "Constraints: small bounded slices, tests required before merge."
            )
        return (
            f'Domain ({domain_tag}): deliver "{prompt[:240]}" with explicit acceptance '
            "criteria per feature and regression tests."
        )
    return f"Domain ({domain_tag}): standard software delivery with gated verification."


def _extract_journey_phrases(prompt: str) -> list[str]:
    parts = re.split(r"[.;]\s+|\n+", prompt)
    out: list[str] = []
    for part in parts:
        text = part.strip()
        if len(text) < 8:
            continue
        if re.search(r"\b(with|and|for|using)\b", text, re.I):
            out.append(text[:200])
    if not out and prompt.strip():
        out.append(prompt.strip()[:200])
    return out


def load_pattern_catalog(repo_root: Path) -> list[dict[str, Any]]:
    path = pattern_index_path(repo_root)
    if not path.is_file():
        return []
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, list):
        return []
    return [dict(e) for e in loaded if isinstance(e, dict)]


def discover_workspace_patterns(repo_root: Path) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    if not root.is_dir():
        return []
    patterns: list[dict[str, Any]] = []
    markers: list[tuple[str, str, list[str]]] = [
        ("python-api", "local://python/fastapi", ["app.py", "main.py", "pyproject.toml"]),
        ("python-package", "local://python/package", ["pyproject.toml", "setup.py"]),
        ("web-static", "local://web/static", ["index.html", "public/index.html"]),
        ("web-spa", "local://web/spa", ["package.json", "src/App.tsx", "src/main.tsx"]),
        ("go-module", "local://go/module", ["go.mod", "main.go"]),
    ]
    for pattern_id, repo_url, candidates in markers:
        paths = [c for c in candidates if (root / c).is_file()]
        if not paths:
            continue
        patterns.append(
            {
                "pattern_id": f"workspace-{pattern_id}",
                "repo_url": repo_url,
                "paths": paths,
                "license": "proprietary",
                "embedding_ref": f"workspace:{pattern_id}",
            },
        )
    try:
        from orchestrator.code_intel_entrypoints import discover_entrypoint_modules

        entries = discover_entrypoint_modules(root)
        if entries:
            patterns.append(
                {
                    "pattern_id": "workspace-entrypoints",
                    "repo_url": "local://workspace/entrypoints",
                    "paths": entries[:8],
                    "license": "proprietary",
                    "embedding_ref": "workspace:entrypoints",
                },
            )
    except (ImportError, OSError, TypeError, ValueError):
        pass
    return patterns


def code_brief_summary(
    requirements: dict[str, Any] | None,
    *,
    domain_tag: str,
    patterns: list[dict[str, Any]],
) -> str:
    prompt = ""
    if isinstance(requirements, dict):
        prompt = str(requirements.get("business_prompt") or "").strip()
    if patterns:
        refs = ", ".join(
            f"{p.get('repo_url', 'local')} ({len(p.get('paths') or [])} paths)"
            for p in patterns[:4]
        )
        base = f"Code research ({domain_tag}): reuse patterns from {refs}."
    else:
        base = f"Code research ({domain_tag}): greenfield implementation from requirements."
    if prompt:
        base = f"{base} Target capability: {prompt[:300]}"
    return base[:4000]


def select_research_patterns(
    repo_root: Path,
    *,
    requirements: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    indexed = load_pattern_catalog(repo_root)
    if indexed:
        return indexed[-6:]
    discovered = discover_workspace_patterns(repo_root)
    if discovered:
        return discovered
    domain = infer_domain_tag(requirements)
    return [
        {
            "pattern_id": f"greenfield-{domain}",
            "repo_url": f"requirements://greenfield/{domain}",
            "paths": ["src/", "app.py", "main.py"],
            "license": "proprietary",
            "embedding_ref": f"requirements:{domain}",
        },
    ]
