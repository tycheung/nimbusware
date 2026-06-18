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
_BUTTON_RE = re.compile(
    r"""<button[^>]*>([^<]*)</button>""",
    re.IGNORECASE,
)
_INPUT_RE = re.compile(
    r"""<input[^>]*>""",
    re.IGNORECASE,
)
_FORM_RE = re.compile(r"""<form[^>]*>""", re.IGNORECASE)
_TESTID_RE = re.compile(r"""data-testid\s*=\s*["']([^"']+)["']""", re.IGNORECASE)
_ATTR_RE = re.compile(r"""(\w+)\s*=\s*["']([^"']*)["']""")


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


def discover_interactive_surfaces_from_html(html: str) -> list[ISMSurface]:
    surfaces: list[ISMSurface] = []
    seen: set[str] = set()
    for match in _BUTTON_RE.finditer(html):
        label = match.group(1).strip() or "button"
        sid = f"button:{label}"
        if sid in seen:
            continue
        seen.add(sid)
        surfaces.append(ISMSurface(surface_id=sid, kind="button", path="/", label=label))
    for match in _INPUT_RE.finditer(html):
        tag = match.group(0)
        attrs = {m.group(1).lower(): m.group(2) for m in _ATTR_RE.finditer(tag)}
        testid = attrs.get("data-testid") or attrs.get("id") or attrs.get("name") or "input"
        sid = f"input:{testid}"
        if sid in seen:
            continue
        seen.add(sid)
        surfaces.append(ISMSurface(surface_id=sid, kind="input", path="/", label=testid))
    for idx, _ in enumerate(_FORM_RE.finditer(html)):
        sid = f"form:{idx}"
        if sid in seen:
            continue
        seen.add(sid)
        surfaces.append(ISMSurface(surface_id=sid, kind="form", path="/", label=f"form_{idx}"))
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
        for surface in discover_interactive_surfaces_from_html(html):
            if surface.surface_id in seen_ids:
                continue
            seen_ids.add(surface.surface_id)
            surfaces.append(surface)
        if not any(s.kind == "html_link" for s in surfaces):
            root = ISMSurface(surface_id="page:/", kind="html_page", path="/", label="index")
            if root.surface_id not in seen_ids:
                seen_ids.add(root.surface_id)
                surfaces.append(root)

    source = "static_discovery"
    if spec is not None and html:
        source = "openapi+html"
    elif spec is not None:
        source = "openapi"
    elif html:
        source = "html"

    return InteractionSurfaceMap(version="1", surfaces=surfaces, source=source)


def discover_surfaces_runtime(
    preview_base_url: str,
    *,
    max_links: int = 20,
    timeout_seconds: float = 2.0,
) -> InteractionSurfaceMap:
    """Bounded same-origin link crawl from a live preview URL."""
    base = preview_base_url.rstrip("/")
    visited: set[str] = set()
    queue: list[str] = [base]
    surfaces: list[ISMSurface] = []
    seen_ids: set[str] = set()

    while queue and len(visited) < max_links:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        try:
            resp = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        except httpx.HTTPError:
            continue
        if not resp.is_success:
            continue
        path = url.replace(base, "") or "/"
        sid = f"runtime:{path}"
        if sid not in seen_ids:
            seen_ids.add(sid)
            surfaces.append(ISMSurface(surface_id=sid, kind="page", path=path))
        for href in _HREF_RE.findall(resp.text):
            if href.startswith("#") or href.startswith("mailto:"):
                continue
            joined = urljoin(url + "/", href)
            if not joined.startswith(base):
                continue
            if joined not in visited and joined not in queue:
                queue.append(joined)

    return InteractionSurfaceMap(version="1", surfaces=surfaces, source="runtime_crawl")


def exploratory_crawl_limits() -> tuple[int, int]:
    from nimbusware_env.env_flags import env_str

    clicks_raw = env_str("NIMBUSWARE_FACTORY_EXPLORATORY_MAX_CLICKS", "12")
    depth_raw = env_str("NIMBUSWARE_FACTORY_EXPLORATORY_MAX_DEPTH", "3")
    try:
        max_clicks = max(1, min(64, int(clicks_raw)))
    except ValueError:
        max_clicks = 12
    try:
        max_depth = max(0, min(8, int(depth_raw)))
    except ValueError:
        max_depth = 3
    return max_clicks, max_depth


