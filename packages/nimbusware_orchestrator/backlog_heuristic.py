from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_core.models.backlog import (
    BacklogEpic,
    BacklogFeature,
    BacklogMetadata,
    BacklogSlice,
    DeliveryBacklog,
    EpicStatus,
    SliceStatus,
    sync_backlog_metadata,
)

_BACKLOG_GENERATOR_MODE = "heuristic"

_KEYWORD_TEMPLATES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("crm", "customer", "contact", "sales"), "crm"),
    (("todo", "task list", "tasks"), "todo_api"),
    (("contact", "rest api", "health check"), "contacts_api"),
    (("static", "marketing", "landing", "homepage"), "static_site"),
    (("auth", "login", "sign in", "oauth"), "auth_app"),
    (("dashboard", "admin panel", "analytics"), "dashboard"),
)


@dataclass(frozen=True)
class _SliceSpec:
    slice_id: str
    title: str
    rationale: str
    target_suffixes: tuple[str, ...] = ()
    estimated_loc: int = 80


@dataclass(frozen=True)
class _Template:
    template_id: str
    feature_title: str
    acceptance: tuple[str, ...]
    slices: tuple[_SliceSpec, ...]


_TEMPLATES: dict[str, _Template] = {
    "crm": _Template(
        template_id="crm",
        feature_title="CRM core",
        acceptance=(
            "Health and OpenAPI endpoints respond",
            "Contacts can be listed and created",
            "Auth scaffold present",
        ),
        slices=(
            _SliceSpec(
                "slice-001",
                "Scaffold",
                "Project scaffold, health route, and OpenAPI shell",
                ("app.py", "main.py", "pyproject.toml"),
                100,
            ),
            _SliceSpec(
                "slice-002",
                "Auth",
                "User authentication module and session/token stubs",
                ("auth", "users", "login"),
                120,
            ),
            _SliceSpec(
                "slice-003",
                "Contacts list",
                "Contact model and list endpoint",
                ("contact", "crm", "models"),
                100,
            ),
            _SliceSpec(
                "slice-004",
                "Contacts create",
                "Create contact endpoint and validation",
                ("contact", "api", "routes"),
                90,
            ),
            _SliceSpec(
                "slice-005",
                "Tests",
                "API tests for health, auth, and contacts",
                ("test_", "tests/"),
                80,
            ),
        ),
    ),
    "todo_api": _Template(
        template_id="todo_api",
        feature_title="Todo REST API",
        acceptance=("CRUD todo endpoints", "Project tests pass"),
        slices=(
            _SliceSpec(
                "slice-001",
                "Scaffold",
                "App scaffold with health check",
                ("app.py", "main.py"),
                80,
            ),
            _SliceSpec(
                "slice-002",
                "Todo CRUD",
                "Create, list, and delete todo endpoints",
                ("todo", "api", "routes"),
                120,
            ),
            _SliceSpec(
                "slice-003",
                "Tests",
                "REST tests for todo endpoints",
                ("test_", "tests/"),
                70,
            ),
        ),
    ),
    "contacts_api": _Template(
        template_id="contacts_api",
        feature_title="Contacts API",
        acceptance=("Health and contacts endpoints", "OpenAPI published"),
        slices=(
            _SliceSpec(
                "slice-001",
                "Scaffold",
                "FastAPI/Flask scaffold with /health",
                ("app.py", "main.py"),
                70,
            ),
            _SliceSpec(
                "slice-002",
                "Contacts",
                "List and create contacts endpoints",
                ("contact", "routes"),
                100,
            ),
            _SliceSpec(
                "slice-003",
                "Tests",
                "Integration tests for contacts API",
                ("test_",),
                60,
            ),
        ),
    ),
    "static_site": _Template(
        template_id="static_site",
        feature_title="Marketing site",
        acceptance=("Index page loads", "README documents run instructions"),
        slices=(
            _SliceSpec(
                "slice-001",
                "HTML shell",
                "index.html with layout and primary content",
                ("index.html", "src/", "public/"),
                60,
            ),
            _SliceSpec(
                "slice-002",
                "Styles",
                "CSS theme and responsive layout",
                (".css", "styles/"),
                50,
            ),
            _SliceSpec(
                "slice-003",
                "Docs",
                "README and asset polish",
                ("README", "readme"),
                30,
            ),
        ),
    ),
    "auth_app": _Template(
        template_id="auth_app",
        feature_title="Authentication",
        acceptance=("Login/register flows", "Protected routes"),
        slices=(
            _SliceSpec(
                "slice-001",
                "Auth scaffold",
                "User model and password hashing utilities",
                ("auth", "user", "models"),
                100,
            ),
            _SliceSpec(
                "slice-002",
                "Login API",
                "Login and session/token endpoints",
                ("login", "auth", "routes"),
                90,
            ),
            _SliceSpec(
                "slice-003",
                "Tests",
                "Auth flow tests",
                ("test_",),
                70,
            ),
        ),
    ),
    "dashboard": _Template(
        template_id="dashboard",
        feature_title="Dashboard UI",
        acceptance=("Dashboard route renders", "Core widgets wired"),
        slices=(
            _SliceSpec(
                "slice-001",
                "Layout",
                "Dashboard shell and navigation",
                ("dashboard", "layout", "App."),
                90,
            ),
            _SliceSpec(
                "slice-002",
                "Widgets",
                "Summary cards and data tables",
                ("components/", "widgets"),
                110,
            ),
            _SliceSpec(
                "slice-003",
                "Tests",
                "UI smoke and component tests",
                ("test_", ".spec."),
                70,
            ),
        ),
    ),
    "generic": _Template(
        template_id="generic",
        feature_title="Delivery slices",
        acceptance=("Core requirement implemented", "Tests and gates pass"),
        slices=(
            _SliceSpec(
                "slice-001",
                "Scaffold",
                "Project scaffold aligned to requirements",
                ("app.py", "main.py", "src/", "packages/"),
                80,
            ),
            _SliceSpec(
                "slice-002",
                "Core feature",
                "Primary feature from business prompt",
                (),
                100,
            ),
            _SliceSpec(
                "slice-003",
                "Verification",
                "Tests and gate fixes for implemented feature",
                ("test_", "tests/"),
                70,
            ),
            _SliceSpec(
                "slice-004",
                "Polish",
                "Docs, error handling, and integration polish",
                ("README", "docs/"),
                50,
            ),
        ),
    ),
}


