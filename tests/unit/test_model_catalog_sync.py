from __future__ import annotations

import json
from pathlib import Path

from nimbusware_hw.catalog_sync import (
    build_catalog_from_source,
    catalog_info_from_path,
    merge_catalog,
    normalize_model_row,
    validate_catalog,
)


def test_normalize_model_row_odysseus_style() -> None:
    row = normalize_model_row(
        {
            "name": "qwen2.5-coder:14b",
            "parameters_b": 14,
            "context_length": 32768,
            "moe": False,
        },
    )
    assert row is not None
    assert row["id"] == "qwen2.5-coder:14b"
    assert row["params_b"] == 14.0
    assert row["context"] == 32768


def test_validate_catalog_rejects_duplicate() -> None:
    doc = {
        "version": 1,
        "models": [
            {"id": "a", "params_b": 7, "context": 8192},
            {"id": "a", "params_b": 8, "context": 8192},
        ],
    }
    assert any("duplicate" in e for e in validate_catalog(doc))


def test_merge_catalog_by_id() -> None:
    existing = {"version": 1, "models": [{"id": "old", "params_b": 3, "context": 4096}]}
    incoming = {"version": 2, "models": [{"id": "new", "params_b": 8, "context": 128000}]}
    merged = merge_catalog(existing, incoming)
    ids = {m["id"] for m in merged["models"]}
    assert ids == {"new", "old"}
    assert merged["version"] == 2


def test_build_catalog_from_source_merge(tmp_path: Path) -> None:
    raw = {
        "models": [
            {"id": "llama3.2:3b", "params_b": 3, "context": 128000},
        ],
    }
    existing = {"version": 1, "models": [{"id": "phi3:mini", "params_b": 4, "context": 128000}]}
    out = build_catalog_from_source(raw, existing=existing, merge=True)
    assert len(out["models"]) == 2
    assert validate_catalog(out) == []


def test_catalog_info_from_path(tmp_path: Path) -> None:
    path = tmp_path / "model_catalog.json"
    path.write_text(
        json.dumps({"version": 1, "models": [{"id": "x", "params_b": 1, "context": 8192}]}),
        encoding="utf-8",
    )
    info = catalog_info_from_path(path)
    assert info["model_count"] == 1
    assert info["version"] == 1
    assert info["updated_at"]


def test_sync_script_dry_run(tmp_path: Path) -> None:
    import subprocess
    import sys

    src = tmp_path / "src.json"
    src.write_text(
        json.dumps(
            {
                "version": 1,
                "models": [{"id": "test:7b", "params_b": 7, "context": 8192}],
            },
        ),
        encoding="utf-8",
    )
    script = Path(__file__).resolve().parents[2] / "scripts" / "codegen" / "sync_model_catalog.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--from-json", str(src), "--dry-run"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert not (tmp_path / "configs" / "hardware" / "model_catalog.json").exists()
