from __future__ import annotations

import json
from pathlib import Path

import pytest

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


@pytest.mark.parametrize(
    ("deps", "pack_id"),
    [
        ({"next": "14"}, "next_js"),
        ({"nuxt": "3"}, "nuxt"),
        ({"@remix-run/react": "2"}, "remix"),
    ],
)
def test_detect_only_framework_packs(tmp_path: Path, deps: dict, pack_id: str) -> None:
    (tmp_path / "package.json").write_text(json.dumps({"dependencies": deps}), encoding="utf-8")
    assert detect_js_framework(tmp_path) == pack_id
    pack = load_framework_pack(pack_id)
    assert pack.get("id") == pack_id
    assert str(pack.get("writer_instructions") or "").strip()


@pytest.mark.parametrize(
    "pack_id",
    [
        "react_vite",
        "vue_vite",
        "angular_cli",
        "svelte_vite",
        "static_html",
        "spa_generic",
        "next_js",
        "nuxt",
        "remix",
    ],
)
def test_framework_pack_yaml_smoke(pack_id: str) -> None:
    pack = load_framework_pack(pack_id)
    assert pack.get("id") == pack_id
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
