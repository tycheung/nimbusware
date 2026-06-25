"""Measure consumer archetype fit via static rubric (CI-stable)."""

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

_TARGET_SCORE = 0.85

_SAFE_CODING_CHECKS: tuple[str, ...] = (
    "configs/workflows/safe_coding.yaml",
    "docs/product/safe-coding.md",
    "packages/nimbusware_maker_web/static/js/archetype-picker.js",
    "packages/nimbusware_maker_web/static/js/safe-coding-ux.js",
    "configs/install/bundles/default.env.yaml",
)

_ENGINEER_CHECKS: tuple[str, ...] = (
    "packages/nimbusware_orchestrator/participant_output_packet.py",
    "packages/nimbusware_orchestrator/collab_output_redaction.py",
    "configs/autopilot/user_profiles.yaml",
    "packages/nimbusware_api/routes/provider_subscription_oauth.py",
    "configs/install/bundles/enterprise.env.yaml",
)


def _rubric_score(root: Path, rel_paths: tuple[str, ...]) -> dict[str, object]:
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


def measure_archetype_fit(*, repo_root: Path | None = None) -> dict[str, object]:
    root = repo_root or find_repo_root()
    safe = _rubric_score(root, _SAFE_CODING_CHECKS)
    engineer = _rubric_score(root, _ENGINEER_CHECKS)
    ok = bool(safe.get("meets_target")) and bool(engineer.get("meets_target"))
    return {
        "version": 1,
        "ok": ok,
        "target_score": _TARGET_SCORE,
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "mode": "static_rubric",
        "archetypes": {
            "safe_coding": safe,
            "engineer": engineer,
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
