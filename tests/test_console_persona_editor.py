"""Unit tests for the fo127 Streamlit persona editor helpers."""


from __future__ import annotations

from nimbusware_console.persona_editor import (
    EDITABLE_FIELDS,
    build_patch_request,
    diff_summary,
    find_persona_in_catalog,
    parse_write_response,
    persona_editor_diff_summary_caption,
    persona_editor_display_name_draft_caption,
    persona_editor_expected_version_caption,
    persona_editor_instructions_metrics_caption,
    persona_editor_multiline_field_metrics_caption,
    persona_editor_probation_status_caption,
    persona_editor_probation_status_draft_caption,
    persona_editor_selected_shelf_caption,
    persona_editor_validation_blocking_caption,
    persona_editor_validation_issues,
    persona_editor_validation_table_rows,
    persona_field_metrics,
    persona_list_field_line_counts_caption,
)
from hermes_extensions.personas import (
    PERSONA_ALLOWED_TOOLS_MAX_ENTRIES,
    PERSONA_INSTRUCTIONS_MAX_CHARS,
)

SNAPSHOT: dict = {
    "id": "commerce",
    "display_name": "Commerce",
    "instructions": "Validate refund flows.",
    "version": 3,
    "probation_status": "promoted",
}


# Axis 1: build_patch_request only includes mutated fields + expected_version


def test_build_patch_request_only_includes_changed_fields() -> None:
    edited = dict(SNAPSHOT, instructions="Updated.")
    req = build_patch_request(SNAPSHOT, edited, actor="alice")
    assert req == {
        "expected_version": 3,
        "actor": "alice",
        "instructions": "Updated.",
    }


def test_build_patch_request_treats_empty_string_and_none_as_same() -> None:
    """Editor uses ``"" → None`` mapping; helper must not flag those as edits."""
    edited = dict(SNAPSHOT, capability_profile="")  # absent both before + after
    req = build_patch_request(SNAPSHOT, edited)
    assert "capability_profile" not in req


# Axis 2: diff_summary returns operator-readable bullets


def test_diff_summary_returns_changed_field_pairs() -> None:
    edited = dict(
        SNAPSHOT,
        instructions="Updated brief.",
        probation_status="probation",
    )
    diff = diff_summary(SNAPSHOT, edited)
    assert any("instructions" in line and "Updated brief." in line for line in diff)
    assert any("probation_status" in line for line in diff)
    # Unchanged fields don't appear
    assert not any("display_name" in line for line in diff)


def test_diff_summary_empty_when_nothing_changed() -> None:
    assert diff_summary(SNAPSHOT, dict(SNAPSHOT)) == []


def test_persona_editor_selected_shelf_caption() -> None:
    cap = persona_editor_selected_shelf_caption("business_area")
    assert cap is not None
    assert "**business_area**" in cap
    cap_dev = persona_editor_selected_shelf_caption("development_role")
    assert cap_dev is not None
    assert "**development_role**" in cap_dev
    assert persona_editor_selected_shelf_caption(None) is None
    assert persona_editor_selected_shelf_caption("") is None
    assert persona_editor_selected_shelf_caption("   ") is None


def test_persona_editor_display_name_draft_caption() -> None:
    cap = persona_editor_display_name_draft_caption("Commerce Bot")
    assert cap is not None
    assert "**12**" in cap
    assert persona_editor_display_name_draft_caption("   ") is None
    assert persona_editor_display_name_draft_caption(None) is None


def test_persona_editor_probation_status_draft_caption() -> None:
    cap = persona_editor_probation_status_draft_caption("probation")
    assert cap is not None
    assert "**probation**" in cap
    assert persona_editor_probation_status_draft_caption("   ") is None
    assert persona_editor_probation_status_draft_caption(None) is None


