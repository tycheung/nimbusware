from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.web

_REPO = Path(__file__).resolve().parents[2]
_WIRING = Path(__file__).resolve().parent / "parity_ide_wiring.yaml"
_MATRIX = Path(__file__).resolve().parent / "parity_matrix.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_parity_ide_wiring_targets_exist() -> None:
    wiring = _load(_WIRING).get("ide") or {}
    matrix = _load(_MATRIX)
    ide_rows = {
        r["id"]: r for r in matrix.get("maker", []) if str(r.get("id", "")).startswith("ide_mcp")
    }
    assert ide_rows
    for row_id, rel in wiring.items():
        assert row_id in ide_rows, f"wiring row {row_id} missing from parity_matrix"
        spec = (_REPO / str(rel)).resolve()
        assert spec.is_file(), f"{row_id} -> {rel}"


def test_parity_ide_rows_have_journey_coverage() -> None:
    wiring = _load(_WIRING).get("ide") or {}
    matrix = _load(_MATRIX)
    ide_rows = [r for r in matrix.get("maker", []) if str(r.get("id", "")).startswith("ide_mcp")]
    covered = sum(1 for r in ide_rows if r["id"] in wiring)
    ratio = covered / len(ide_rows)
    assert ratio >= 1.0, f"IDE MCP parity {covered}/{len(ide_rows)} wired"
