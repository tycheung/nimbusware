# nimbusware_projections

Pure functions that turn append-only events into timeline summaries, operator metrics tables, and CSV export rows. Shared between API responses and Admin Console display modules.

## Layout

| Area | Role |
|------|------|
| `builders/` | Per-stage timeline builders |
| `fields/` | Stable field extractors for display layers |
| `run_summary.py` | Run-level rollup |

## Import rules

Projections must not import `nimbusware_orchestrator` at module level (campaign/backlog parsers live in `agent_core.read.campaign`). Orchestrator must not import `nimbusware_api`. Enforced in `tests/unit/test_import_graph.py`.

Campaign projections: `builders/campaign_progress.py`, `builders/backlog_tree.py`.

Ships PEP 561 marker (`py.typed`). Per-package coverage floor: ≥85% in CI.

Normative Nimbusware contract: gitignored `nimbusware-orchestrator-local-plan.md` at repo root.
