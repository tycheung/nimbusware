#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO / "packages") not in sys.path:
    sys.path.insert(0, str(_REPO / "packages"))

from nimbusware_env import find_repo_root

_TARGET_SCORE = 0.95

_SAFE_CODING_STATIC: tuple[str, ...] = (
    "configs/workflows/safe_coding.yaml",
    "docs/product/safe-coding.md",
    "docs/product/journeys/safe-coding-first-app.md",
    "packages/nimbusware_maker_web/static/js/safe-coding-wizard.js",
    "packages/nimbusware_maker_web/static/js/safe-coding-ux.js",
    "packages/nimbusware_api/routes/platform.py",
)

_SAFE_CODING_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker/consumer_test_scaffold.py",
    "packages/nimbusware_maker/playwright_bootstrap.py",
    "tests/e2e/web/maker_safe_coding_onboarding.spec.ts",
    "tests/e2e/web/maker_safe_coding_full_journey.spec.ts",
)

_ENGINEER_STATIC: tuple[str, ...] = (
    "packages/nimbusware_orchestrator/collab_binding_resolver.py",
    "packages/nimbusware_api/routes/platform_collab_settings.py",
    "packages/nimbusware_maker_web/static/js/tabs/chat_model_drawer_ui.js",
    "packages/nimbusware_maker_web/static/js/tabs/chat_solo_hat_coach_ui.js",
    "docs/product/journeys/engineer-first-app.md",
    "configs/install/bundles/default.config.yaml",
    "packages/nimbusware_config/collab_settings_store.py",
)

_ENGINEER_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker_web/static/js/archetype-picker.js",
    "packages/nimbusware_orchestrator/host_collab_mesh_hydrate.py",
    "tests/api/test_collab_settings_api.py",
    "tests/api/test_collab_model_routing_api.py",
    "tests/e2e/web/collab_model_routing.spec.ts",
    "tests/e2e/web/maker_solo_hat_coach.spec.ts",
)

_ENTERPRISE_STATIC: tuple[str, ...] = (
    "configs/install/bundles/enterprise.env.yaml",
    "docs/product/journeys/enterprise-first-app.md",
    "packages/nimbusware_api/routes/enterprise/compliance.py",
    "packages/nimbusware_api/routes/enterprise/audit_export.py",
    "packages/nimbusware_api/routes/enterprise/audit_policy.py",
)

_ENTERPRISE_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker_web/static/js/tabs/home.js",
    "tests/e2e/web/maker_enterprise_journey.spec.ts",
    "tests/e2e/web/maker_enterprise_install_journey.spec.ts",
    "packages/nimbusware_memory/embeddings.py",
    "scripts/benchmarks/measure_gate_comprehension.py",
)

_POLISH_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker_web/static/js/tabs/chat_discovery_ui.js",
    "tests/e2e/web/maker_product_polish_smoke.spec.ts",
    ".github/workflows/product_polish_smoke.yml",
    ".github/workflows/archetype_fit_weekly.yml",
)

_FS6_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_orchestrator/stack_agent_scaffold.py",
    "configs/personas/surface_critics.yaml",
    "packages/nimbusware_orchestrator/factory_put_e2e.py",
    "tests/unit/test_fs6_scaffold_polish.py",
)


def _score_paths(root: Path, rel_paths: tuple[str, ...]) -> dict[str, object]:
    passed = 0
    missing: list[str] = []
    for rel in rel_paths:
        if (root / rel).is_file():
            passed += 1
        else:
            missing.append(rel)
    total = len(rel_paths) or 1
    fit = round(passed / total, 3)
    return {
        "fit_score": fit,
        "checks_passed": passed,
        "checks_total": total,
        "missing": missing,
        "meets_target": fit >= _TARGET_SCORE,
    }


def _content_checks(root: Path) -> dict[str, dict[str, object]]:
    wizard = (root / "packages/nimbusware_maker_web/static/js/safe-coding-wizard.js").read_text(
        encoding="utf-8",
    )
    bootstrap = (root / "packages/nimbusware_maker/playwright_bootstrap.py").read_text(encoding="utf-8")
    compliance = (root / "packages/nimbusware_api/routes/enterprise/compliance.py").read_text(
        encoding="utf-8",
    )
    fleet = (root / "packages/nimbusware_admin_ui/src/pages/FleetPage.tsx").read_text(encoding="utf-8")
    hydrate = (root / "packages/nimbusware_orchestrator/host_collab_mesh_hydrate.py").read_text(
        encoding="utf-8",
    )
    collab_store = (root / "packages/nimbusware_config/collab_settings_store.py").read_text(
        encoding="utf-8",
    )
    discovery_ui = (root / "packages/nimbusware_maker_web/static/js/tabs/chat_discovery_ui.js").read_text(
        encoding="utf-8",
    )
    return {
        "safe_coding": {
            "wizard_poll": "pollPlaywrightBootstrap" in wizard and "BOOTSTRAP_POLL_MS" in wizard,
            "async_bootstrap": "_job_status" in bootstrap and "threading" in bootstrap,
        },
        "engineer": {
            "collab_persist": "save_persisted_collab_enabled" in collab_store,
            "host_hydrate": "ensure_mesh_binding_for_llm" in hydrate,
            "campaign_parallel": "ThreadPoolExecutor" in (root / "packages/nimbusware_orchestrator/campaign_driver_execute.py").read_text(encoding="utf-8"),
        },
        "enterprise": {
            "compliance_metrics": "gate_pass_rate" in compliance,
            "fleet_dashboard": "gate_pass_rate" in fleet or "Gate pass rate" in fleet,
            "fleet_semantic_embedding": (root / "packages/nimbusware_memory/embeddings.py").is_file(),
            "gate_comprehension_harness": (root / "scripts/benchmarks/measure_gate_comprehension.py").is_file(),
        },
        "polish": {
            "discovery_explain": "discovery-explain-btn" in discovery_ui,
            "surface_bindings": "maker-chat-scope-surface-bindings" in discovery_ui,
            "product_polish_smoke": (root / "tests/e2e/web/maker_product_polish_smoke.spec.ts").is_file(),
            "fs6_scaffold": (root / "packages/nimbusware_orchestrator/stack_agent_scaffold.py").is_file(),
            "archetype_weekly": (root / ".github/workflows/archetype_fit_weekly.yml").is_file(),
        },
    }


