from __future__ import annotations

from nimbusware_env.settings_catalog import SettingDef
from nimbusware_env.settings_catalog_extended.core_legacy_install import core_legacy_install_defs
from nimbusware_env.settings_catalog_extended.core_legacy_runtime import core_legacy_runtime_defs


def core_legacy_defs() -> tuple[SettingDef, ...]:
    return core_legacy_install_defs() + core_legacy_runtime_defs()
