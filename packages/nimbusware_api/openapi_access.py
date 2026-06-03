"""OpenAPI access-level tagging (Lane U — user vs admin route groups)."""

from __future__ import annotations

import re
from typing import Any

ACCESS_TAG_USER = "user"
ACCESS_TAG_ADMIN = "admin"

_ACCESS_TAG_DESCRIPTIONS: dict[str, str] = {
    ACCESS_TAG_USER: (
        "Maker product routes. Individual edition: no API key required. "
        "Enterprise: requires ``X-Nimbusware-Api-Key`` with ``maker_user`` scope."
    ),
    ACCESS_TAG_ADMIN: (
        "Admin Console / control-plane routes. Individual edition: requires "
        "``X-Nimbusware-Admin-Token``. Enterprise: ``maker_admin`` API key scope "
        "or admin token (bootstrap)."
    ),
}

_ADMIN_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("DELETE", re.compile(r"^/v1/projects/\{project_id\}$")),
    ("POST", re.compile(r"^/v1/roles/\{role_id\}/execute$")),
    ("POST", re.compile(r"^/v1/enterprise/iam/bootstrap$")),
    ("PUT", re.compile(r"^/v1/bundles/catalog")),
    ("PATCH", re.compile(r"^/v1/bundles/catalog")),
    ("PATCH", re.compile(r"^/v1/custom-agents/")),
    ("DELETE", re.compile(r"^/v1/custom-agents/")),
    ("POST", re.compile(r"^/v1/personas/")),
    ("PUT", re.compile(r"^/v1/personas/")),
    ("PATCH", re.compile(r"^/v1/personas/")),
    ("DELETE", re.compile(r"^/v1/personas/")),
    ("POST", re.compile(r"^/v1/runs/\{run_id\}/lifecycle/")),
    ("POST", re.compile(r"^/v1/runs/\{run_id\}/actions/")),
    ("POST", re.compile(r"^/v1/enterprise/tenants")),
    ("POST", re.compile(r"^/v1/enterprise/tenants/\{tenant_id\}/api-keys$")),
    ("POST", re.compile(r"^/v1/enterprise/fleet-memory/")),
    ("GET", re.compile(r"^/v1/enterprise/fleet-")),
    ("GET", re.compile(r"^/v1/enterprise/config-notify/")),
    ("GET", re.compile(r"^/v1/enterprise/scraper-artifacts/")),
    ("GET", re.compile(r"^/v1/enterprise/status$")),
    ("PATCH", re.compile(r"^/v1/admin/ollama/")),
    ("POST", re.compile(r"^/v1/admin/ollama/")),
    ("DELETE", re.compile(r"^/v1/admin/ollama/")),
)

_USER_PATH_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("GET", re.compile(r"^/v1/projects")),
    ("POST", re.compile(r"^/v1/projects$")),
    ("GET", re.compile(r"^/v1/policy/compare")),
    ("GET", re.compile(r"^/v1/runs/\{run_id\}/audit-export$")),
    ("GET", re.compile(r"^/v1/runs")),
    ("POST", re.compile(r"^/v1/runs$")),
    ("GET", re.compile(r"^/v1/runs/\{run_id\}/slices/")),
    ("GET", re.compile(r"^/v1/runs/\{run_id\}/maker-progress")),
    ("GET", re.compile(r"^/v1/runs/\{run_id\}/research$")),
    ("POST", re.compile(r"^/v1/runs/\{run_id\}/research/")),
    ("GET", re.compile(r"^/v1/runs/\{run_id\}/maker/")),
    ("POST", re.compile(r"^/v1/runs/\{run_id\}/maker/")),
    ("POST", re.compile(r"^/v1/runs/\{run_id\}/workspace/revert$")),
    ("GET", re.compile(r"^/v1/platform/models/")),
    ("POST", re.compile(r"^/v1/platform/models/")),
    ("GET", re.compile(r"^/v1/platform/")),
    ("POST", re.compile(r"^/v1/platform/ollama/pull$")),
    ("DELETE", re.compile(r"^/v1/platform/ollama/models/")),
    ("PATCH", re.compile(r"^/v1/platform/ollama/routing/")),
    ("GET", re.compile(r"^/v1/personas$")),
    ("GET", re.compile(r"^/v1/bundles/search$")),
    ("GET", re.compile(r"^/v1/bundles/catalog")),
    ("GET", re.compile(r"^/v1/preflight-history$")),
    ("GET", re.compile(r"^/v1/scraper-artifacts")),
    ("GET", re.compile(r"^/v1/custom-agents")),
    ("GET", re.compile(r"^/v1/enterprise/iam/me$")),
    ("GET", re.compile(r"^/v1/enterprise/tenants$")),
)


def _matches(rules: tuple[tuple[str, re.Pattern[str]], ...], method: str, path: str) -> bool:
    upper = method.upper()
    for rule_method, pattern in rules:
        if rule_method == upper and pattern.search(path):
            return True
    return False


def access_tag_for_operation(method: str, path: str) -> str:
    if _matches(_ADMIN_PATH_PATTERNS, method, path):
        return ACCESS_TAG_ADMIN
    if _matches(_USER_PATH_PATTERNS, method, path):
        return ACCESS_TAG_USER
    return ACCESS_TAG_ADMIN


def _prepend_access_tag(tags: list[str], access: str) -> list[str]:
    rest = [t for t in tags if t not in {ACCESS_TAG_USER, ACCESS_TAG_ADMIN}]
    return [access, *rest]


def enrich_openapi_access_tags(schema: dict[str, Any]) -> None:
    paths = schema.get("paths")
    if not isinstance(paths, dict):
        return

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method.startswith("x") or not isinstance(operation, dict):
                continue
            access = access_tag_for_operation(method, path)
            existing = operation.get("tags")
            tags = list(existing) if isinstance(existing, list) else []
            operation["tags"] = _prepend_access_tag(tags, access)

    tag_names = {t.get("name") for t in schema.get("tags", []) if isinstance(t, dict)}
    for name, description in _ACCESS_TAG_DESCRIPTIONS.items():
        if name not in tag_names:
            schema.setdefault("tags", []).append({"name": name, "description": description})

    schema["x-tagGroups"] = [
        {
            "name": "User routes (Maker)",
            "tags": [ACCESS_TAG_USER],
        },
        {
            "name": "Admin routes (Admin Console)",
            "tags": [ACCESS_TAG_ADMIN],
        },
    ]
