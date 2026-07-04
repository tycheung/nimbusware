from __future__ import annotations

from pathlib import Path

from standards.bundles.python_hygiene import (
    check_config_module_loc,
    check_init_exports_only,
    check_pydantic_v2,
)


def test_config_module_loc_flags_oversized_settings(tmp_path: Path) -> None:
    settings = tmp_path / "settings.py"
    settings.write_text("\n".join(f"x_{i} = {i}" for i in range(300)), encoding="utf-8")
    result = check_config_module_loc(workspace=tmp_path, params={"max_loc": 250})
    assert result.passed is False
    assert "settings.py" in result.detail


def test_pydantic_v2_detects_validator_decorator(tmp_path: Path) -> None:
    model = tmp_path / "models.py"
    model.write_text(
        "from pydantic import BaseModel, validator\n\n"
        "class M(BaseModel):\n"
        "    @validator('x')\n"
        "    def v(cls, v): return v\n",
        encoding="utf-8",
    )
    result = check_pydantic_v2(workspace=tmp_path, params={})
    assert result.passed is False
    assert "@validator" in result.detail


def test_init_exports_only_allows_imports_only(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    init = pkg / "__init__.py"
    init.write_text("from .core import Widget\n__all__ = ['Widget']\n", encoding="utf-8")
    result = check_init_exports_only(workspace=tmp_path, params={"max_non_import_loc": 40})
    assert result.passed is True
