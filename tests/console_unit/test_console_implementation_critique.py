from __future__ import annotations

from console.implementation_critique_display import (
    implementation_critique_caption,
    implementation_critique_table_rows,
)


def test_implementation_critique_caption_empty() -> None:
    assert "No implementation critic" in implementation_critique_caption({})


def test_implementation_critique_table_rows() -> None:
    rows = implementation_critique_table_rows(
        {
            "security_critique": {"verdict": "PASS", "failing_critics": []},
        },
    )
    assert len(rows) == 1
    assert rows[0]["Verdict"] == "PASS"
