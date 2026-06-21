# ADR 022: Per-role model routing

## Status

Accepted (v1.2 Track A shipped Jun 2026).

## Context

v1.1 hybrid routing binds **stage keys** (`plan`, `slice.critique`) to a single OpenAI-compatible cloud block plus one global Ollama primary. Operators need **per agent role** bindings (planner, backend_writer, security_critic, custom agents) with mid-run swap and honest preflight when Ollama is optional.

## Decision

1. **Binding schema** — each role resolves to `provider_kind`, `provider_id`, `model_id`, optional `base_url`, `api_key_ref` / vault `connection_id`, and generation params (see `alllms.md` § Track A).
2. **Resolution precedence** (highest first): workload claimer snapshot → `model.binding.overridden` event → run `model_bindings_snapshot` → session overrides → user profile defaults → workflow profile → global `model-routing.models.primary`.
3. **`ModelBindingResolver`** in orchestrator is the **only** dispatch path for agent LLM calls after Track A2; direct `ollama_chat_json` is forbidden in feature code (audit: `docs/audits/llm-call-sites.md`).
4. **Preflight** reports `roles_covered` and per-provider reachability; missing Ollama does **not** block runs when all active workflow roles have healthy cloud bindings.
5. **Secrets** — API keys live in per-user vault refs (`connection_id`); never appear in events, chat turns, or audit exports.

## Non-goals (v1.2)

- Per-message (non-role) model routing
- Cursor Composer as an LLM backend
- Cloud-only platform default

## Consequences

- `configs/model-routing.yaml` `stage_providers` shimmed during migration (fo1471).
- Settings **Agent & Models** tab and Model Hub API connections are the operator surfaces (Tracks A4, C2–C3).
- Telemetry adds `provider_id`, `model_id`, `binding_source` on inference events.
