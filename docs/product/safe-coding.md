# Safe Coding (Maker persona)

Safe Coding is for builders who want working software with **fewer errors**, not deep engineering tooling. It uses the **`safe_coding`** workflow profile, **guided autopilot**, and **maker approval** before changes apply.

## When to use

- You are new to software development or prefer plain-language progress
- You want tests, browser checks, and security critics before each slice lands
- You prefer pauses when checks fail rather than auto-advancing

## Setup

1. Install with the **default** setup bundle (`--setup-bundle default`).
2. On first Maker launch, choose **Safe Coding** in the archetype picker (or set workflow to `safe_coding` in Settings).
3. Keep enforcement at **Balanced** (level 5) or higher.

## What you get

| Control | Safe Coding default |
|---------|---------------------|
| Workflow | `safe_coding` — fullstack gates + launch test + approval |
| Autopilot | `guided` — pauses on gate and regression failures |
| Enforcement | `balanced` |
| Auto-advance | Off |
| Collab | Off (use Engineer workspace preset for teams) |

## Plain-language gates

Progress and Review show gate steps as short sentences (e.g. “Automated tests: failed — review before continuing”) instead of raw stage ids.

## Workspace helpers

- **Readiness** — `GET /v1/platform/workspace-readiness?workspace_path=` checks for Playwright, tests, and project markers.
- **Scaffold** — `POST /v1/platform/workspace-scaffold` adds minimal `tests/e2e` or `tests/test_smoke.py` when missing.
- **Pre-commit** — `POST /v1/platform/workspace-precommit` installs a consumer `.pre-commit-config.yaml` template (ruff + pytest smoke).

## Related docs

- [maker.md](maker.md) — Maker tabs and operator ribbons
- [install-profiles.md](../install-profiles.md) — default vs enterprise setup bundles
- ADR [026](../adr/026-enforcement-depth-slider.md) — enforcement depth
