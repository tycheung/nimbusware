from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agent_core.mapping import mapping_or_empty

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


@dataclass(frozen=True)
class WorkspaceLayout:
    workspace: Path
    stack: str
    source_roots: tuple[str, ...]
    test_roots: tuple[str, ...]
    has_poetry_lock: bool
    has_requirements_lock: bool
    has_mypy_config: bool
    has_bandit_config: bool
    has_pyproject: bool
    coverage_floor: float | None = None
    e2e_command: str | None = None

    def scan_paths(self) -> list[Path]:
        ws = self.workspace.resolve()
        paths: list[Path] = []
        for rel in (*self.source_roots, *self.test_roots):
            candidate = ws / rel
            if candidate.is_dir():
                paths.append(candidate)
        if not paths:
            paths.append(ws)
        return paths

    def to_dict(self) -> dict[str, Any]:
        return {
            "stack": self.stack,
            "source_roots": list(self.source_roots),
            "test_roots": list(self.test_roots),
            "has_poetry_lock": self.has_poetry_lock,
            "has_requirements_lock": self.has_requirements_lock,
            "has_mypy_config": self.has_mypy_config,
            "has_bandit_config": self.has_bandit_config,
            "has_pyproject": self.has_pyproject,
            "coverage_floor": self.coverage_floor,
            "e2e_command": self.e2e_command,
        }


def _workspace_stack(workspace: Path) -> str:
    if (workspace / "Cargo.toml").is_file():
        return "rust"
    if (workspace / "go.mod").is_file():
        return "go"
    if (workspace / "pom.xml").is_file():
        return "jvm"
    if (workspace / "package.json").is_file():
        return "node"
    return "python"


def _has_mypy_config(workspace: Path) -> bool:
    if (workspace / "mypy.ini").is_file() or (workspace / ".mypy.ini").is_file():
        return True
    pyproject = workspace / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    tool = data.get("tool") if isinstance(data, dict) else None
    return isinstance(tool, dict) and isinstance(tool.get("mypy"), dict)


def _has_bandit_config(workspace: Path) -> bool:
    if (workspace / ".bandit").is_file() or (workspace / "bandit.yaml").is_file():
        return True
    pyproject = workspace / "pyproject.toml"
    if not pyproject.is_file():
        return False
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    tool = data.get("tool") if isinstance(data, dict) else None
    return isinstance(tool, dict) and isinstance(tool.get("bandit"), dict)


def _coverage_floor_from_pyproject(workspace: Path) -> float | None:
    pyproject = workspace / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    tool = mapping_or_empty(data.get("tool") if isinstance(data, dict) else None)
    cov = mapping_or_empty(tool.get("coverage"))
    run_block = mapping_or_empty(cov.get("run"))
    fail_under = run_block.get("fail_under")
    if fail_under is None:
        return None
    try:
        val = float(fail_under)
    except (TypeError, ValueError):
        return None
    if val > 1.0:
        val = val / 100.0
    return max(0.0, min(1.0, val))


def _load_enforcement_overlay(workspace: Path) -> dict[str, Any]:
    path = workspace / ".nimbusware" / "enforcement.yaml"
    if not path.is_file():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return dict(raw) if isinstance(raw, dict) else {}


def detect_workspace_layout(workspace: Path) -> WorkspaceLayout:
    ws = workspace.resolve()
    stack = _workspace_stack(ws)
    overlay = _load_enforcement_overlay(ws)
    source_roots: list[str] = []
    test_roots: list[str] = []
    for rel in ("packages", "src", "app"):
        if (ws / rel).is_dir():
            source_roots.append(rel)
    if (ws / "tests").is_dir():
        test_roots.append("tests")
    if overlay.get("source_roots") and isinstance(overlay["source_roots"], list):
        source_roots = [str(x) for x in overlay["source_roots"]]
    if overlay.get("test_roots") and isinstance(overlay["test_roots"], list):
        test_roots = [str(x) for x in overlay["test_roots"]]
    if not source_roots and stack == "python":
        source_roots = ["."]
    cov = overlay.get("coverage_floor")
    coverage_floor = float(cov) if cov is not None else _coverage_floor_from_pyproject(ws)
    e2e_cmd = overlay.get("e2e_command")
    e2e_command = str(e2e_cmd).strip() if e2e_cmd else None
    return WorkspaceLayout(
        workspace=ws,
        stack=stack,
        source_roots=tuple(source_roots),
        test_roots=tuple(test_roots),
        has_poetry_lock=(ws / "poetry.lock").is_file(),
        has_requirements_lock=(ws / "requirements.txt").is_file()
        and (ws / "requirements.lock").is_file(),
        has_mypy_config=_has_mypy_config(ws),
        has_bandit_config=_has_bandit_config(ws),
        has_pyproject=(ws / "pyproject.toml").is_file(),
        coverage_floor=coverage_floor,
        e2e_command=e2e_command,
    )


def resolve_ruff_targets(
    layout: WorkspaceLayout,
    *,
    scope_paths: list[str] | None = None,
    scope: str,
) -> list[Path]:
    ws = layout.workspace
    if scope == "off":
        return []
    if scope == "scoped" and scope_paths:
        resolved: list[Path] = []
        for p in scope_paths:
            candidate = ws / p
            if candidate.is_file():
                resolved.append(candidate)
        return resolved
    return layout.scan_paths()