def test_persona_editor_probation_status_caption() -> None:
    cap = persona_editor_probation_status_caption(SNAPSHOT)
    assert cap is not None
    assert "promoted" in cap
    cap_prob = persona_editor_probation_status_caption(
        {"probation_status": "probation"},
    )
    assert cap_prob is not None
    assert "probation" in cap_prob
    assert persona_editor_probation_status_caption(None) is None
    assert persona_editor_probation_status_caption({}) is None
    assert persona_editor_probation_status_caption(
        {"probation_status": "unknown"},
    ) is None


def test_persona_editor_expected_version_caption() -> None:
    cap = persona_editor_expected_version_caption(SNAPSHOT)
    assert cap is not None
    assert "expected_version=**3**" in cap
    assert persona_editor_expected_version_caption(None) is None
    assert persona_editor_expected_version_caption({}) is None
    assert persona_editor_expected_version_caption({"version": 0}) is None


def test_persona_editor_diff_summary_caption_none_when_unchanged() -> None:
    assert persona_editor_diff_summary_caption(SNAPSHOT, dict(SNAPSHOT)) is None


def test_persona_editor_diff_summary_caption_single_field() -> None:
    edited = dict(SNAPSHOT, instructions="Updated brief.")
    cap = persona_editor_diff_summary_caption(SNAPSHOT, edited)
    assert cap is not None
    assert "1 field" in cap
    assert "instructions" in cap


def test_persona_editor_diff_summary_caption_multi_field_sorted() -> None:
    edited = dict(
        SNAPSHOT,
        instructions="Updated brief.",
        probation_status="probation",
    )
    cap = persona_editor_diff_summary_caption(SNAPSHOT, edited)
    assert cap is not None
    assert "2 fields" in cap
    assert cap.index("instructions") < cap.index("probation_status")


def test_persona_editor_diff_summary_caption_overflow_cap() -> None:
    edited = dict(SNAPSHOT)
    for i, field in enumerate(EDITABLE_FIELDS):
        edited[field] = f"v{i}"
    cap = persona_editor_diff_summary_caption(SNAPSHOT, edited)
    assert cap is not None
    assert "+1 more" in cap
    assert str(len(EDITABLE_FIELDS)) in cap


# Axis 3: parse_write_response on 200 returns ok=True + catalog


def test_parse_write_response_2xx_returns_catalog() -> None:
    body = {"version": 1, "business_area": [], "development_role": []}
    parsed = parse_write_response(200, body)
    assert parsed["ok"] is True
    assert parsed["catalog"] == body


# Axis 4: 409 version conflict flagged for UI


def test_parse_write_response_flags_version_conflict() -> None:
    body = {
        "code": "persona_version_conflict",
        "message": "expected_version does not match",
        "details": {"actual_version": 4},
    }
    parsed = parse_write_response(409, {"detail": body})
    assert parsed["ok"] is False
    assert parsed["version_conflict"] is True
    assert parsed["code"] == "persona_version_conflict"


def test_parse_write_response_409_without_version_code_is_not_version_conflict() -> None:
    body = {"code": "persona_already_exists", "message": "dup"}
    parsed = parse_write_response(409, {"detail": body})
    assert parsed["ok"] is False
    assert parsed["version_conflict"] is False


# Axis 5: 422 length-cap / validation surfaces structured error


def test_parse_write_response_422_surfaces_validation_error() -> None:
    body = {
        "code": "validation_error",
        "message": "request validation failed",
        "details": {"errors": [{"loc": ["body", "entry", "instructions"]}]},
    }
    parsed = parse_write_response(422, {"detail": body})
    assert parsed["ok"] is False
    assert parsed["status"] == 422
    assert parsed["code"] == "validation_error"
    assert parsed["details"]["errors"]


# Axis 6: find_persona_in_catalog handles missing/empty inputs


