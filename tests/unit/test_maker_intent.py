from __future__ import annotations

import pytest

from nimbusware_maker.intent import (
    build_requirements_artifact,
    plan_summary_from_requirements,
    requirements_from_run_created_metadata,
)


def test_build_requirements_artifact() -> None:
    artifact = build_requirements_artifact(
        business_prompt="Inventory tracker",
        clarifications=[
            {
                "question_id": "audience",
                "question": "Who?",
                "answer": "Shop staff",
            },
        ],
    )
    assert artifact["business_prompt"] == "Inventory tracker"
    assert len(artifact["clarifications"]) == 1
    assert "frozen_at" in artifact


def test_build_requirements_requires_prompt() -> None:
    with pytest.raises(ValueError, match="business_prompt"):
        build_requirements_artifact(business_prompt="  ")


def test_plan_summary_from_requirements() -> None:
    summary = plan_summary_from_requirements(
        {
            "business_prompt": "Inventory tracker",
            "clarifications": [
                {"question": "Who?", "answer": "Shop staff"},
            ],
        },
    )
    assert "Inventory tracker" in summary
    assert "Shop staff" in summary


def test_requirements_from_run_created_metadata() -> None:
    meta = {"requirements": {"business_prompt": "x"}}
    assert requirements_from_run_created_metadata(meta) == {"business_prompt": "x"}
