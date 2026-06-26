#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
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
    "packages/nimbusware_maker_web/static/js/safe-coding-wizard.js",
    "packages/nimbusware_maker_web/static/js/safe-coding-ux.js",
    "packages/nimbusware_api/routes/platform.py",
)

_SAFE_CODING_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker/consumer_test_scaffold.py",
    "packages/nimbusware_maker/playwright_bootstrap.py",
    "tests/e2e/web/maker_safe_coding_onboarding.spec.ts",
)

_ENGINEER_STATIC: tuple[str, ...] = (
    "packages/nimbusware_orchestrator/collab_binding_resolver.py",
    "packages/nimbusware_api/routes/platform_collab_settings.py",
    "packages/nimbusware_maker_web/static/js/tabs/chat_model_drawer_ui.js",
    "configs/install/bundles/default.config.yaml",
)

_ENGINEER_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker_web/static/js/archetype-picker.js",
    "tests/api/test_collab_settings_api.py",
    "tests/api/test_collab_model_routing_api.py",
)

_ENTERPRISE_STATIC: tuple[str, ...] = (
    "configs/install/bundles/enterprise.env.yaml",
    "packages/nimbusware_api/routes/enterprise/compliance.py",
    "packages/nimbusware_api/routes/enterprise/audit_export.py",
)

_ENTERPRISE_BEHAVIORAL: tuple[str, ...] = (
    "packages/nimbusware_maker_web/static/js/tabs/home.js",
    "tests/e2e/web/maker_enterprise_journey.spec.ts",
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
    safe = _blend(
        _score_paths(root, _SAFE_CODING_STATIC),
        _score_paths(root, _SAFE_CODING_BEHAVIORAL),
    )
    engineer = _blend(
        _score_paths(root, _ENGINEER_STATIC),
        _score_paths(root, _ENGINEER_BEHAVIORAL),
    )
    enterprise = _blend(
        _score_paths(root, _ENTERPRISE_STATIC),
        _score_paths(root, _ENTERPRISE_BEHAVIORAL),
    )
    ok = all(row.get("meets_target") for row in (safe, engineer, enterprise))
    return {
        "version": 2,
        "ok": ok,
        "target_score": _TARGET_SCORE,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "mode": "behavioral_rubric",
        "archetypes": {
            "safe_coding": safe,
            "engineer": engineer,
            "enterprise": enterprise,
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
