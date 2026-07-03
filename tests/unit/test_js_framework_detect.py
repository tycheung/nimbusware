from __future__ import annotations

import json
from pathlib import Path

from orchestrator.js_framework_detect import detect_js_framework, load_framework_pack


def test_detect_react_vite_from_frontend_package(tmp_path: Path) -> None:
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        json.dumps(
            {"dependencies": {"react": "18", "react-dom": "18"}, "devDependencies": {"vite": "5"}}
        ),
        encoding="utf-8",
    )
    assert detect_js_framework(tmp_path) == "react_vite"


def test_detect_vue_vite(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"vue": "3"}, "devDependencies": {"vite": "5"}}),
        encoding="utf-8",
    )
    assert detect_js_framework(tmp_path) == "vue_vite"


def test_load_react_vite_pack() -> None:
    pack = load_framework_pack("react_vite")
    assert pack.get("id") == "react_vite"
    assert "writer_instructions" in pack
