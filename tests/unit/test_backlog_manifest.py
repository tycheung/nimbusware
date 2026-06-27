from __future__ import annotations

from nimbusware_orchestrator.backlog_generator import generate_heuristic_backlog
from nimbusware_orchestrator.backlog_manifest import (
    manifest_template_id,
    validate_manifest_backlog,
)


def _fullstack_requirements() -> dict:
    return {
        "prompt": "Build a todo app with API and web UI",
        "stack_manifest": {
            "surfaces": ["api", "web"],
            "stacks": {"api": "fastapi_python", "web": "react_vite"},
            "confirmed": True,
        },
    }


def test_manifest_template_id_fullstack() -> None:
    assert manifest_template_id(_fullstack_requirements()) == "fullstack_todo"


def test_generate_heuristic_backlog_uses_fullstack_template() -> None:
    backlog = generate_heuristic_backlog(
        "run-fs", requirements=_fullstack_requirements(), max_slices=20
    )
    surfaces = {
        str(sl.surface_id or "")
        for epic in backlog.epics
        for feature in epic.features
        for sl in feature.slices
    }
    assert "api" in surfaces
    assert "web" in surfaces


def test_validate_manifest_backlog_missing_web() -> None:
    backlog = generate_heuristic_backlog(
        "run-api-only",
        requirements={
            "prompt": "API only",
            "stack_manifest": {
                "surfaces": ["api"],
                "stacks": {"api": "fastapi_python"},
            },
        },
        max_slices=5,
    )
    errors = validate_manifest_backlog(
        backlog,
        {
            "stack_manifest": {
                "surfaces": ["api", "web"],
                "stacks": {"api": "fastapi_python", "web": "react_vite"},
            },
        },
    )
    assert errors
