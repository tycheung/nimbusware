from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from hermes_extensions import (
    BundleCatalog,
    EscalationPolicy,
    PersonaShelf,
    assert_workflow_bundle_map_ids_resolve,
    bundle_faiss_index_ready,
    search_bundles,
)
from hermes_extensions.phase2 import ModuleIntegrator, SecurityScanner, UniversalCritiqueRouter
from hermes_orchestrator.ingress import assert_bundle_catalog_maps_resolve
from hermes_orchestrator.registry import RoleRegistry
from nimbusware_env import find_repo_root

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])
CRITIQUE_PAIRINGS_YAML = ROOT / "configs" / "personas" / "critique_pairings.yaml"


def test_bundle_catalog_loads() -> None:
    cat = BundleCatalog(ROOT / "configs" / "bundles" / "catalog.yaml")
    bundles = cat.list_bundles()
    assert any(b.get("id") == "auth-rbac-starter" for b in bundles)


def test_bundle_catalog_maps_resolve_repository_catalog() -> None:
    path = ROOT / "configs" / "bundles" / "catalog.yaml"
    assert_workflow_bundle_map_ids_resolve(path)
    assert_bundle_catalog_maps_resolve(ROOT)


def test_bundle_catalog_maps_reject_unknown_bundle_id(tmp_path: Path) -> None:
    cat = ROOT / "configs" / "bundles" / "catalog.yaml"
    p = tmp_path / "catalog.yaml"
    raw = cat.read_text(encoding="utf-8")
    corrupted = raw.replace("default: auth-rbac-starter", "default: no-such-bundle")
    p.write_text(corrupted, encoding="utf-8")
    with pytest.raises(ValueError, match="unknown bundle id"):
        assert_workflow_bundle_map_ids_resolve(p)


def test_bundle_catalog_search_tags() -> None:
    cat = BundleCatalog(ROOT / "configs" / "bundles" / "catalog.yaml")
    hits = cat.search("auth rbac", k=2)
    assert hits and hits[0].get("id") == "auth-rbac-starter"


def test_bundle_catalog_search_prefers_billing_for_stripe_query() -> None:
    cat = BundleCatalog(ROOT / "configs" / "bundles" / "catalog.yaml")
    hits = cat.search("stripe billing", k=2)
    assert hits and hits[0].get("id") == "billing-stripe"


def test_bundle_catalog_search_zero_match_returns_first_bundles() -> None:
    cat = BundleCatalog(ROOT / "configs" / "bundles" / "catalog.yaml")
    hits = cat.search("no-matching-terms-xyz", k=1)
    assert len(hits) == 1
    assert hits[0].get("id") == "auth-rbac-starter"


def test_search_bundles_repo_root_matches_bundle_catalog() -> None:
    q = "rbac"
    cat = BundleCatalog(ROOT / "configs" / "bundles" / "catalog.yaml")
    assert search_bundles(ROOT, q, k=3) == cat.search(q, k=3)


def test_search_bundles_missing_catalog_returns_empty(tmp_path: Path) -> None:
    assert search_bundles(tmp_path, "auth", k=5) == []


def test_search_bundles_tag_match_without_faiss_index(tmp_path: Path) -> None:
    """No ``configs/bundles/index`` files → :func:`search_bundles` uses tag overlap."""
    catp = tmp_path / "configs" / "bundles" / "catalog.yaml"
    catp.parent.mkdir(parents=True)
    catp.write_text(
        "bundles:\n  - id: zed-alpha\n    tags: [zed]\n  - id: zed-beta\n    tags: [other]\n",
        encoding="utf-8",
    )
    hits = search_bundles(tmp_path, "zed", k=5)
    assert hits and hits[0].get("id") == "zed-alpha"


def test_bundle_faiss_index_ready_false_when_index_missing(tmp_path: Path) -> None:
    """Empty repo root has no index files, so the helper must return ``False``."""
    assert bundle_faiss_index_ready(tmp_path) is False


def test_bundle_faiss_index_ready_true_when_both_files_present(tmp_path: Path) -> None:
    """Both ``faiss.index`` and ``bundle_order.json`` must exist to be ready."""
    idx_dir = tmp_path / "configs" / "bundles" / "index"
    idx_dir.mkdir(parents=True)
    (idx_dir / "faiss.index").write_bytes(b"\x00")
    (idx_dir / "bundle_order.json").write_text("[]", encoding="utf-8")
    assert bundle_faiss_index_ready(tmp_path) is True


