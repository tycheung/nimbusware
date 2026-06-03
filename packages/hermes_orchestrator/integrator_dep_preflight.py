from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def _normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.strip().lower())


def _parse_pyproject_deps(pyproject_path: Path) -> dict[str, str]:
    if not pyproject_path.is_file():
        return {}
    text = pyproject_path.read_text(encoding="utf-8")
    match = re.search(
        r"dependencies\s*=\s*\[(.*?)\]",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if not match:
        return {}
    block = match.group(1)
    out: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip().strip(",").strip('"').strip("'")
        if not line or line.startswith("#"):
            continue
        name = re.split(r"[<>=!~\s\[]", line, maxsplit=1)[0].strip()
        if name:
            out[_normalize_name(name)] = line
    return out


def _required_packages_from_bundle_meta(bundle_meta: dict[str, Any] | None) -> list[str]:
    if not bundle_meta:
        return []
    raw = bundle_meta.get("required_packages")
    if isinstance(raw, list):
        return [str(x).strip() for x in raw if str(x).strip()]
    constraints = bundle_meta.get("dependency_constraints")
    if isinstance(constraints, dict):
        return [str(k).strip() for k in constraints if str(k).strip()]
    return []


def analyze_integrator_dep_conflicts(
    *,
    pyproject_path: Path,
    bundle_meta: dict[str, Any] | None,
) -> list[dict[str, str]]:
    installed = _parse_pyproject_deps(pyproject_path)
    required = _required_packages_from_bundle_meta(bundle_meta)
    conflicts: list[dict[str, str]] = []
    for pkg in required:
        key = _normalize_name(pkg)
        if key and key not in installed:
            conflicts.append(
                {
                    "package": pkg,
                    "reason": "missing_from_pyproject",
                    "detail": f"{pkg} not listed in project.dependencies",
                },
            )
    return conflicts
