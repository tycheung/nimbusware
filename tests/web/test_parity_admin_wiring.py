from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.web

_REPO = Path(__file__).resolve().parents[2]
_MATRIX = Path(__file__).resolve().parent / "parity_matrix.yaml"
_WIRING = Path(__file__).resolve().parent / "parity_admin_wiring.yaml"

_ADMIN_PARITY_EXTRA = frozenset(
    {
        "launch_eval_scorecard_admin",
        "operator_chat",
        "critic_pack_crud",
    }
)


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_parity_admin_wiring_specs_exist_on_disk() -> None:
    wiring = _load(_WIRING)
    for section, rows in wiring.items():
        assert isinstance(rows, dict), section
        for parity_id, rel_spec in rows.items():
            spec = (_REPO / rel_spec).resolve()
            assert spec.is_file(), f"{section}/{parity_id} -> {rel_spec}"


def test_parity_admin_wiring_ids_are_web_true_in_matrix() -> None:
    matrix = _load(_MATRIX)
    wiring = _load(_WIRING)
    for section, rows in wiring.items():
        section_rows = {r["id"]: r for r in matrix.get(section, []) if isinstance(r, dict)}
        for parity_id in rows:
            assert parity_id in section_rows, f"missing matrix row {section}/{parity_id}"
            assert section_rows[parity_id].get("web") is True


def _admin_parity_ids(matrix: dict) -> list[str]:
    ids: list[str] = []
    for row in matrix.get("admin", []):
        if not isinstance(row, dict) or row.get("web") is not True:
            continue
        rid = str(row.get("id") or "")
        if rid in {"run_list", "admin_gate"} or rid in _ADMIN_PARITY_EXTRA:
            ids.append(rid)
    return ids


def test_parity_admin_wiring_covers_at_least_eighty_percent() -> None:
    matrix = _load(_MATRIX)
    wiring = _load(_WIRING)
    wired = set((wiring.get("admin") or {}).keys())
    admin_ids = _admin_parity_ids(matrix)
    assert admin_ids, "expected at least one Admin parity row"
    covered = sum(1 for parity_id in admin_ids if parity_id in wired)
    ratio = covered / len(admin_ids)
    assert ratio >= 0.8, f"{covered}/{len(admin_ids)} Admin parity rows wired ({ratio:.0%})"
