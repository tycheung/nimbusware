# nimbusware_projections

Pure functions that turn append-only events into timeline summaries, operator metrics tables, and CSV export rows. Shared between API responses and Admin Console display modules.

## Layout

| Area | Role |
|------|------|
| `builders/` | Per-stage timeline builders |
| `fields/` | Stable field extractors for display layers |
| `run_summary.py` | Run-level rollup |

## Import rules

Orchestrator must not import `nimbusware_api`; projections are the shared read-model layer (`tests/unit/test_import_graph.py`).

Normative contract: [hermes-orchestrator-local-plan.md](../../hermes-orchestrator-local-plan.md).
