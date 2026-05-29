# agent_core

Shared Pydantic models for Hermes orchestration events.

Normative product plan: `hermes-orchestrator-local-plan.md` (repo root).  
Post-alignment gap analysis: `PLAN_GAP.md` (repo root).

Sibling packages (same Poetry workspace): `hermes_store` (Postgres + in-memory append store),
`hermes_orchestrator` (YAML §6.3A merge, registry, preflight, MVP pipeline), `hermes_api` (FastAPI
`/v1`), `hermes_executor` (subprocess + egress helpers), `hermes_console` (Streamlit), `hermes_extensions` (Phase 2+ stubs).

## Wire format

- **Role identifiers** (`owner_role`, `actor_role`, critic / routing role fields): **UUID** values
  from the Role Registry (plan §3, §5). JSON uses **UUID strings** (`serialize_event_persistent` /
  `model_dump(mode="json")`).
- **Event envelope**: discriminated union on `event_type`; use `validate_event_dict` so
  `event_type` and `payload` stay coupled (plan §6.5).

## Public API

See `agent_core.models` exports in `packages/agent_core/models/__init__.py`.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) in this directory.
