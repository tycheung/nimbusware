from __future__ import annotations

from pathlib import Path

from orchestrator.put_runtime import detect_put_stack


def test_detect_fullstack_monorepo(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\ndependencies = ['fastapi']\n", encoding="utf-8"
    )
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8"
    )
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "package.json").write_text(
        '{"dependencies":{"react":"18","vite":"5"}}', encoding="utf-8"
    )
    (frontend / "index.html").write_text('<html><div id="root"></div></html>', encoding="utf-8")
    assert detect_put_stack(tmp_path) == "fullstack"
