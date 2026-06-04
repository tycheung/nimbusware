from __future__ import annotations

from pathlib import Path

import yaml

MATRIX = Path(__file__).resolve().parent / "parity_matrix.yaml"


def _load() -> dict:
    return yaml.safe_load(MATRIX.read_text(encoding="utf-8"))


def test_parity_matrix_has_maker_rows() -> None:
    data = _load()
    assert len(data.get("maker", [])) >= 30


def test_parity_matrix_web_true_items_exist() -> None:
    data = _load()
    web_true = [r for r in data.get("maker", []) if r.get("web") is True]
    assert any(r["id"] == "shell_loads" for r in web_true)
