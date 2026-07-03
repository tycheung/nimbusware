from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from research.stitch_models import TransplantManifest

_SPDX_TOKEN = re.compile(
    r"\b(MIT|Apache-2\.0|Apache-2|BSD-2-Clause|BSD-3-Clause|ISC|GPL-3\.0|GPL-2\.0)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LicenseCheckResult:
    detected_licenses: tuple[str, ...]
    allowlist: tuple[str, ...]
    passed: bool
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class DependencyCheckResult:
    declared_deps: tuple[str, ...]
    new_deps: tuple[str, ...]
    max_allowed: int
    passed: bool
    reason_code: str | None


def _normalize_license(token: str) -> str:
    cleaned = token.strip()
    if cleaned.lower() == "apache-2":
        return "Apache-2.0"
    return cleaned


def _licenses_from_brief_sources(prior_events: list[dict[str, Any]]) -> list[str]:
    found: list[str] = []
    for row in prior_events:
        if row.get("event_type") != "research.brief.emitted":
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict) or payload.get("brief_kind") != "code":
            continue
        for source in payload.get("sources") or []:
            if not isinstance(source, dict):
                continue
            lic = str(source.get("license") or "").strip()
            if lic:
                found.append(_normalize_license(lic))
    return found


def scan_manifest_licenses(
    manifest: TransplantManifest,
    repo_root: Path,
    *,
    prior_events: list[dict[str, Any]] | None = None,
) -> tuple[str, ...]:
    detected: list[str] = []
    for rel in manifest.license_paths:
        path = repo_root / str(rel)
        if path.is_file():
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for match in _SPDX_TOKEN.finditer(text):
                detected.append(_normalize_license(match.group(1)))
    if prior_events:
        detected.extend(_licenses_from_brief_sources(prior_events))
    if not detected and manifest.source_kind == "stub":
        detected.append("MIT")
    unique = sorted({d for d in detected if d})
    return tuple(unique)


def license_check_passes(
    detected: tuple[str, ...],
    allowlist: tuple[str, ...] | list[str],
) -> LicenseCheckResult:
    allowed = {_normalize_license(a) for a in allowlist if str(a).strip()}
    if not detected:
        return LicenseCheckResult(
            detected_licenses=(),
            allowlist=tuple(sorted(allowed)),
            passed=False,
            evidence_refs=("stitch://license/none_detected",),
        )
    passed = all(lic in allowed for lic in detected)
    refs = [f"license://{lic}" for lic in detected]
    return LicenseCheckResult(
        detected_licenses=detected,
        allowlist=tuple(sorted(allowed)),
        passed=passed,
        evidence_refs=tuple(refs),
    )


def _read_declared_deps(workspace: Path) -> list[str]:
    declared: list[str] = []
    pyproject = workspace / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            return declared
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith('"') and "=" not in stripped[:1]:
                continue
            if "dependencies" in stripped.lower():
                continue
            m = re.match(r'^["\']?([a-zA-Z0-9_.-]+)', stripped)
            if m and not stripped.startswith("["):
                declared.append(m.group(1))
    req = workspace / "requirements.txt"
    if req.is_file():
        try:
            for line in req.read_text(encoding="utf-8").splitlines():
                pkg = line.split("==")[0].split(">=")[0].strip()
                if pkg and not pkg.startswith("#"):
                    declared.append(pkg)
        except OSError:
            pass
    return declared


def dependency_diff_check(
    proposed_new_deps: list[str] | tuple[str, ...],
    *,
    max_new_dependencies: int,
    workspace: Path | None = None,
) -> DependencyCheckResult:
    new_deps = tuple(str(d).strip() for d in proposed_new_deps if str(d).strip())
    declared: list[str] = []
    if workspace is not None and workspace.is_dir():
        declared = _read_declared_deps(workspace)
    if len(new_deps) > max_new_dependencies:
        return DependencyCheckResult(
            declared_deps=tuple(declared),
            new_deps=new_deps,
            max_allowed=max_new_dependencies,
            passed=False,
            reason_code="exceeds_max_new_dependencies",
        )
    return DependencyCheckResult(
        declared_deps=tuple(declared),
        new_deps=new_deps,
        max_allowed=max_new_dependencies,
        passed=True,
        reason_code=None,
    )
