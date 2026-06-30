from __future__ import annotations

from pathlib import Path

from agent_core.yaml_io import load_yaml
from nimbusware_env import find_repo_root
from nimbusware_env.settings_catalog import SettingDef, SettingKind, SettingScope

_SCOPE = {
    "install": SettingScope.INSTALL,
    "system": SettingScope.SYSTEM,
    "user": SettingScope.USER,
    "run": SettingScope.RUN,
    "internal": SettingScope.INTERNAL,
}
_KIND = {
    "bool": SettingKind.BOOL,
    "int": SettingKind.INT,
    "str": SettingKind.STR,
    "enum": SettingKind.ENUM,
}


def _settings_catalog_dir() -> Path:
    return find_repo_root() / "configs" / "settings_catalog"


def load_setting_defs_yaml(name: str) -> tuple[SettingDef, ...]:
    path = _settings_catalog_dir() / f"{name}.yaml"
    raw = load_yaml(path)
    if not isinstance(raw, dict):
        msg = f"settings catalog yaml must be a mapping: {path}"
        raise ValueError(msg)
    rows = raw.get("settings")
    if not isinstance(rows, list):
        msg = f"settings catalog yaml missing settings list: {path}"
        raise ValueError(msg)
    out: list[SettingDef] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        scope = _SCOPE[str(row["scope"])]
        kind = _KIND[str(row["kind"])]
        choices_raw = row.get("choices")
        choices: tuple[str, ...] = ()
        if isinstance(choices_raw, list):
            choices = tuple(str(c) for c in choices_raw)
        out.append(
            SettingDef(
                str(row["key"]),
                scope,
                kind,
                str(row.get("default", "")),
                str(row.get("label", "")),
                str(row.get("description", "")),
                str(row.get("group", "")),
                choices=choices,
                admin_editable=bool(row.get("admin_editable", True)),
                user_editable=bool(row.get("user_editable", True)),
            )
        )
    return tuple(out)
