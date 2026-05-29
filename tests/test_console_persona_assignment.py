"""Console persona assignment display (P1-b)."""

from __future__ import annotations

from hermes_console.persona_assignment_display import (
    persona_assignment_caption,
    persona_assignment_from_timeline,
    persona_assignment_summary_rows,
    persona_assignment_timeline_export_json,
)


def test_persona_assignment_display_from_timeline_body() -> None:
    body = {
        "persona_assignment": {
            "business_area": {"id": "commerce", "display_name": "Commerce"},
            "development_role": {"id": "backend_engineer"},
        },
    }
    pa = persona_assignment_from_timeline(body)
    assert pa is not None
    rows = persona_assignment_summary_rows(pa)
    fields = {r["field"] for r in rows}
    assert "Business area id" in fields
    assert "Business area display name" in fields
    assert persona_assignment_caption(pa) is not None
    assert "commerce" in persona_assignment_timeline_export_json(pa)
