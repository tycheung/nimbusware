from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hermes_extensions.personas import (
    ALLOWED_PROBATION_STATUSES,
    PERSONA_ALLOWED_TOOL_MAX_CHARS,
    PERSONA_ALLOWED_TOOLS_MAX_ENTRIES,
    PERSONA_INSTRUCTIONS_MAX_CHARS,
    PERSONA_SUCCESS_METRICS_MAX_ENTRIES,
    PersonaShelf,
    normalize_entry,
)


def _shelf_with_entry(tmp_path: Path, entry: dict, *, shelf: str = "business_area") -> Path:
    """Drop one ``entry`` onto ``shelf`` with a legacy filler on the other shelf."""
    other = "development_role" if shelf == "business_area" else "business_area"
    payload = {
        "version": 1,
        shelf: [entry],
        other: [{"id": "filler", "display_name": "Filler"}],
    }
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "shelves.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


# Axis 1: legacy compat


def test_legacy_minimal_entry_still_loads(tmp_path: Path) -> None:
    """``{id, display_name}`` entries from before fo127 must still validate."""
    path = _shelf_with_entry(tmp_path, {"id": "commerce", "display_name": "Commerce"})
    shelf = PersonaShelf(path)
    shelf.validate_structure()
    catalog = shelf.to_public_catalog()
    [entry] = catalog["business_area"]
    assert entry["id"] == "commerce"
    assert entry["display_name"] == "Commerce"
    # Version defaults to 1 in the public catalog even when absent on disk
    assert entry["version"] == 1
    # Optional fields are omitted from the wire payload
    assert "instructions" not in entry


# Axis 2: full-payload entry (all fo127 fields) accepts + round-trips


def test_full_entry_with_all_optional_fields_accepted(tmp_path: Path) -> None:
    full = {
        "id": "commerce",
        "display_name": "Commerce",
        "instructions": "Validate refund flows.",
        "capability_profile": "Knows PCI scope basics.",
        "boundary_statement": "Defers GPU perf to others.",
        "allowed_tools": ["bundle_search"],
        "success_metrics": ["Plan covers refunds"],
        "probation_status": "promoted",
        "version": 3,
    }
    shelf = PersonaShelf(_shelf_with_entry(tmp_path, full))
    shelf.validate_structure()
    [entry] = shelf.to_public_catalog()["business_area"]
    for key, value in full.items():
        assert entry[key] == value


# Axis 3: instructions length cap rejected


def test_instructions_length_cap_rejected(tmp_path: Path) -> None:
    bad = {
        "id": "commerce",
        "instructions": "x" * (PERSONA_INSTRUCTIONS_MAX_CHARS + 1),
    }
    shelf = PersonaShelf(_shelf_with_entry(tmp_path, bad))
    with pytest.raises(ValueError, match="instructions"):
        shelf.validate_structure()


# Axis 4: allowed_tools entry count cap rejected


def test_allowed_tools_entry_count_cap_rejected(tmp_path: Path) -> None:
    bad = {
        "id": "commerce",
        "allowed_tools": [f"tool_{i}" for i in range(PERSONA_ALLOWED_TOOLS_MAX_ENTRIES + 1)],
    }
    shelf = PersonaShelf(_shelf_with_entry(tmp_path, bad))
    with pytest.raises(ValueError, match="allowed_tools"):
        shelf.validate_structure()


# Axis 5: allowed_tools per-entry length cap rejected


def test_allowed_tools_per_entry_length_cap_rejected(tmp_path: Path) -> None:
    bad = {
        "id": "commerce",
        "allowed_tools": ["t" * (PERSONA_ALLOWED_TOOL_MAX_CHARS + 1)],
    }
    shelf = PersonaShelf(_shelf_with_entry(tmp_path, bad))
    with pytest.raises(ValueError, match="allowed_tools"):
        shelf.validate_structure()


# Axis 6: success_metrics entry count cap rejected


