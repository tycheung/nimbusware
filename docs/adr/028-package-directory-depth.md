# ADR 028: Package directory depth vs breadth

## Status

Accepted (2026-07)

## Context

After dropping the `nimbusware_` package prefix, several packages still expose most modules at a single directory level. `orchestrator` had **250+** `.py` files at package root while `agent_core` and `projections` already follow a depth-first layout (`models/`, `read/`, `builders/`, `fields/`). Flat packages slow navigation, encourage accidental coupling, and make module-size guards harder to reason about.

Horizontal sprawl also appeared in tests (`tests/unit/` ~400 flat files) and in incomplete extractions (`orchestrator/slice/` and `critique/` barrels re-exporting root modules that were never moved).

## Decision

### Depth-first layout (target)

| Principle | Rule |
|-----------|------|
| **Breadth cap** | Prefer **≤25** `.py` modules at package root; entrypoints (`pipeline.py`, `*_cli.py`, `app.py`) and thin `__init__.py` exports only. |
| **Domain subpackages** | Group by bounded context: `orchestrator/workflow/`, `slice/`, `fleet/`, `critique/`, etc. — mirror stage/workflow names operators already use. |
| **No compatibility shims** | Delete re-export-only modules (`read_models.py`, `llm_plan.py`, `stage_graph.py` → import `projections` / `agent_core` / `llm` directly). |
| **Barrel `__init__.py`** | Allowed only when a subpackage is a **cohesive public API** (e.g. `orchestrator.llm`); not as a substitute for moving files. |
| **Tests mirror packages** | Themed folders under `tests/unit/<package>/` or top-level `tests/api_http/`, `tests/orchestrator_pipeline/`; never a test package name that shadows a production import (`tests/orchestrator` → `tests/orchestrator_pipeline`). |

### Orchestrator domain map (normative)

```
orchestrator/
  _pipeline/     # RunOrchestrator mixins + stage_registry.py (ordered mixin list)
  llm/           # LLM stage helpers + providers
  workflow/      # workflow_*.py, registry, profiles
  fleet/         # fleet_*.py (CLI entrypoints stay at root)
  slice/         # slice_*, micro_slice_*, fast_slice_critique
  campaign/      # campaign_*, backlog_*
  critique/      # scan/security/performance/simplification critics
  persona/       # persona shelf + probation
  integrator/    # integrator gate + integration adapters
  dev_env/       # persistent dev environment
  factory/       # factory + put/e2e harness + js_framework_detect, human_fidelity
  launch/        # launch_eval*, launch_flow_resolver, launch_test_*
  escalation/    # escalation_*, gate_override_execution
  improvement/   # improvement_council*, diagnose_learn, feature_gap_matrix, resolution_council
  interaction/   # interaction_surface_*
  scraper/       # scraper artifacts + stage
  routing/       # model bindings, Ollama, routing presets
  profiles/      # user/autopilot/enforcement profiles
  collab/        # collab mesh + mesh scheduler
  replay/        # replay + audit export
  repo_intel/    # code graph, repo inventory, similarity
  stack/         # stack catalog / diff budget / agent scaffold
```

### Memory and maker (phase-aligned)

- `memory/store/`, `memory/fleet/`, `memory/index/` — backends vs fleet sync vs indexing.
- `maker/chat/`, `maker/deploy/`, `maker/collab/` — chat store vs deploy pipeline vs collab policy.

## Consequences

- One-time import path churn; no long-lived `nimbusware_*` or root-level alias modules.
- `tests/unit/test_package_module_size.py` and import-graph guards unchanged; new subpackages must respect existing layer boundaries (`orchestrator` must not import `api`).
- Future modules land in the domain subpackage first; root only when adding a new CLI or facade entrypoint.
- LOC/module-size CI may need allowlist updates when splitting large files across subpackages.

## References

- [ARCHITECTURE.md](../../ARCHITECTURE.md) — layer diagram and package summary
- [packages/README.md](../../packages/README.md) — package catalog
- [ADR 003](003-projections-layer.md) — projections as the read-model home (retire orchestrator `read_models` shim)
- [ADR 006](006-prompt-tiers.md) — `agent_core.prompt_tiers` is canonical (retire orchestrator copy)
- `scripts/ci/reorganize_packages.py` — migration tooling
