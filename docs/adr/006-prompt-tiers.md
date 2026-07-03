# ADR 006: Prompt tiers for slice LLM calls

## Status

Accepted (2026-06)

## Context

Pi-style efficiency requires a stable prefix across consecutive slice LLM calls so
providers can cache system instructions. Volatile slice ids, handoffs, and tool
results must not pollute the stable block.

## Decision

Use three tiers via `orchestrator.prompt_tiers`:

| Tier | Contents | Example call sites |
|------|----------|-------------------|
| **STABLE** | Role, JSON schemas, tool rules (no timestamps) | `llm_slice` plan, `agent_loop`, plan stage schema |
| **CONTEXT** | Skill briefs, loaded rubric bodies (per stage) | Plan stage skills block |
| **VOLATILE** | Slice id, handoff, memory, verifier logs | Plan user prompt, agent loop user block |

`assemble_prompt(stable, context, volatile)` maps STABLE+CONTEXT to the system
message and VOLATILE to the user message.

## Consequences

- Consecutive slices share byte-identical stable prefixes when model and rules unchanged.
- Skill bodies load into CONTEXT once per stage, not at `run.created`.
- Critique stages should migrate to tiers incrementally; slice paths are tier-aware today.
