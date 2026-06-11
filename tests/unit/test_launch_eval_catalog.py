from __future__ import annotations

from pathlib import Path

import yaml


def test_launch_eval_catalog_lists_prompts_and_workspaces() -> None:
    catalog_path = Path(__file__).resolve().parents[2] / "configs" / "launch_eval" / "catalog.yaml"
    doc = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    prompt_ids = {p["id"] for p in doc.get("prompts", [])}
    assert prompt_ids >= {
        "basic_crm",
        "todo_api",
        "static_site",
        "contacts_api",
        "patch_go_hotfix",
        "patch_jvm_hotfix",
    }
    workspaces = doc.get("default_workspaces") or []
    assert any("tiny_python_app" in str(w) for w in workspaces)
    assert any("tiny_web_app" in str(w) for w in workspaces)
    assert any("tiny_api_app" in str(w) for w in workspaces)
