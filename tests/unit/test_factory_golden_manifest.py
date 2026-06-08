import importlib.util
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _load_factory_weekly():
    path = REPO / "scripts" / "run_factory_weekly_ci.py"
    spec = importlib.util.spec_from_file_location("run_factory_weekly_ci", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_factory_golden_manifest_has_catalog_flows() -> None:
    mod = _load_factory_weekly()
    entries = mod.load_factory_golden_entries(REPO)
    assert len(entries) >= 5
    flow_ids = {str(e.get("flow_id")) for e in entries}
    assert {"crm", "contacts_api", "todo_api", "static_site"}.issubset(flow_ids)
    tiers = {str(e.get("factory_tier")) for e in entries}
    assert {"T1", "T2", "T3"}.issubset(tiers)


def test_factory_golden_manifest_entries_pass() -> None:
    mod = _load_factory_weekly()
    entries = mod.load_factory_golden_entries(REPO)
    for spec in entries:
        result = mod.run_factory_golden_entry(spec, repo_root=REPO)
        assert result.get("passed") is True, result
