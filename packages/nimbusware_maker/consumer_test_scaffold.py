from __future__ import annotations

from pathlib import Path

SMOKE_SPEC_REL = Path("tests/e2e/smoke.spec.ts")
SMOKE_PYTEST_REL = Path("tests/test_smoke.py")

SMOKE_SPEC_TEMPLATE = """import { test, expect } from "@playwright/test";

test("workspace smoke", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveTitle(/.+/);
});
"""

SMOKE_PYTEST_TEMPLATE = '''"""Minimal smoke test scaffold for Safe Coding workspaces."""


def test_smoke_import() -> None:
    assert True
'''


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
        spec_path.write_text(SMOKE_SPEC_TEMPLATE, encoding="utf-8")
        created.append(str(SMOKE_SPEC_REL))
    if pytest_path.is_file():
        skipped.append(str(SMOKE_PYTEST_REL))
    else:
        pytest_path.parent.mkdir(parents=True, exist_ok=True)
        pytest_path.write_text(SMOKE_PYTEST_TEMPLATE, encoding="utf-8")
        created.append(str(SMOKE_PYTEST_REL))
    return {"workspace": str(root), "created": created, "skipped": skipped}
