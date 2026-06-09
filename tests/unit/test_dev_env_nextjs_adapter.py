from __future__ import annotations

import json
from pathlib import Path

from nimbusware_orchestrator.dev_env_adapters import resolve_adapter_name


def test_resolve_nextjs_adapter_when_next_dependency(tmp_path: Path) -> None:
    ws = tmp_path / "next-app"
    ws.mkdir()
    (ws / "package.json").write_text(
        json.dumps({"dependencies": {"next": "14.0.0", "react": "18.0.0"}}),
        encoding="utf-8",
    )
    (ws / "pages").mkdir()
    (ws / "pages" / "index.tsx").write_text(
        "export default function Home() { return null }", encoding="utf-8"
    )
    assert resolve_adapter_name(ws) == "nextjs_dev"


def test_resolve_npm_dev_for_vite_spa(tmp_path: Path) -> None:
    ws = tmp_path / "vite-app"
    ws.mkdir()
    (ws / "package.json").write_text(
        json.dumps({"scripts": {"dev": "vite"}, "devDependencies": {"vite": "5.0.0"}}),
        encoding="utf-8",
    )
    (ws / "index.html").write_text(
        '<html><body><div id="root"></div></body></html>', encoding="utf-8"
    )
    assert resolve_adapter_name(ws) == "npm_dev"