def _normalize_prompt(requirements: dict[str, Any] | None) -> str:
    if not isinstance(requirements, dict):
        return ""
    return str(requirements.get("business_prompt") or requirements.get("prompt") or "").strip()


def _match_template_id(prompt: str) -> str:
    lower = prompt.lower()
    if not lower:
        return "generic"
    for keywords, template_id in _KEYWORD_TEMPLATES:
        if any(kw in lower for kw in keywords):
            return template_id
    return "generic"


def _catalog_template_id(prompt: str, repo_root: Path | None) -> str | None:
    if repo_root is None:
        return None
    catalog = repo_root / "configs" / "launch_eval" / "catalog.yaml"
    prompts_dir = repo_root / "configs" / "launch_eval" / "prompts"
    if not catalog.is_file() or not prompts_dir.is_dir():
        return None
    try:
        import yaml

        doc = yaml.safe_load(catalog.read_text(encoding="utf-8")) or {}
    except OSError:
        return None
    entries = doc.get("prompts")
    if not isinstance(entries, list):
        return None
    lower = prompt.lower()
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        pid = str(entry.get("id") or "").strip()
        path_rel = str(entry.get("path") or "").strip()
        if not pid or not path_rel:
            continue
        prompt_path = prompts_dir / path_rel
        if not prompt_path.is_file():
            continue
        try:
            pdoc = yaml.safe_load(prompt_path.read_text(encoding="utf-8")) or {}
        except OSError:
            continue
        catalog_prompt = str(pdoc.get("business_prompt") or "").strip().lower()
        label = str(pdoc.get("label") or "").strip().lower()
        if catalog_prompt and catalog_prompt[:40] in lower:
            return pid if pid in _TEMPLATES else _match_template_id(catalog_prompt)
        if label and label in lower:
            return pid if pid in _TEMPLATES else _match_template_id(label)
    return None


