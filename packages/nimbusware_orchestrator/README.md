# Nimbusware agent orchestration (Nimbusware integration)

Local event-sourced run pipeline for the Nimbusware online agentic system, hosted by Nimbusware. Public entry: `RunOrchestrator` in `pipeline.py` (class defined in `_pipeline/compose.py`).

Runtime wiring for the API and run-dispatch worker is centralized in `runtime_bootstrap.py` (`build_runtime_orchestrator`, `api_config_from_db_enabled`).

## Mixin map (`_pipeline/compose.py`)

| Mixin | Module | Responsibility |
|-------|--------|----------------|
| `CreateRunMixin` | `create_run.py` | `run.created`, idempotency, project metadata |
| `CampaignDispatchMixin` | `campaign_dispatch.py` | `start_campaign`, `campaign_tick` queue dispatch |
| `MicroSliceMixin` | `micro_slice.py` | Slice plan/implement/verify chain |
| (packet helper) | `slice_repo_map.py` | Repo tree + import graph for `SliceContextPacket.repo_map_excerpt` |
| (packet helper) | `slice_symbol_sketch.py` | AST symbol sketch; `slice_lsp_client.py` Pyright `documentSymbol` with import-neighbor expansion (default `poetry install`) |
| `PipelineScraperMixin` | `pipeline_scraper.py` | Scraper stage + artifacts |
| `LifecycleMixin` | `lifecycle.py` | start / plan / verify / slice API transitions |
| `CritiqueGatesMixin` | `critique_gates.py` | Composed: `critique_gates_{stage_failed,helpers,optional_emit}.py` |
| `WritersMixin` | `writers.py` | Parallel frontend/backend writers |
| `RoleExecuteMixin` | `role_execute.py` | `POST /roles/{id}/execute` dispatcher into pipeline stage entry points |
| `OptionalCritiqueMixin` | `optional_critique.py` | Universal critique, agent evaluator |
| `EscalationMixin` | `escalation.py` | Anti-deadlock escalation |
| `OptionalStagesMixin` | `optional_stages.py` | Composed: `optional_stages_{integration,agent_evaluator,self_refinement,integrator}.py` |
| `RunOrchestratorBase` | `base.py` | Shared store/registry wiring |

## Layering

- Depends on: `agent_core`, `nimbusware_store`, `nimbusware_extensions`, `nimbusware_memory`, `nimbusware_executor`
- Must **not** import `nimbusware_api` (use `nimbusware_projections` for read models)
- Extensions must **not** import orchestrator at module level (see `tests/unit/test_import_graph.py`)
- **Ollama inventory:** `ollama_manage.py` (list/pull/delete against runtime), `ollama_user_policy.py` (`ollama_user_policy` in `model-routing.yaml`)

## Campaign driver

Long-running autonomous builds use `workflow_profile=campaign_micro_slice`: `campaign_driver.py` generates a delivery backlog, executes **one** micro-slice per `campaign_tick` worker task, runs periodic refactor/architecture maintenance, and finalizes via tiered `completion_evaluator.py` (slice terminal + workflow `completion:` policy). Event-row parsers: `agent_core.read.campaign`. Public safety API: `RunOrchestrator.active_campaigns_for_project()`. Start with `RunOrchestrator.start_campaign(run_id)`; worker steps: `campaign_tick` (see `run_worker.py`).

## Testing

Orchestrator tests live under `tests/orchestrator/` and `tests/unit/test_*slice*`, `test_*critique*`, `test_campaign*`.

## Adding a pipeline stage

1. **Mixin module** — Add `packages/nimbusware_orchestrator/_pipeline/<stage>.py` with a `*Mixin` class. Import symbols from `_helpers` **explicitly** (no star imports), matching existing mixins such as `create_run.py` or `pipeline_scraper.py`.
2. **Register in `compose.py`** — Import the mixin and append it to `_MIXINS` (order matters for MRO). `build_run_orchestrator_class` wraps mixin methods so runtime lookups resolve via `nimbusware_orchestrator.pipeline` (stable `unittest.mock.patch` target).
3. **`_helpers` exports** — Shared types, event helpers, and policy parsers live in `_pipeline/_helpers.py`. If a mixin needs a new symbol, add or re-export it there.
4. **Export guard** — `tests/unit/test_pipeline_helpers_exports.py` asserts required `_helpers` symbols exist and that mixin modules do not star-import `_helpers`.

For composed stages (e.g. `optional_stages.py`, `critique_gates.py`), split implementation modules and re-export a single composed mixin class.

## Refactor notes

- **Mypy:** Tranche E strict-checks `_pipeline/_helpers` (explicit `__all__`) and all `_pipeline` mixin modules without `attr-defined` ignores on `_helpers` imports. Ships PEP 561 marker (`py.typed`).
- **Compose-time patch seam:** `compose.py` binds mixin method globals to `pipeline` during each call so tests can patch `nimbusware_orchestrator.pipeline.*` without star-import barrels in mixins. Mixins still import from `_helpers` explicitly at module level.
- After mechanical splits in console display packages, run `poetry run python scripts/explicit_star_imports.py` and `poetry run python scripts/sync_display_facade.py`.
- Do **not** run repo-wide `ruff check --fix` (strips re-export imports). Use `./scripts/ci_check.ps1` locally.

Normative Nimbusware contract: gitignored `nimbusware-orchestrator-local-plan.md` at repo root.
