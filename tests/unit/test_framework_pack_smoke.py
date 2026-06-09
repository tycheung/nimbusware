from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.js_framework_detect import detect_js_framework, load_framework_pack


def test_react_vite_pack_smoke(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {"dependencies": {"react": "18"}, "devDependencies": {"vite": "5"}},
        ),
        encoding="utf-8",
    )
    pack_id = detect_js_framework(tmp_path)
    assert pack_id == "react_vite"
    pack = load_framework_pack(pack_id)
    assert pack.get("id") == "react_vite"
    assert str(pack.get("writer_instructions") or "").strip()


def test_vue_vite_pack_smoke(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"vue": "3"}, "devDependencies": {"vite": "5"}}),
        encoding="utf-8",
    )
    pack_id = detect_js_framework(tmp_path)
    assert pack_id == "vue_vite"
    pack = load_framework_pack(pack_id)
    assert pack.get("id") == "vue_vite"
    assert str(pack.get("writer_instructions") or "").strip()