def test_bundle_faiss_index_ready_false_when_only_one_file(tmp_path: Path) -> None:
    """Partial state (only one of the two files) must not report ready."""
    idx_dir = tmp_path / "configs" / "bundles" / "index"
    idx_dir.mkdir(parents=True)
    (idx_dir / "faiss.index").write_bytes(b"\x00")
    assert bundle_faiss_index_ready(tmp_path) is False
    (idx_dir / "faiss.index").unlink()
    (idx_dir / "bundle_order.json").write_text("[]", encoding="utf-8")
    assert bundle_faiss_index_ready(tmp_path) is False


def test_persona_shelf() -> None:
    shelf = PersonaShelf(ROOT / "configs" / "personas" / "shelves.yaml")
    assert shelf.list_personas("business_area")


def test_persona_shelf_all_persona_ids() -> None:
    shelf = PersonaShelf(ROOT / "configs" / "personas" / "shelves.yaml")
    assert shelf.all_persona_ids() == frozenset({"commerce", "backend_engineer"})


def test_persona_shelf_validate_structure_accepts_repository_shelves() -> None:
    shelf = PersonaShelf(ROOT / "configs" / "personas" / "shelves.yaml")
    shelf.validate_structure()


def test_persona_shelf_validate_structure_rejects_empty_development_role(
    tmp_path: Path,
) -> None:
    p = tmp_path / "shelves.yaml"
    p.write_text(
        "version: 1\nbusiness_area:\n  - id: commerce\ndevelopment_role: []\n",
        encoding="utf-8",
    )
    shelf = PersonaShelf(p)
    with pytest.raises(ValueError, match="development_role"):
        shelf.validate_structure()


def test_persona_shelf_validate_structure_rejects_missing_id(tmp_path: Path) -> None:
    p = tmp_path / "shelves.yaml"
    p.write_text(
        "version: 1\nbusiness_area:\n  - display_name: X\ndevelopment_role:\n  - id: ok\n",
        encoding="utf-8",
    )
    shelf = PersonaShelf(p)
    with pytest.raises(ValueError, match="id"):
        shelf.validate_structure()


def test_assert_persona_shelves_valid_accepts_repo_root() -> None:
    from hermes_orchestrator.ingress import assert_persona_shelves_valid

    assert_persona_shelves_valid(ROOT)


def test_assert_agent_evaluator_persona_in_shelves_rejects_unknown(tmp_path: Path) -> None:
    from hermes_orchestrator.ingress import assert_agent_evaluator_persona_in_shelves

    (tmp_path / "configs/workflows").mkdir(parents=True)
    shutil.copytree(ROOT / "configs/personas", tmp_path / "configs/personas")
    wf = tmp_path / "configs/workflows/x_eval.yaml"
    wf.write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n  persona_id: no_shelf_match\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="agent_evaluator"):
        assert_agent_evaluator_persona_in_shelves(tmp_path, "x_eval")


def test_assert_agent_evaluator_persona_allows_reserved_default(tmp_path: Path) -> None:
    from hermes_orchestrator.ingress import assert_agent_evaluator_persona_in_shelves

    (tmp_path / "configs/workflows").mkdir(parents=True)
    shutil.copytree(ROOT / "configs/personas", tmp_path / "configs/personas")
    wf = tmp_path / "configs/workflows/y_eval.yaml"
    wf.write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n  persona_id: default\n",
        encoding="utf-8",
    )
    assert_agent_evaluator_persona_in_shelves(tmp_path, "y_eval")


def test_assert_agent_evaluator_persona_allows_unknown_when_auto_create_configured(
    tmp_path: Path,
) -> None:
    from hermes_orchestrator.ingress import assert_agent_evaluator_persona_in_shelves

    (tmp_path / "configs/workflows").mkdir(parents=True)
    shutil.copytree(ROOT / "configs/personas", tmp_path / "configs/personas")
    wf = tmp_path / "configs/workflows/ac_gate.yaml"
    wf.write_text(
        "version: 1\nagent_evaluator:\n  enabled: true\n"
        "  persona_id: not_in_catalog_yet\n"
        "  auto_create_persona:\n"
        "    enabled: true\n"
        "    shelf: business_area\n"
        "    display_name: Will create\n",
        encoding="utf-8",
    )
    assert_agent_evaluator_persona_in_shelves(tmp_path, "ac_gate")


