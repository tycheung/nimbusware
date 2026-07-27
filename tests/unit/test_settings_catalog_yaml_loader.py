from __future__ import annotations

from pathlib import Path

from env.settings_catalog import CATALOG
from env.settings_catalog_extended import yaml_loader
from env.settings_catalog_extended.core_legacy_runtime import core_legacy_runtime_defs


def test_core_legacy_runtime_settings_loaded_from_yaml() -> None:
    defs = core_legacy_runtime_defs()
    assert len(defs) >= 50
    assert CATALOG["NIMBUSWARE_USE_LLM"].key == "NIMBUSWARE_USE_LLM"
    assert CATALOG["NIMBUSWARE_SLICE_BUDGET_PRESET"].choices == ("tiny", "standard", "careful")


def test_settings_catalog_dir_prefers_frozen_meipass(
    tmp_path: Path, monkeypatch
) -> None:
    bundled = tmp_path / "mei" / "configs" / "settings_catalog"
    bundled.mkdir(parents=True)
    (bundled / "core_legacy_runtime.yaml").write_text("settings: []\n", encoding="utf-8")
    monkeypatch.setattr(yaml_loader.sys, "frozen", True, raising=False)
    monkeypatch.setattr(yaml_loader.sys, "_MEIPASS", str(tmp_path / "mei"), raising=False)
    monkeypatch.setattr(
        yaml_loader.sys,
        "executable",
        str(tmp_path / "elsewhere" / "NimbuswareLauncher.exe"),
    )
    assert yaml_loader._settings_catalog_dir() == bundled
