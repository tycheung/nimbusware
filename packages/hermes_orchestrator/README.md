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
- **Ollama inventory:** `ollama_manage.py` (list/pull/delete against runtime), `ollama_user_policy.py` (`ollama_user_policy` in `model-routing.yaml`)

## Testing

Orchestrator tests live under `tests/orchestrator/` and `tests/unit/test_*slice*`, `test_*critique*`.

## Adding a pipeline stage

1. **Mixin module** — Add `packages/hermes_orchestrator/_pipeline/<stage>.py` with a `*Mixin` class. Import symbols from `_helpers` **explicitly** (no star imports), matching existing mixins such as `create_run.py` or `pipeline_scraper.py`.
2. **Register in `compose.py`** — Import the mixin and append it to `_MIXINS` (order matters for MRO). `build_run_orchestrator_class` wraps mixin methods so runtime lookups resolve via `hermes_orchestrator.pipeline` (stable `unittest.mock.patch` target).
3. **`_helpers` exports** — Shared types, event helpers, and policy parsers live in `_pipeline/_helpers.py`. If a mixin needs a new symbol, add or re-export it there.
4. **Export guard** — `tests/unit/test_pipeline_helpers_exports.py` asserts required `_helpers` symbols exist and that mixin modules do not star-import `_helpers`.

For composed stages (e.g. `optional_stages.py`, `critique_gates.py`), split implementation modules and re-export a single composed mixin class.

## Refactor notes

- **Mypy:** `hermes_orchestrator._pipeline.*` stays on `ignore_errors = true` in `pyproject.toml` (mixin MRO / dynamic bindings). All other orchestrator modules are strict-checked with the API (Lane T fo531).
- **Compose-time patch seam:** `compose.py` binds mixin method globals to `pipeline` during each call so tests can patch `hermes_orchestrator.pipeline.*` without star-import barrels in mixins. Mixins still import from `_helpers` explicitly at module level.
- After mechanical splits in console display packages, run `poetry run python scripts/explicit_star_imports.py` and `poetry run python scripts/sync_display_facade.py`.
- Do **not** run repo-wide `ruff check --fix` (strips re-export imports). Use `./scripts/ci_check.ps1` locally.
