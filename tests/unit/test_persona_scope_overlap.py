from __future__ import annotations

from nimbusware_extensions.persona_scope_overlap import (
    persona_scope_overlap_report,
    scope_in_overlaps_for_assignment,
)
from nimbusware_extensions.personas import PersonaShelf


def test_scope_in_overlap_detected() -> None:
    shelf = PersonaShelf.from_content(
        {
            "business_area": [
                {
                    "id": "ba1",
                    "display_name": "BA",
                    "scope_in": ["payments", "auth"],
                },
            ],
            "development_role": [
                {
                    "id": "dr1",
                    "display_name": "DR",
                    "scope_in": ["auth", "api"],
                },
            ],
        },
    )
    warnings = scope_in_overlaps_for_assignment(
        shelf=shelf,
        persona_assignment={"business_area": "ba1", "development_role": "dr1"},
    )
    assert len(warnings) == 1
    assert "auth" in warnings[0]


def test_persona_scope_overlap_report_pairs() -> None:
    shelf = PersonaShelf.from_content(
        {
            "business_area": [{"id": "ba1", "scope_in": ["auth", "pay"]}],
            "development_role": [
                {"id": "dr1", "scope_in": ["auth"]},
                {"id": "dr2", "scope_in": ["ui"]},
            ],
        },
    )
    rows = persona_scope_overlap_report(shelf)
    assert len(rows) == 1
    assert rows[0]["business_area_id"] == "ba1"
    assert rows[0]["development_role_id"] == "dr1"
    assert "auth" in rows[0]["overlap_tags"]
