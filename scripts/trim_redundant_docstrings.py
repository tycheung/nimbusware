from __future__ import annotations

import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TARGETS = (_ROOT / "packages", _ROOT / "tests", _ROOT / "scripts")

_SKIP_REL = {
    "packages/nimbusware_api/schemas/openapi_problem.py",
    "packages/nimbusware_api/schemas/openapi_route_docs.py",
    "scripts/coverage_package_floors.py",
    "scripts/mypy_ci_targets.py",
    "scripts/e2e_smoke.py",
    "scripts/prune_scraper_artifacts.py",
}

_REDUNDANT_PREFIXES = (
    "Unit tests for ",
    "Integration tests for ",
    "API tests for ",
    "Console tests for ",
    "Contract tests for ",
    "Tests for ",
    "Postgres ",
    "Focused smoke tests to ratchet",
    "Fail when key packages fall below",
    "Trim redundant one-line module docstrings",
    "Smoke-test ",
    "Pilot: ",
    "Replay a run's event-store rows",
    "Remove scraper response artifact files",
    "Rebuild bundle FAISS index when catalog",
    "Nimbusware end-to-end operator smoke checks",
)


def _rel(path: Path) -> str:
    return path.relative_to(_ROOT).as_posix()


def _should_drop(doc: str) -> bool:
    stripped = doc.strip()
    if not stripped or "\n" in stripped:
        return False
    if any(stripped.startswith(p) for p in _REDUNDANT_PREFIXES):
        return True
    if stripped.endswith(" module.") or stripped.endswith(" package."):
        return True
    if stripped.endswith(" .") or stripped.endswith("."):
        if stripped.startswith("LLM-backed plan stage"):
            return True
    if stripped == "Backward-compatible shim.":
        return True
    if stripped.startswith("Mechanical split of ") or stripped.startswith("Split "):
        return True
    if " direct contract" in stripped or " direct-contract" in stripped:
        return True
    if stripped.endswith(" contract.") or stripped.endswith(" contracts."):
        return True
    return len(stripped) > 120


def _process(path: Path) -> bool:
    if _rel(path) in _SKIP_REL:
        return False
    if "_archive" in path.parts:
        return False
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    if not tree.body:
        return False
    first = tree.body[0]
    if not isinstance(first, ast.Expr) or not isinstance(first.value, ast.Constant):
        return False
    if not isinstance(first.value.value, str):
        return False
    doc = first.value.value
    if not _should_drop(doc):
        return False
    lines = text.splitlines(keepends=True)
    start = first.lineno - 1
    end = first.end_lineno
    new_lines = lines[:start] + lines[end:]
    while len(new_lines) > 1 and new_lines[0].strip() == "":
        new_lines = new_lines[1:]
    path.write_text("".join(new_lines), encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for root in _TARGETS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if _process(path):
                changed += 1
                print(_rel(path))
    print(f"trimmed {changed} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
