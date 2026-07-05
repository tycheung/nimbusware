from __future__ import annotations

from uuid import uuid4

from standards.persist import apply_standards_at_run_start, standards_profile_from_rows
from standards.preset_defaults import workspace_standards_is_custom


class _Store:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def append(self, event) -> None:
        self.events.append(
            {
                "event_type": event.event_type.value,
                "payload": event.payload.model_dump(),
                "metadata": event.metadata,
            },
        )


def test_apply_default_standards_at_run_start(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    store = _Store()
    profile = apply_standards_at_run_start(
        store,
        uuid4(),
        workspace=tmp_path,
        enforcement_level=5,
    )
    assert profile is not None
    assert profile.custom is False
    assert "python-agent-hygiene" in profile.bundle_ids
    assert not (tmp_path / ".nimbusware" / "standards.yaml").exists()
    resolved = standards_profile_from_rows(store.events, workspace=tmp_path)
    assert resolved.facade_id == "python-fastapi"


def test_custom_workspace_overlay_not_overridden(tmp_path) -> None:
    overlay_dir = tmp_path / ".nimbusware"
    overlay_dir.mkdir()
    (overlay_dir / "standards.yaml").write_text(
        "facade_id: python-fastapi\nbundles:\n  - oop-solid\ncustom: true\n",
        encoding="utf-8",
    )
    assert workspace_standards_is_custom(tmp_path)
    store = _Store()
    profile = apply_standards_at_run_start(
        store,
        uuid4(),
        workspace=tmp_path,
        enforcement_level=5,
    )
    assert profile is not None
    assert profile.custom is True
    assert profile.bundle_ids == ("oop-solid",)
