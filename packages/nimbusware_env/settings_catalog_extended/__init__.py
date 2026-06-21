from __future__ import annotations

from nimbusware_env.settings_catalog import SettingDef
from nimbusware_env.settings_catalog_extended.core_legacy import core_legacy_defs
from nimbusware_env.settings_catalog_extended.install import install_defs
from nimbusware_env.settings_catalog_extended.internal import internal_defs
from nimbusware_env.settings_catalog_extended.system import system_defs
from nimbusware_env.settings_catalog_extended.uc import uc_defs
from nimbusware_env.settings_catalog_extended.user import user_defs


def extended_defs() -> tuple[SettingDef, ...]:
    return (
        core_legacy_defs()
        + uc_defs()
        + install_defs()
        + system_defs()
        + user_defs()
        + internal_defs()
    )
