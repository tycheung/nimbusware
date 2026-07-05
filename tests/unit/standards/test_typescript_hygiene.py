from __future__ import annotations

from pathlib import Path

from standards.bundles.typescript_hygiene import check_barrel_exports, check_config_loc


def test_ts_config_loc_flags_large_config(tmp_path: Path) -> None:
    cfg = tmp_path / "src" / "config.ts"
    cfg.parent.mkdir(parents=True)
    cfg.write_text("\n".join(["export const x = 1;"] * 400), encoding="utf-8")
    result = check_config_loc(workspace=tmp_path, params={"max_loc": 300})
    assert not result.passed


def test_ts_barrel_exports_passes_reexport(tmp_path: Path) -> None:
    index = tmp_path / "index.ts"
    index.write_text("export { foo } from './foo.js';\n", encoding="utf-8")
    result = check_barrel_exports(workspace=tmp_path, params={"max_non_export_loc": 30})
    assert result.passed
