from __future__ import annotations

from collections.abc import Callable

from nimbusware_env.settings_catalog import SettingDef
from nimbusware_env.settings_catalog_extended.core_legacy_install import core_legacy_install_defs
from nimbusware_env.settings_catalog_extended.core_legacy_runtime import core_legacy_runtime_defs
from nimbusware_env.settings_catalog_extended.install import install_defs
from nimbusware_env.settings_catalog_extended.internal import internal_defs
from nimbusware_env.settings_catalog_extended.system import system_defs
from nimbusware_env.settings_catalog_extended.uc import uc_defs
from nimbusware_env.settings_catalog_extended.user import user_defs

SettingDefLoader = Callable[[], tuple[SettingDef, ...]]

_SETTING_DEF_LOADERS: tuple[SettingDefLoader, ...] = (
    lambda: core_legacy_install_defs() + core_legacy_runtime_defs(),
    uc_defs,
    install_defs,
    system_defs,
    user_defs,
    internal_defs,
)


def extended_defs() -> tuple[SettingDef, ...]:
    out: list[SettingDef] = []
    for loader in _SETTING_DEF_LOADERS:
        out.extend(loader())
    return tuple(out)
