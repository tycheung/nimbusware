from __future__ import annotations

import pytest

from nimbusware_hw.fit import rank_models
from nimbusware_hw.fixtures import FIXTURE_NAMES, fixture_probe
from nimbusware_hw.governor import ResourceGovernor, governor_for_profile
from nimbusware_hw.probe import classify_tier, probe_hardware
from nimbusware_hw.profile import profile_from_probe


def test_classify_tier() -> None:
    assert classify_tier(ram_total_gb=64, cpu_count=16) == "strong"
    assert classify_tier(ram_total_gb=16, cpu_count=6) == "medium"
    assert classify_tier(ram_total_gb=8, cpu_count=2) == "weak"


@pytest.mark.parametrize("name", sorted(FIXTURE_NAMES))
def test_fixture_probe_tiers(name: str) -> None:
    raw = fixture_probe(name)
    profile = profile_from_probe(raw)
    assert profile.tier == name


def test_governor_caps_differ_by_fixture_tier() -> None:
    weak = governor_for_profile(profile_from_probe(fixture_probe("weak")))
    strong = governor_for_profile(profile_from_probe(fixture_probe("strong")))
    assert weak.max_parallel_writer_stages < strong.max_parallel_writer_stages
    assert weak.max_system_ram_pct <= strong.max_system_ram_pct


def test_governor_metadata_roundtrip() -> None:
    gov = ResourceGovernor(hardware_tier="medium", max_parallel_writer_stages=2)
    meta = gov.to_metadata()
    assert meta["hardware_tier"] == "medium"
    assert meta["max_parallel_writer_stages"] == 2


def test_rank_models_includes_routing_allowlist() -> None:
    from nimbusware_env import find_repo_root

    root = find_repo_root()
    profile = profile_from_probe(fixture_probe("medium"))
    ranked = rank_models(root, profile)
    assert ranked
    assert all(r["fit_level"] in ("perfect", "good", "marginal", "too_tight") for r in ranked)


def test_probe_hardware_fixture_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_HW_FIXTURE", "weak")
    from nimbusware_hw import cache

    cache._cached = None
    raw = probe_hardware()
    assert raw.get("tier") == "weak"
    cache._cached = None
    monkeypatch.delenv("NIMBUSWARE_HW_FIXTURE", raising=False)
