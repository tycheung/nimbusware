from __future__ import annotations

from hermes_extensions.persona_scope_overlap import scope_in_overlaps_for_assignment
from hermes_extensions.personas import PersonaShelf


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
