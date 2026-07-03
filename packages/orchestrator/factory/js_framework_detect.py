from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from env import find_repo_root


def _read_package_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _deps(pkg: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        block = pkg.get(key)
        if isinstance(block, dict):
            merged.update(block)
    return merged


def detect_js_framework(workspace: Path, repo_root: Path | None = None) -> str:
    ws = workspace.resolve()
    candidates = [ws / "package.json", ws / "frontend" / "package.json"]
    for pkg_path in candidates:
        pkg = _read_package_json(pkg_path)
        deps = _deps(pkg)
        if "next" in deps:
            return "next_js"
        if "nuxt" in deps:
            return "nuxt"
        if "@remix-run/node" in deps or "@remix-run/react" in deps:
            return "remix"
        if "@angular/core" in deps:
            return "angular_cli"
        if "svelte" in deps:
            return "svelte_vite"
        if "vue" in deps:
            return "vue_vite"
        if "react" in deps and "vite" in deps:
            return "react_vite"
        if "react" in deps:
            return "react_vite"
        if (ws / "index.html").is_file() and not deps:
            return "static_html"
    if (ws / "frontend" / "index.html").is_file():
        return "static_html"
    if any((ws / name).is_file() for name in ("index.html", "dist/index.html")):
        return "static_html"
    return "spa_generic"


def load_framework_pack(pack_id: str, repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or find_repo_root()
    path = root / "configs" / "launch_test" / "frameworks" / f"{pack_id}.yaml"
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