def test_assert_agent_evaluator_skips_when_disabled(tmp_path: Path) -> None:
    from hermes_orchestrator.ingress import assert_agent_evaluator_persona_in_shelves

    (tmp_path / "configs/workflows").mkdir(parents=True)
    shutil.copytree(ROOT / "configs/personas", tmp_path / "configs/personas")
    wf = tmp_path / "configs/workflows/z_eval.yaml"
    wf.write_text(
        "version: 1\nagent_evaluator:\n  enabled: false\n  persona_id: nonsense\n",
        encoding="utf-8",
    )
    assert_agent_evaluator_persona_in_shelves(tmp_path, "z_eval")


def test_escalation_policy() -> None:
    pol = EscalationPolicy(ROOT / "configs" / "escalation" / "policy.yaml")
    d = pol.as_dict()
    assert d.get("max_retries_per_stage") == 3
    assert d.get("verification", {}).get("auto_escalate_after_cumulative_findings") is None
    assert d.get("verification", {}).get("notice_escalate_at_cumulative_findings") is None
    assert d.get("verification", {}).get("escalate_on_first_verifier_failure") is False
    assert d.get("verification", {}).get("escalate_after_cumulative_stage_failures") is None
    assert d.get("verification", {}).get("escalate_after_cumulative_gate_failures") is None
    assert d.get("verification", {}).get("escalate_after_cumulative_high_severity_findings") is None


def test_module_integrator_score() -> None:
    mi = ModuleIntegrator()
    assert mi.score_fit("auth-rbac-starter", {"tags": ["auth-rbac-starter"]}) == 1.0


def test_module_integrator_score_with_bundle_tags_recall() -> None:
    mi = ModuleIntegrator(min_score_to_pass=0.7)
    prof = {"tags": ["auth", "rbac"], "bundle_tags": ["auth", "rbac"]}
    assert mi.score_fit("auth-rbac-starter", prof) == 1.0
    assert mi.passes_gate("auth-rbac-starter", prof)
    partial = {"tags": ["auth"], "bundle_tags": ["auth", "rbac"]}
    assert mi.score_fit("auth-rbac-starter", partial) == 0.5
    assert not mi.passes_gate("auth-rbac-starter", partial)
    mismatch = {"tags": ["billing", "stripe"], "bundle_tags": ["auth", "rbac"]}
    assert mi.score_fit("auth-rbac-starter", mismatch) == 0.0


def test_module_integrator_threshold_yaml() -> None:
    mi = ModuleIntegrator.from_yaml(ROOT / "configs" / "integrator" / "thresholds.yaml")
    assert mi.passes_gate("auth-rbac-starter", {"tags": ["auth-rbac-starter"]})
    assert not mi.passes_gate("unknown", {"tags": ["nope"]})


def test_universal_critique_router_yaml() -> None:
    r = UniversalCritiqueRouter.from_yaml(CRITIQUE_PAIRINGS_YAML)
    assert "product_reference_critic" in r.pairing_for("backend_writer")


def _producer_taxonomy_keys(registry: RoleRegistry) -> set[str]:
    return {k for k in registry.known_taxonomy_keys() if not k.endswith("_critic")}


def test_critique_pairings_cover_registry_producers() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(CRITIQUE_PAIRINGS_YAML)
    producers = _producer_taxonomy_keys(reg)
    missing = producers - router.known_producer_keys()
    assert not missing, f"critique_pairings.yaml missing producers: {sorted(missing)}"
    for prod in producers:
        critics = router.pairing_for(prod)
        assert critics, f"empty critics for {prod!r}"
        for critic in critics:
            assert critic in reg.known_taxonomy_keys(), (
                f"unknown critic {critic!r} for producer {prod!r}"
            )


def test_universal_critique_unknown_producer_defaults_to_plan_critics() -> None:
    reg = RoleRegistry.from_yaml(ROOT / "configs" / "roles.yaml")
    router = UniversalCritiqueRouter.from_yaml(CRITIQUE_PAIRINGS_YAML)
    critics = router.pairing_for("hypothetical_future_writer")
    assert critics == ["product_reference_critic", "domain_critic"]
    for critic in critics:
        assert critic in reg.known_taxonomy_keys()


def test_security_scanner_runs_static_bundle() -> None:
    scanner = SecurityScanner()
    result = scanner.run(str(ROOT))
    assert "exit_code" in result and "log" in result
    assert result.get("ruff_exit_code") is not None
    assert result.get("bandit_exit_code") is not None
