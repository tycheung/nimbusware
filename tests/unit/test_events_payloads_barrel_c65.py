from __future__ import annotations

import importlib

import agent_core.models.events_payloads as barrel


def test_events_payloads_c65_barrel_exports_importable() -> None:
    domain_modules = (
        "events_payloads_base",
        "events_payloads_run",
        "events_payloads_stage",
        "events_payloads_campaign",
    )
    domain_names: set[str] = set()
    for mod_name in domain_modules:
        mod = importlib.import_module(f"agent_core.models.{mod_name}")
        for name in dir(mod):
            if name.startswith("_"):
                continue
            domain_names.add(name)
    assert set(barrel.__all__) <= domain_names
    for name in barrel.__all__:
        assert hasattr(barrel, name)
