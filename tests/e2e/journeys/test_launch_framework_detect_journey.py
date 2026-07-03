from __future__ import annotations

import json
from pathlib import Path

import pytest

from orchestrator.js_framework_detect import detect_js_framework, load_framework_pack
from orchestrator.launch_test_stage import build_launch_test_writer_prompt

pytestmark = [pytest.mark.e2e, pytest.mark.e2e_journey]

_FRAMEWORK_FIXTURES: list[tuple[str, dict, str | None]] = [
    ("react_vite", {"react": "18", "vite": "5"}, None),
    ("vue_vite", {"vue": "3", "vite": "5"}, None),
    ("angular_cli", {"@angular/core": "17"}, None),
    ("svelte_vite", {"svelte": "4", "vite": "5"}, None),
    ("next_js", {"next": "14"}, None),
    ("nuxt", {"nuxt": "3"}, None),
    ("remix", {"@remix-run/react": "2"}, None),
    ("static_html", {}, "index.html"),
    ("spa_generic", {"unknown-spa-runtime": "0"}, None),
]


@pytest.mark.parametrize(("pack_id", "deps", "extra_file"), _FRAMEWORK_FIXTURES)
def test_launch_framework_detect_and_writer_prompt(
    tmp_path: Path,
    pack_id: str,
    deps: dict,
    extra_file: str | None,
) -> None:
    if deps:
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": deps}),
            encoding="utf-8",
        )
    if extra_file:
        (tmp_path / extra_file).write_text(
            "<html><body><h1>ok</h1></body></html>", encoding="utf-8"
        )

    detected = detect_js_framework(tmp_path)
    if pack_id == "spa_generic":
        assert detected == "spa_generic"
    else:
        assert detected == pack_id

    pack = load_framework_pack(detected)
    assert pack.get("id") == detected
    prompt = build_launch_test_writer_prompt(tmp_path)
    assert detected in prompt or str(pack.get("display_name") or "") in prompt
