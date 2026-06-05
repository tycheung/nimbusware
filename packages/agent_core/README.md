# agent_core

Shared Pydantic models for Nimbusware agent orchestration events (Nimbusware wire format).

Normative Nimbusware contract: gitignored `nimbusware-orchestrator-local-plan.md` at repo root.

Sibling packages (same Poetry workspace): `nimbusware_store` (Postgres + in-memory append store),
`nimbusware_orchestrator` (YAML merge, registry, preflight, MVP pipeline), `nimbusware_api` (FastAPI
`/v1`), `nimbusware_executor` (subprocess + egress helpers), `nimbusware_console` (Admin display modules),
`nimbusware_extensions` (personas, bundles, escalation), `nimbusware_projections` (shared timeline builders).

## Wire format

- **Role identifiers** (`owner_role`, `actor_role`, critic / routing role fields): **UUID** values
  from the Role Registry (plan §3, §5). JSON uses **UUID strings** (`serialize_event_persistent` /
  `model_dump(mode="json")`).
- **Event envelope**: discriminated union on `event_type`; use `validate_event_dict` so
  `event_type` and `payload` stay coupled.
- **Hardware**: `hardware.profile.detected` (optional `run_id` on platform rescan) is in the foundation union (`events_foundation.py`).

## Public API

See `agent_core.models` exports in `packages/agent_core/models/__init__.py`.

YAML helpers live in `agent_core.yaml_io` (`load_yaml`, `dump_yaml`, `atomic_write_yaml`).

Ships PEP 561 marker (`py.typed`).
