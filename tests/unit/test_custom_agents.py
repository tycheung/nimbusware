"""Custom agent registry."""

from __future__ import annotations

from pathlib import Path

from nimbusware_extensions.custom_agents import CustomAgent, CustomAgentRegistry


def test_registry_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "registry.yaml"
    reg = CustomAgentRegistry(
        {
            "a1": CustomAgent(
                id="a1",
                display_name="Agent One",
                system_prompt="You are agent one.",
            ),
        },
    )
    reg.save(path)
    loaded = CustomAgentRegistry.load(path)
    assert loaded.get("a1") is not None
    assert loaded.get("a1").display_name == "Agent One"


def test_upsert_increments_version() -> None:
    reg = CustomAgentRegistry(
        {
            "a1": CustomAgent(
                id="a1",
                display_name="A",
                system_prompt="p1",
                version=2,
            ),
        },
    )
    reg.upsert(
        CustomAgent(id="a1", display_name="A", system_prompt="p2"),
    )
    assert reg.get("a1") is not None
    assert reg.get("a1").version == 3