def exploratory_put_crawl(
    preview_base_url: str,
    *,
    max_clicks: int | None = None,
    max_depth: int | None = None,
) -> InteractionSurfaceMap:
    """Bounded Playwright link walk for factory T3 depth."""
    if max_clicks is None or max_depth is None:
        default_clicks, default_depth = exploratory_crawl_limits()
        max_clicks = default_clicks if max_clicks is None else max_clicks
        max_depth = default_depth if max_depth is None else max_depth
    from nimbusware_orchestrator.fleet_playwright import fleet_playwright_page

    base = preview_base_url.rstrip("/")
    surfaces: list[ISMSurface] = []
    seen: set[str] = set()
    with fleet_playwright_page() as page:
        if page is None:
            return InteractionSurfaceMap(version="1", surfaces=[], source="exploratory_unavailable")
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(base, 0)]
        clicks = 0
        while queue and clicks < max_clicks:
            url, depth = queue.pop(0)
            if url in visited or depth > max_depth:
                continue
            visited.add(url)
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=12000)
            except Exception:
                continue
            clicks += 1
            path = url.replace(base, "") or "/"
            sid = f"explore:{path}"
            if sid not in seen:
                seen.add(sid)
                surfaces.append(ISMSurface(surface_id=sid, kind="page", path=path))
            for form in page.query_selector_all("form"):
                form_id = form.get_attribute("id") or form.get_attribute("name") or "form"
                fid = f"explore-form:{path}:{form_id}"
                if fid not in seen:
                    seen.add(fid)
                    surfaces.append(
                        ISMSurface(surface_id=fid, kind="form", path=path),
                    )
            for control in page.query_selector_all(
                "button, [role=button], input[type=submit], [data-testid]",
            ):
                test_id = control.get_attribute("data-testid")
                label = test_id or control.get_attribute("name") or control.tag_name
                cid = f"explore-control:{path}:{label}"
                if cid not in seen:
                    seen.add(cid)
                    surfaces.append(
                        ISMSurface(surface_id=cid, kind="control", path=path),
                    )
            if depth >= max_depth:
                continue
            for anchor in page.query_selector_all("a[href]"):
                href = anchor.get_attribute("href") or ""
                if not href or href.startswith("#") or href.startswith("mailto:"):
                    continue
                joined = urljoin(url + "/", href)
                if joined.startswith(base) and joined not in visited:
                    queue.append((joined, depth + 1))
    return InteractionSurfaceMap(version="1", surfaces=surfaces, source="exploratory_crawl")


def discover_surfaces_combined(
    workspace: Path,
    *,
    preview_base_url: str | None = None,
    runtime_crawl: bool = False,
    exploratory: bool = False,
) -> InteractionSurfaceMap:
    static_map = discover_surfaces_static(workspace, preview_base_url=preview_base_url)
    merged = list(static_map.surfaces)
    seen = {s.surface_id for s in merged}
    source_parts = [static_map.source]
    if runtime_crawl and preview_base_url:
        runtime_map = discover_surfaces_runtime(preview_base_url)
        source_parts.append("runtime_crawl")
        for surface in runtime_map.surfaces:
            if surface.surface_id in seen:
                continue
            seen.add(surface.surface_id)
            merged.append(surface)
    if exploratory and preview_base_url:
        explore_map = exploratory_put_crawl(preview_base_url)
        source_parts.append("exploratory_crawl")
        for surface in explore_map.surfaces:
            if surface.surface_id in seen:
                continue
            seen.add(surface.surface_id)
            merged.append(surface)
    return InteractionSurfaceMap(
        version="1",
        surfaces=merged,
        source="+".join(source_parts),
    )


def coverage_pct(ism: InteractionSurfaceMap, exercised: set[str]) -> float:
    if not ism.surfaces:
        return 0.0
    matched = 0
    for surface in ism.surfaces:
        if surface.surface_id in exercised or surface.path in exercised:
            matched += 1
    return round(100.0 * matched / len(ism.surfaces), 2)
