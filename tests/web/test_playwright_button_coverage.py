from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.web

_REPO = Path(__file__).resolve().parents[2]
_INVENTORY = Path(__file__).resolve().parent / "playwright_button_inventory.yaml"
_WIRING = Path(__file__).resolve().parent / "playwright_button_click_wiring.yaml"
_AUDIT = _REPO / "scripts" / "ci" / "audit_playwright_button_coverage.py"

_CLICK_TESTID_RE = re.compile(
    r"getByTestId\(\s*[`\"']([^`\"']+)[`\"']\s*\)\s*\.click\(",
)
_CLICK_TESTID_CHAIN_RE = re.compile(
    r"getByTestId\(\s*[`\"']([^`\"']+)[`\"']\s*\)\s*\.\s*first\(\)\s*;",
)
_ROLE_CLICK_RE = re.compile(
    r'getByRole\(\s*["\']button["\']\s*,\s*\{\s*name:\s*["\']([^"\']+)["\']\s*\}\s*\)'
    r"(?:\s*\.\s*first\(\))?\s*\.click\(",
)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_playwright_button_inventory_is_fresh() -> None:
    proc = subprocess.run(
        [sys.executable, str(_AUDIT), "--check"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_playwright_button_click_wiring_specs_exist() -> None:
    wiring = _load(_WIRING)
    for section in ("maker", "admin"):
        rows = wiring.get(section) or {}
        assert isinstance(rows, dict), section
        for test_id, rel_spec in rows.items():
            spec = (_REPO / rel_spec).resolve()
            assert spec.is_file(), f"{section}/{test_id} -> {rel_spec}"


def _spec_clicks(path: Path) -> tuple[set[str], set[str]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    test_ids = set(_CLICK_TESTID_RE.findall(text))
    if ".click(" in text:
        test_ids.update(_CLICK_TESTID_CHAIN_RE.findall(text))
    roles = set(_ROLE_CLICK_RE.findall(text))
    return test_ids, roles


def test_playwright_button_click_wiring_specs_invoke_click() -> None:
    wiring = _load(_WIRING)
    for section in ("maker", "admin"):
        for test_id, rel_spec in (wiring.get(section) or {}).items():
            spec = (_REPO / rel_spec).resolve()
            clicked_ids, _ = _spec_clicks(spec)
            assert test_id in clicked_ids, f"{test_id} not clicked in {rel_spec}"

    for row in wiring.get("role_buttons") or []:
        name = str(row.get("name") or "")
        rel_spec = str(row.get("spec") or "")
        spec = (_REPO / rel_spec).resolve()
        _, clicked_roles = _spec_clicks(spec)
        assert name in clicked_roles, f'role button "{name}" not clicked in {rel_spec}'


def test_playwright_button_click_ratio_meets_floor() -> None:
    inventory = _load(_INVENTORY)
    summary = inventory.get("summary") or {}
    ratio = float(summary.get("click_ratio") or 0.0)
    # Floor ratchets as click wiring grows; keep below current inventory click_ratio.
    assert ratio >= 0.23, f"click_ratio {ratio:.1%} below 23% floor"
