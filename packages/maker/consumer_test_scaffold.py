from __future__ import annotations

from pathlib import Path

from env import find_repo_root

SMOKE_SPEC_REL = Path("tests/e2e/smoke.spec.ts")
SMOKE_PYTEST_REL = Path("tests/test_smoke.py")

_TEMPLATE_DIR = find_repo_root() / "configs" / "templates"


def _template_text(name: str) -> str:
    return (_TEMPLATE_DIR / name).read_text(encoding="utf-8")


def scaffold_consumer_tests(workspace: Path) -> dict[str, object]:
    root = workspace.resolve()
    if not root.is_dir():
        raise ValueError(f"workspace is not a directory: {root}")
    created: list[str] = []
    skipped: list[str] = []
    spec_path = root / SMOKE_SPEC_REL
    pytest_path = root / SMOKE_PYTEST_REL
    if spec_path.is_file():
        skipped.append(str(SMOKE_SPEC_REL))
    else:
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(_template_text("safe_coding_smoke.spec.ts"), encoding="utf-8")
        created.append(str(SMOKE_SPEC_REL))
    if pytest_path.is_file():
        skipped.append(str(SMOKE_PYTEST_REL))
    else:
        pytest_path.parent.mkdir(parents=True, exist_ok=True)
        pytest_path.write_text(_template_text("safe_coding_smoke_test.py"), encoding="utf-8")
        created.append(str(SMOKE_PYTEST_REL))
    return {"workspace": str(root), "created": created, "skipped": skipped}


def maybe_scaffold_safe_coding_workspace(workspace: Path) -> dict[str, object] | None:
    spec_path = workspace.resolve() / SMOKE_SPEC_REL
    pytest_path = workspace.resolve() / SMOKE_PYTEST_REL
    if spec_path.is_file() and pytest_path.is_file():
        return None
    return scaffold_consumer_tests(workspace)
