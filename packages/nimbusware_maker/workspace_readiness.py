from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any


def assess_workspace_readiness(workspace_path: Path) -> dict[str, Any]:
    ws = workspace_path.resolve()
    blockers: list[str] = []
    warnings: list[str] = []
    checks: dict[str, Any] = {}

    if not ws.is_dir():
        blockers.append("Workspace path does not exist.")
        return {"ready": False, "blockers": blockers, "warnings": warnings, "checks": checks}

    e2e_dir = ws / "tests" / "e2e"
    checks["e2e_dir"] = e2e_dir.is_dir()
    if not checks["e2e_dir"]:
        warnings.append(
            "No tests/e2e folder — browser checks will skip until you add Playwright tests."
        )

    playwright = shutil.which("playwright") or shutil.which("npx")
    checks["playwright_cli"] = bool(playwright)
    if not checks["playwright_cli"]:
        warnings.append("Playwright CLI not found — install with: poetry run playwright install")

    pyproject = ws / "pyproject.toml"
    package_json = ws / "package.json"
    checks["python_project"] = pyproject.is_file()
    checks["node_project"] = package_json.is_file()
    if not checks["python_project"] and not checks["node_project"]:
        warnings.append("No pyproject.toml or package.json detected — test mapping may be limited.")

    ready = not blockers
    return {
        "ready": ready,
        "blockers": blockers,
        "warnings": warnings,
        "checks": checks,
        "plain_summary": (
            "Ready to start."
            if ready and not warnings
            else ("; ".join(blockers) if blockers else "; ".join(warnings))
        ),
    }
