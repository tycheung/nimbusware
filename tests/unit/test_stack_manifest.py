from __future__ import annotations

from pathlib import Path

from env import find_repo_root
from maker.stack_manifest import (
    freeze_manifest,
    parse_stack_manifest,
    validate_frozen_manifest,
)


def test_parse_stack_manifest() -> None:
    manifest = parse_stack_manifest(
        {
            "surfaces": ["api", "web"],
            "stacks": {"api": "fastapi_python", "web": "react_vite"},
            "hosting": "local",
        },
    )
    assert manifest.surfaces == ("api", "web")
    assert manifest.stacks["web"] == "react_vite"


def test_freeze_manifest_sets_timestamp() -> None:
    raw = {
        "surfaces": ["api", "web"],
        "stacks": {"api": "fastapi_python", "web": "react_vite"},
    }
    frozen = freeze_manifest(raw, answers={"client_form": "Web app"}, confirmed=True)
    assert frozen.frozen_at
    assert frozen.confirmed is True
    assert frozen.discovery_summary.get("client_form") == "Web app"


def test_validate_frozen_manifest_ok() -> None:
    repo = find_repo_root(start=Path(__file__).resolve().parents[1])
    manifest = freeze_manifest(
        {
            "surfaces": ["api", "web"],
            "stacks": {"api": "fastapi_python", "web": "react_vite"},
        },
        confirmed=True,
    )
    assert validate_frozen_manifest(manifest, repo_root=repo) == []


def test_validate_frozen_manifest_unknown_stack() -> None:
    manifest = parse_stack_manifest(
        {"surfaces": ["api"], "stacks": {"api": "not_a_real_stack"}},
    )
    errors = validate_frozen_manifest(manifest)
    assert errors
