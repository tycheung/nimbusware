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


def test_factory_golden_manifest_has_t2_and_t3_entries() -> None:
    mod = _load_factory_weekly()
    entries = mod.load_factory_golden_entries(REPO)
    assert len(entries) >= 2
    tiers = {str(e.get("factory_tier")) for e in entries}
    assert "T2" in tiers and "T3" in tiers


def test_factory_golden_manifest_entries_pass() -> None:
    mod = _load_factory_weekly()
    entries = mod.load_factory_golden_entries(REPO)
    for spec in entries:
        result = mod.run_factory_golden_entry(spec, repo_root=REPO)
        assert result.get("passed") is True, result
