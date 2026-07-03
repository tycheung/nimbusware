from __future__ import annotations

from pathlib import Path

from orchestrator.slice_symbol_sketch import build_symbol_sketch


def test_symbol_sketch_lists_class_and_def() -> None:
    root = Path(__file__).resolve().parents[1] / "fixtures" / "slice_symbols"
    sketch = build_symbol_sketch(root, ["sample.py"], max_chars=2000)
    assert "class Widget" in sketch
    assert "def helper" in sketch
    assert "sample.py" in sketch
