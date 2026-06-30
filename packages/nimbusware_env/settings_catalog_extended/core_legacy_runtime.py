from __future__ import annotations

from nimbusware_env.settings_catalog import SettingDef
from nimbusware_env.settings_catalog_extended.yaml_loader import load_setting_defs_yaml


def core_legacy_runtime_defs() -> tuple[SettingDef, ...]:
    return load_setting_defs_yaml("core_legacy_runtime")