def test_success_metrics_entry_count_cap_rejected(tmp_path: Path) -> None:
    bad = {
        "id": "commerce",
        "success_metrics": [
            f"metric_{i}" for i in range(PERSONA_SUCCESS_METRICS_MAX_ENTRIES + 1)
        ],
    }
    shelf = PersonaShelf(_shelf_with_entry(tmp_path, bad))
    with pytest.raises(ValueError, match="success_metrics"):
        shelf.validate_structure()


# Axis 7: probation_status enum


def test_probation_status_must_be_known_value(tmp_path: Path) -> None:
    for valid in ALLOWED_PROBATION_STATUSES:
        path = _shelf_with_entry(tmp_path / valid, {"id": "x", "probation_status": valid})
        PersonaShelf(path).validate_structure()
    bad_path = _shelf_with_entry(
        tmp_path / "bad",
        {"id": "x", "probation_status": "not_a_real_status"},
    )
    with pytest.raises(ValueError, match="probation_status"):
        PersonaShelf(bad_path).validate_structure()


# Axis 8: version must be int >= 1 when present


def test_version_must_be_positive_int(tmp_path: Path) -> None:
    for ver, expect_ok in ((1, True), (5, True), (0, False), (-1, False)):
        path = _shelf_with_entry(tmp_path / f"v{ver}", {"id": "x", "version": ver})
        shelf = PersonaShelf(path)
        if expect_ok:
            shelf.validate_structure()
        else:
            with pytest.raises(ValueError, match="version"):
                shelf.validate_structure()


def test_version_must_be_int_not_string(tmp_path: Path) -> None:
    path = _shelf_with_entry(tmp_path, {"id": "x", "version": "1"})
    with pytest.raises(ValueError, match="version"):
        PersonaShelf(path).validate_structure()


# Axis 9: wrong type for instructions rejected


def test_instructions_must_be_str_when_present(tmp_path: Path) -> None:
    path = _shelf_with_entry(tmp_path, {"id": "x", "instructions": ["not", "a", "string"]})
    with pytest.raises(ValueError, match="instructions"):
        PersonaShelf(path).validate_structure()


# Axis 10: unicode NFC normalization on instructions


def test_normalize_entry_applies_nfc_to_instructions() -> None:
    """Compose + decompose forms of é should collapse to the same NFC string."""
    composed = "caf\u00e9"  # NFC
    decomposed = "cafe\u0301"  # NFD
    assert composed != decomposed
    n1 = normalize_entry({"id": "x", "instructions": composed})
    n2 = normalize_entry({"id": "x", "instructions": decomposed})
    assert n1["instructions"] == n2["instructions"] == composed


# Axis 11: to_public_catalog omits absent optional fields, includes present


def test_to_public_catalog_omits_absent_optional_fields(tmp_path: Path) -> None:
    path = _shelf_with_entry(
        tmp_path,
        {
            "id": "commerce",
            "display_name": "Commerce",
            "instructions": "x",
        },
    )
    [entry] = PersonaShelf(path).to_public_catalog()["business_area"]
    assert "instructions" in entry
    assert "capability_profile" not in entry  # absent ⇒ omitted
    assert "boundary_statement" not in entry
    assert "allowed_tools" not in entry


# Axis 12: write_entry replaces in place; delete_entry raises when missing


def test_write_entry_replaces_in_place_and_delete_entry_raises_for_missing(
    tmp_path: Path,
) -> None:
    path = _shelf_with_entry(
        tmp_path,
        {"id": "commerce", "display_name": "Commerce", "version": 1},
    )
    shelf = PersonaShelf(path)
    shelf.write_entry(
        "business_area",
        {"id": "commerce", "display_name": "Commerce v2", "version": 2},
    )
    entries = shelf.list_personas("business_area")
    assert len(entries) == 1
    assert entries[0]["display_name"] == "Commerce v2"
    with pytest.raises(KeyError):
        shelf.delete_entry("business_area", "does_not_exist")
    shelf.delete_entry("business_area", "commerce")
    assert shelf.list_personas("business_area") == []