def _discover_workspace_paths(repo_root: Path | None) -> list[str]:
    if repo_root is None:
        return []
    ws = Path(repo_root).resolve()
    if not ws.is_dir():
        return []
    from nimbusware_orchestrator.code_intel_entrypoints import (
        discover_entrypoint_modules,
        discover_test_seed_modules,
    )

    paths: list[str] = []
    paths.extend(discover_entrypoint_modules(ws))
    paths.extend(sorted(discover_test_seed_modules(ws)))
    for rel in ("index.html", "package.json", "pyproject.toml", "README.md"):
        if (ws / rel).is_file():
            paths.append(rel)
    for pattern in ("src/**/*.py", "src/**/*.tsx", "app/**/*.py", "packages/**/*.py"):
        for p in sorted(ws.glob(pattern))[:12]:
            if any(part.startswith(".") for part in p.parts):
                continue
            paths.append(str(p.relative_to(ws)).replace("\\", "/"))
    seen: set[str] = set()
    out: list[str] = []
    for p in paths:
        key = p.replace("\\", "/")
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out[:24]


def _path_matches_suffix(path: str, suffix: str) -> bool:
    lower_path = path.lower().replace("\\", "/")
    token = suffix.lower().strip("/")
    if not token:
        return False
    if token.endswith("/"):
        return token.rstrip("/") in lower_path
    return token in lower_path


def _resolve_target_paths(
    spec: _SliceSpec,
    workspace_paths: list[str],
    *,
    fallback: tuple[str, ...],
) -> tuple[str, ...]:
    if not spec.target_suffixes:
        if workspace_paths:
            return (workspace_paths[0],)
        return fallback
    matched: list[str] = []
    for path in workspace_paths:
        if any(_path_matches_suffix(path, suf) for suf in spec.target_suffixes):
            matched.append(path)
    if matched:
        return tuple(matched[:3])
    guessed: list[str] = []
    for suf in spec.target_suffixes:
        token = suf.strip("/")
        if not token or token.endswith("/"):
            continue
        for path in workspace_paths:
            if _path_matches_suffix(path, token):
                guessed.append(path)
        if not guessed and not workspace_paths:
            guessed.append(token)
    if guessed:
        return tuple(dict.fromkeys(guessed))[:3]
    return fallback[:3] if fallback else (spec.target_suffixes[0],)


def _fallback_paths(repo_root: Path | None) -> tuple[str, ...]:
    discovered = _discover_workspace_paths(repo_root)
    if discovered:
        return tuple(discovered[:2])
    return ("app.py", "tests/")


def _title_from_prompt(prompt: str) -> str:
    if not prompt.strip():
        return "Campaign delivery"
    one_line = re.sub(r"\s+", " ", prompt.strip())
    return one_line[:120]


def generate_heuristic_backlog(
    campaign_id: str,
    *,
    requirements: dict[str, Any] | None = None,
    max_slices: int = 10,
    repo_root: Path | Any | None = None,
) -> DeliveryBacklog:
    prompt = _normalize_prompt(requirements)
    title = _title_from_prompt(prompt)
    root = Path(repo_root).resolve() if repo_root is not None else None
    template_id = _catalog_template_id(prompt, root) or _match_template_id(prompt)
    template = _TEMPLATES.get(template_id) or _TEMPLATES["generic"]
    workspace_paths = _discover_workspace_paths(root)
    fallback = _fallback_paths(root)
    count = max(1, min(max_slices, len(template.slices)))
    slices: list[BacklogSlice] = []
    prior_id: str | None = None
    for spec in template.slices[:count]:
        targets = _resolve_target_paths(spec, workspace_paths, fallback=fallback)
        deps: tuple[str, ...] = (prior_id,) if prior_id else ()
        slices.append(
            BacklogSlice(
                slice_id=spec.slice_id,
                status=SliceStatus.PENDING,
                target_paths=targets,
                depends_on=deps,
                estimated_loc=spec.estimated_loc,
                rationale=f"{spec.title}: {spec.rationale}",
            ),
        )
        prior_id = spec.slice_id
    backlog = DeliveryBacklog(
        campaign_id=campaign_id,
        epics=(
            BacklogEpic(
                epic_id=f"epic-{template.template_id}",
                title=title,
                status=EpicStatus.IN_PROGRESS,
                features=(
                    BacklogFeature(
                        feature_id=f"feat-{template.template_id}",
                        title=template.feature_title,
                        acceptance_criteria=template.acceptance,
                        slices=tuple(slices),
                    ),
                ),
            ),
        ),
        metadata=BacklogMetadata(generator_mode=_BACKLOG_GENERATOR_MODE),
    )
    return sync_backlog_metadata(backlog)
