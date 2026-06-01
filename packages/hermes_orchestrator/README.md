# Hermes orchestrator

Event-sourced run pipeline for Nimbusware. Public entry: `RunOrchestrator` in `pipeline.py`.

## Mixin map (`_pipeline/compose.py`)

| Mixin | Module | Responsibility |
|-------|--------|----------------|
| `CreateRunMixin` | `create_run.py` | `run.created`, idempotency, project metadata |
| `MicroSliceMixin` | `micro_slice.py` | Slice plan/implement/verify chain |
| `PipelineScraperMixin` | `pipeline_scraper.py` | Scraper stage + artifacts |
| `LifecycleMixin` | `lifecycle.py` | start / plan / verify / slice API transitions |
| `CritiqueGatesMixin` | `critique_gates.py` | Composed: `critique_gates_{stage_failed,helpers,optional_emit}.py` |
| `WritersMixin` | `writers.py` | Parallel frontend/backend writers |
| `OptionalCritiqueMixin` | `optional_critique.py` | Universal critique, agent evaluator |
| `EscalationMixin` | `escalation.py` | Anti-deadlock escalation |
| `OptionalStagesMixin` | `optional_stages.py` | Composed: `optional_stages_{integration,agent_evaluator,self_refinement,integrator}.py` |
| `RunOrchestratorBase` | `base.py` | Shared store/registry wiring |

## Layering

- Depends on: `agent_core`, `hermes_store`, `hermes_extensions`, `hermes_memory`, `hermes_executor`
- Must **not** import `nimbusware_api` (use `nimbusware_projections` for read models)
- Extensions must **not** import orchestrator at module level (see `tests/unit/test_import_graph.py`)

## Testing

Orchestrator tests live under `tests/orchestrator/` and `tests/unit/test_*slice*`, `test_*critique*`.

## Refactor notes

- Pipeline mixins intentionally `from _helpers import *` — guarded by `tests/unit/test_pipeline_helpers_exports.py`.
- After mechanical splits in console display packages, run `poetry run python scripts/explicit_star_imports.py` and `poetry run python scripts/sync_display_facade.py`.
- Do **not** run repo-wide `ruff check --fix` (strips re-export imports). Use `./scripts/ci_check.ps1` locally.
