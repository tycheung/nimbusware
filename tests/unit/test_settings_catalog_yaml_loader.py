from __future__ import annotations

from nimbusware_env.settings_catalog import CATALOG
from nimbusware_env.settings_catalog_extended.core_legacy_runtime import core_legacy_runtime_defs


def test_core_legacy_runtime_settings_loaded_from_yaml() -> None:
    defs = core_legacy_runtime_defs()
    assert len(defs) >= 50
    assert CATALOG["NIMBUSWARE_USE_LLM"].key == "NIMBUSWARE_USE_LLM"
    assert CATALOG["NIMBUSWARE_SLICE_BUDGET_PRESET"].choices == ("tiny", "standard", "careful")