def _score_content_checks(checks: dict[str, bool]) -> dict[str, object]:
    passed = sum(1 for ok in checks.values() if ok)
    total = len(checks) or 1
    fit = round(passed / total, 3)
    missing = [name for name, ok in checks.items() if not ok]
    return {
        "fit_score": fit,
        "checks_passed": passed,
        "checks_total": total,
        "missing": missing,
        "meets_target": fit >= _TARGET_SCORE,
    }


def _run_behavioral_pytest(root: Path) -> bool:
    modules = [
        "tests/unit/test_collab_settings_store.py",
        "tests/unit/test_host_collab_mesh_hydrate.py",
        "tests/api/test_playwright_bootstrap_api.py",
    ]
    existing = [m for m in modules if (root / m).is_file()]
    if not existing:
        return False
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *existing, "-q"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def _blend(static: dict[str, object], behavioral: dict[str, object]) -> dict[str, object]:
    s = float(static["fit_score"])  # type: ignore[arg-type]
    b = float(behavioral["fit_score"])  # type: ignore[arg-type]
    fit = round(0.4 * s + 0.6 * b, 3)
    missing = list(static.get("missing", [])) + list(behavioral.get("missing", []))  # type: ignore[arg-type]
    return {
        "fit_score": fit,
        "static": static,
        "behavioral": behavioral,
        "missing": missing,
        "meets_target": fit >= _TARGET_SCORE,
    }


def measure_archetype_fit(*, repo_root: Path | None = None) -> dict[str, object]:
    root = repo_root or find_repo_root()
    content = _content_checks(root)
    pytest_ok = _run_behavioral_pytest(root)

    safe_static = _score_paths(root, _SAFE_CODING_STATIC)
    safe_behavioral_files = _score_paths(root, _SAFE_CODING_BEHAVIORAL)
    safe_content = _score_content_checks(content["safe_coding"])
    safe_behavioral = _blend(safe_behavioral_files, safe_content)
    if pytest_ok:
        safe_behavioral["fit_score"] = min(1.0, float(safe_behavioral["fit_score"]) + 0.05)  # type: ignore[arg-type]
    safe = _blend(safe_static, safe_behavioral)

    engineer_static = _score_paths(root, _ENGINEER_STATIC)
    engineer_behavioral_files = _score_paths(root, _ENGINEER_BEHAVIORAL)
    engineer_content = _score_content_checks(content["engineer"])
    engineer_behavioral = _blend(engineer_behavioral_files, engineer_content)
    engineer = _blend(engineer_static, engineer_behavioral)

    enterprise_static = _score_paths(root, _ENTERPRISE_STATIC)
    enterprise_behavioral_files = _score_paths(root, _ENTERPRISE_BEHAVIORAL)
    enterprise_content = _score_content_checks(content["enterprise"])
    enterprise_behavioral = _blend(enterprise_behavioral_files, enterprise_content)
    enterprise = _blend(enterprise_static, enterprise_behavioral)

    polish_static = _score_paths(root, _POLISH_BEHAVIORAL + _FS6_BEHAVIORAL)
    polish_content = _score_content_checks(content["polish"])
    polish_behavioral = _blend(polish_static, polish_content)
    polish = _blend(polish_static, polish_behavioral)

    ok = all(row.get("meets_target") for row in (safe, engineer, enterprise, polish))
    return {
        "version": 3,
        "ok": ok,
        "target_score": _TARGET_SCORE,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "mode": "behavioral_rubric",
        "pytest_modules_ok": pytest_ok,
        "archetypes": {
            "safe_coding": safe,
            "engineer": engineer,
            "enterprise": enterprise,
            "polish": polish,
        },
        "repo_root": str(root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure archetype fit metrics")
    parser.add_argument("--json", dest="json_path", default="")
    args = parser.parse_args(argv)
    metrics = measure_archetype_fit()
    if args.json_path:
        out = Path(args.json_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    return 0 if metrics.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
