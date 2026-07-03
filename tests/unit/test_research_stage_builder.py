from __future__ import annotations

from pathlib import Path

from research.stage_builder import (
    discover_workspace_patterns,
    domain_brief_summary,
    infer_domain_tag,
    select_research_patterns,
)


def test_infer_domain_tag_from_prompt() -> None:
    assert infer_domain_tag({"business_prompt": "Build a CRM for sales"}) == "crm"
    assert infer_domain_tag(None) == "general"


def test_domain_brief_summary_lists_journeys() -> None:
    text = domain_brief_summary(
        {"business_prompt": "Users sign in. They manage contacts. They export reports."},
        domain_tag="crm",
    )
    assert "sign in" in text.lower() or "contacts" in text.lower()


def test_discover_workspace_patterns_finds_python(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("app = 1\n", encoding="utf-8")
    patterns = discover_workspace_patterns(tmp_path)
    assert patterns
    assert any("app.py" in (p.get("paths") or []) for p in patterns)


def test_select_research_patterns_greenfield_when_empty(tmp_path: Path) -> None:
    patterns = select_research_patterns(tmp_path, requirements={"business_prompt": "todo app"})
    assert patterns
    assert patterns[0]["repo_url"].startswith("requirements://")
