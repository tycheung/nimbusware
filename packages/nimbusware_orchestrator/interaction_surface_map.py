"""Interaction surface map (ISM) — OpenAPI and HTML link discovery."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

_HREF_RE = re.compile(
    r"""<a\s+[^>]*href\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ISMSurface:
    surface_id: str
    kind: str
    path: str
    method: str | None = None
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {k: v for k, v in payload.items() if v is not None}


@dataclass
class InteractionSurfaceMap:
    version: str = "1"
    surfaces: list[ISMSurface] = field(default_factory=list)
    source: str = "static_discovery"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "source": self.source,
            "surfaces": [s.to_dict() for s in self.surfaces],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InteractionSurfaceMap:
        raw_surfaces = data.get("surfaces")
        surfaces: list[ISMSurface] = []
        if isinstance(raw_surfaces, list):
            for item in raw_surfaces:
                if not isinstance(item, dict):
                    continue
                sid = str(item.get("surface_id", "")).strip()
                path = str(item.get("path", "")).strip()
                if not sid or not path:
                    continue
                surfaces.append(
                    ISMSurface(
                        surface_id=sid,
                        kind=str(item.get("kind", "unknown")),
                        path=path,
                        method=item.get("method"),
                        label=item.get("label"),
                    ),
                )
        return cls(
            version=str(data.get("version", "1")),
            surfaces=surfaces,
            source=str(data.get("source", "static_discovery")),
        )


def _normalize_path(path: str) -> str:
    if not path:
        return "/"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = f"/{path}"
    return path.rstrip("/") or "/"


def discover_surfaces_from_openapi(spec: dict[str, Any]) -> list[ISMSurface]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []
    surfaces: list[ISMSurface] = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        norm = _normalize_path(str(path))
        for method, detail in methods.items():
            if method.lower() not in {
                "get",
                "post",
                "put",
                "patch",
                "delete",
                "head",
                "options",
            }:
                continue
            label = None
            if isinstance(detail, dict):
                raw_summary = detail.get("summary") or detail.get("operationId")
                if raw_summary is not None:
                    label = str(raw_summary)
            surface_id = f"openapi:{method.upper()}:{norm}"
            surfaces.append(
                ISMSurface(
                    surface_id=surface_id,
                    kind="openapi_path",
                    path=norm,
                    method=method.upper(),
                    label=label,
                ),
            )
    return surfaces


def discover_surfaces_from_html(
    html: str,
    *,
    base_path: str = "/",
) -> list[ISMSurface]:
    surfaces: list[ISMSurface] = []
    seen: set[str] = set()
    for href in _HREF_RE.findall(html):
        href = href.strip()
        if not href or href.startswith("#"):
            continue
        if href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        if href.startswith("http://") or href.startswith("https://"):
            path = href
        else:
            path = urljoin(base_path, href)
        norm = _normalize_path(path)
        if norm in seen:
            continue
        seen.add(norm)
        surfaces.append(
            ISMSurface(
                surface_id=f"link:{norm}",
                kind="html_link",
                path=norm,
                label=href,
            ),
        )
    return surfaces


def _load_openapi_spec(workspace: Path, preview_base_url: str | None) -> dict[str, Any] | None:
    for rel in ("openapi.json", "docs/openapi.json", "static/openapi.json"):
        candidate = workspace / rel
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                return data
    if preview_base_url:
        for suffix in ("/openapi.json", "/docs/openapi.json"):
            url = f"{preview_base_url.rstrip('/')}{suffix}"
            try:
                resp = httpx.get(url, timeout=2.0, follow_redirects=True)
                if resp.is_success:
                    data = resp.json()
                    if isinstance(data, dict):
                        return data
            except (httpx.HTTPError, json.JSONDecodeError, ValueError):
                continue
    return None


def _load_html(workspace: Path, preview_base_url: str | None) -> str:
    for rel in ("index.html", "dist/index.html", "public/index.html"):
        candidate = workspace / rel
        if candidate.is_file():
            return candidate.read_text(encoding="utf-8", errors="replace")
    if preview_base_url:
        try:
            resp = httpx.get(preview_base_url, timeout=2.0, follow_redirects=True)
            if resp.is_success:
                return resp.text
        except httpx.HTTPError:
            pass
    return ""


def discover_surfaces_static(
    workspace: Path,
    *,
    preview_base_url: str | None = None,
) -> InteractionSurfaceMap:
    ws = workspace.resolve()
    surfaces: list[ISMSurface] = []
    seen_ids: set[str] = set()

    spec = _load_openapi_spec(ws, preview_base_url)
    if spec is not None:
        for surface in discover_surfaces_from_openapi(spec):
            if surface.surface_id in seen_ids:
                continue
            seen_ids.add(surface.surface_id)
            surfaces.append(surface)

    html = _load_html(ws, preview_base_url)
    if html:
        for surface in discover_surfaces_from_html(html):
            if surface.surface_id in seen_ids:
                continue
            seen_ids.add(surface.surface_id)
            surfaces.append(surface)

    source = "static_discovery"
    if spec is not None and html:
        source = "openapi+html"
    elif spec is not None:
        source = "openapi"
    elif html:
        source = "html"

    return InteractionSurfaceMap(version="1", surfaces=surfaces, source=source)


def coverage_pct(ism: InteractionSurfaceMap, exercised: set[str]) -> float:
    if not ism.surfaces:
        return 0.0
    matched = 0
    for surface in ism.surfaces:
        if surface.surface_id in exercised or surface.path in exercised:
            matched += 1
    return round(100.0 * matched / len(ism.surfaces), 2)
