"""Unit tests for fo127 ``dump_yaml`` + ``atomic_write_yaml`` helpers (§14 #14-edit).

Six axes: round-trip, atomic tmp + replace pattern, parent-dir auto-create,
simulated ``os.replace`` failure leaves original file intact, back-to-back
writes, and the PersonaShelf.write_entry → atomic_write_yaml pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hermes_extensions.personas import PersonaShelf
from hermes_orchestrator.merge import atomic_write_yaml, dump_yaml, load_yaml

PAYLOAD: dict = {
    "version": 1,
    "business_area": [
        {
            "id": "commerce",
            "display_name": "Commerce",
            "instructions": "Refund flows.",
            "version": 2,
        },
    ],
    "development_role": [{"id": "backend", "display_name": "Backend"}],
}


# ---------------------------------------------------------------------------
# Axis 1: dump_yaml round-trip preserves the payload and key order
# ---------------------------------------------------------------------------


def test_dump_yaml_round_trip_preserves_payload(tmp_path: Path) -> None:
    text = dump_yaml(PAYLOAD)
    assert "instructions: Refund flows." in text
    parsed = yaml.safe_load(text)
    assert parsed == PAYLOAD
    # sort_keys=False ⇒ business_area appears before development_role
    assert text.find("business_area") < text.find("development_role")


# ---------------------------------------------------------------------------
# Axis 2: atomic_write_yaml writes the target and removes the sibling tmp
# ---------------------------------------------------------------------------


def test_atomic_write_yaml_uses_tmp_then_replace(tmp_path: Path) -> None:
    target = tmp_path / "shelves.yaml"
    atomic_write_yaml(target, PAYLOAD)
    assert target.is_file()
    assert load_yaml(target) == PAYLOAD
    assert not (tmp_path / "shelves.yaml.tmp").exists()


# ---------------------------------------------------------------------------
# Axis 3: missing parent directories are created on demand
# ---------------------------------------------------------------------------


def test_atomic_write_yaml_creates_parent_directory(tmp_path: Path) -> None:
    nested = tmp_path / "configs" / "personas" / "shelves.yaml"
    assert not nested.parent.exists()
    atomic_write_yaml(nested, PAYLOAD)
    assert nested.is_file()
    assert load_yaml(nested) == PAYLOAD


# ---------------------------------------------------------------------------
# Axis 4: simulated os.replace failure leaves the original file intact
# ---------------------------------------------------------------------------


def test_atomic_write_yaml_failure_leaves_original_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "shelves.yaml"
    atomic_write_yaml(target, PAYLOAD)
    original_text = target.read_text(encoding="utf-8")

    def _broken_replace(*_a: object, **_kw: object) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("hermes_orchestrator.merge.os.replace", _broken_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        atomic_write_yaml(target, {"version": 99, "business_area": [], "development_role": []})
    # Original file content untouched
    assert target.read_text(encoding="utf-8") == original_text
    # Tmp file cleaned up so a subsequent retry can succeed
    assert not (tmp_path / "shelves.yaml.tmp").exists()


# ---------------------------------------------------------------------------
# Axis 5: back-to-back writes both land
# ---------------------------------------------------------------------------


def test_back_to_back_writes_both_land(tmp_path: Path) -> None:
    target = tmp_path / "shelves.yaml"
    atomic_write_yaml(target, PAYLOAD)
    second = {
        "version": 1,
        "business_area": [{"id": "ops", "display_name": "Ops", "version": 1}],
        "development_role": [{"id": "backend", "display_name": "Backend"}],
    }
    atomic_write_yaml(target, second)
    assert load_yaml(target) == second
    assert not (tmp_path / "shelves.yaml.tmp").exists()


# ---------------------------------------------------------------------------
# Axis 6: PersonaShelf.write_entry → atomic_write_yaml pipeline
# ---------------------------------------------------------------------------


def test_persona_shelf_write_entry_through_atomic_write(tmp_path: Path) -> None:
    target = tmp_path / "shelves.yaml"
    atomic_write_yaml(target, PAYLOAD)
    shelf = PersonaShelf(target)
    shelf.write_entry(
        "business_area",
        {
            "id": "commerce",
            "display_name": "Commerce v3",
            "instructions": "Updated.",
            "version": 3,
        },
    )
    atomic_write_yaml(target, shelf.raw)
    # Re-load from disk through a fresh shelf — verifies the new entry shows up.
    reloaded = PersonaShelf(target)
    reloaded.validate_structure()
    [entry] = reloaded.list_personas("business_area")
    assert entry["display_name"] == "Commerce v3"
    assert entry["instructions"] == "Updated."
    assert entry["version"] == 3
