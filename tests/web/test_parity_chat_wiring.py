from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.web

_REPO = Path(__file__).resolve().parents[2]
_MATRIX = Path(__file__).resolve().parent / "parity_matrix.yaml"
_WIRING = Path(__file__).resolve().parent / "parity_chat_wiring.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_parity_chat_wiring_specs_exist_on_disk() -> None:
    wiring = _load(_WIRING)
    for section, rows in wiring.items():
        assert isinstance(rows, dict), section
        for parity_id, rel_spec in rows.items():
            spec = (_REPO / rel_spec).resolve()
            assert spec.is_file(), f"{section}/{parity_id} -> {rel_spec}"


def test_parity_chat_wiring_ids_are_web_true_in_matrix() -> None:
    matrix = _load(_MATRIX)
    wiring = _load(_WIRING)
    for section, rows in wiring.items():
        section_rows = {r["id"]: r for r in matrix.get(section, []) if isinstance(r, dict)}
        for parity_id in rows:
            assert parity_id in section_rows, f"missing matrix row {section}/{parity_id}"
            assert section_rows[parity_id].get("web") is True