def test_find_persona_in_catalog_returns_none_for_missing_shelf_or_id() -> None:
    catalog = {
        "business_area": [{"id": "commerce", "display_name": "Commerce", "version": 1}],
        "development_role": [],
    }
    assert find_persona_in_catalog(catalog, "business_area", "ghost") is None
    assert find_persona_in_catalog(catalog, "archived", "commerce") is None
    assert find_persona_in_catalog(None, "business_area", "commerce") is None
    found = find_persona_in_catalog(catalog, "business_area", "commerce")
    assert found is not None
    assert found["id"] == "commerce"


def test_persona_field_metrics_non_empty_multiline_utf8() -> None:
    m = persona_field_metrics("  line1\nline2  \n")
    assert m["non_empty"] is True
    assert m["char_len"] == 11
    assert m["line_count"] == 2
    assert m["utf8_bytes"] == len(b"line1\nline2")


def test_persona_field_metrics_whitespace_only_is_not_non_empty() -> None:
    m = persona_field_metrics("  \n\t  ")
    assert m["non_empty"] is False
    assert m["char_len"] == 0


def test_persona_field_metrics_non_string() -> None:
    assert persona_field_metrics(None)["non_empty"] is False


def test_persona_editor_instructions_metrics_caption() -> None:
    cap = persona_editor_instructions_metrics_caption("hello\nworld")
    assert cap is not None
    assert "instructions draft" in cap
    assert "char(s)" in cap
    assert persona_editor_instructions_metrics_caption("") is None
    assert persona_editor_instructions_metrics_caption("   ") is None


def test_persona_editor_multiline_field_metrics_caption() -> None:
    cap = persona_editor_multiline_field_metrics_caption(
        "capability text\nline2",
        "",
    )
    assert cap is not None
    assert "capability_profile" in cap
    assert persona_editor_multiline_field_metrics_caption("", "") is None


def test_persona_list_field_line_counts_caption_counts_nonblank_lines() -> None:
    cap = persona_list_field_line_counts_caption(
        "tool_a\n\n tool_b ",
        "metric_one",
    )
    assert cap is not None
    assert "allowed_tools=2" in cap
    assert "success_metrics=1" in cap


def test_persona_list_field_line_counts_caption_none_when_both_empty() -> None:
    assert persona_list_field_line_counts_caption("", "  \n") is None
    assert persona_list_field_line_counts_caption(None, None) is None


def test_persona_editor_validation_issues_within_caps() -> None:
    assert (
        persona_editor_validation_issues(
            {
                "id": "p1",
                "instructions": "ok",
                "probation_status": "promoted",
            },
        )
        == []
    )


def test_persona_editor_validation_issues_instructions_over_limit() -> None:
    issues = persona_editor_validation_issues(
        {"instructions": "x" * (PERSONA_INSTRUCTIONS_MAX_CHARS + 1)},
    )
    assert len(issues) == 1
    assert "instructions" in issues[0]


def test_persona_editor_validation_issues_too_many_allowed_tools() -> None:
    tools = [f"tool_{i}" for i in range(PERSONA_ALLOWED_TOOLS_MAX_ENTRIES + 1)]
    issues = persona_editor_validation_issues({"allowed_tools": tools})
    assert len(issues) == 1
    assert "allowed_tools" in issues[0]


def test_persona_editor_validation_issues_invalid_probation_status() -> None:
    issues = persona_editor_validation_issues({"probation_status": "beta"})
    assert len(issues) == 1
    assert "probation_status" in issues[0]


def test_persona_editor_validation_issues_empty_create_id() -> None:
    issues = persona_editor_validation_issues({"id": "  "}, require_non_empty_id=True)
    assert any("id" in i for i in issues)


def test_persona_editor_validation_blocking_caption_and_table_rows() -> None:
    issues = ["id: must be non-empty", "persona editor: bad field"]
    cap = persona_editor_validation_blocking_caption(issues)
    assert cap is not None
    assert "2" in cap
    rows = persona_editor_validation_table_rows(issues)
    assert len(rows) == 2
    assert rows[0]["message"] == issues[0]
    assert persona_editor_validation_blocking_caption([]) is None
