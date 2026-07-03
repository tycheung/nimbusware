from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_EXT = Path(__file__).resolve().parents[2] / "extensions" / "nimbusware-status"


def _npm() -> str | None:
    return shutil.which("npm.cmd") or shutil.which("npm")


def test_extension_discipline_routes_match_collab_catalog() -> None:
    npm = _npm()
    if npm is None:
        return
    subprocess.run([npm, "run", "compile"], cwd=_EXT, check=True, capture_output=True, text=True)
    script = """
const { parseDisciplineMentions, disciplineRoutes } = require('./out/discipline_routes.js');
const out = {
  mentions: parseDisciplineMentions('Please @fe fix the form'),
  routes: disciplineRoutes('@backend and @qa review'),
  solo: disciplineRoutes('no mentions', 'backend'),
};
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", script],
        cwd=_EXT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    data = json.loads(proc.stdout.strip())
    assert data["mentions"] == ["frontend"]
    assert data["routes"][0]["taxonomy_key"] == "backend_writer"
    assert data["routes"][0]["source"] == "mention"
    assert data["solo"][0]["source"] == "solo_hat"

    from maker.collab_disciplines import parse_discipline_mentions

    assert parse_discipline_mentions("Please @fe fix the form") == data["mentions"]
