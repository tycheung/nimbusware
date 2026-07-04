# ADR 006: Prompt tiers for slice LLM calls

## Status

Accepted (2026-06); amended (2026-07) — provider cache plumbing

## Context

Pi-style efficiency requires a stable prefix across consecutive slice LLM calls so
providers can cache system instructions. Volatile slice ids, handoffs, and tool
results must not pollute the stable block.

## Decision

Use three tiers via `agent_core.prompt_tiers`:

| Tier | Contents | Example call sites |
|------|----------|-------------------|
| **STABLE** | Role, JSON schemas, tool rules (no timestamps) | `llm_slice` plan, `agent_loop`, plan stage schema |
| **CONTEXT** | Skill briefs, loaded rubric bodies (per stage) | Plan stage skills block |
| **VOLATILE** | Slice id, handoff, memory, verifier logs | Plan user prompt, agent loop user block |

`assemble_prompt(stable, context, volatile)` maps STABLE+CONTEXT to the system
message and VOLATILE to the user message.

### Provider cache metadata (Jul 2026)

`assemble_prompt_with_cache_metadata` returns an `AssembledPrompt` with `cache_blocks`:
each block carries `tier`, `text`, and optional `cache_control` / `cache_breaking` flags.
Call sites pass blocks through `ModelBindingResolver.chat_json()` to cloud providers:

| Provider | Behavior |
|----------|----------|
| Anthropic | Multi-block system content via `orchestrator/llm/prompt_cache.py` (T0/T1 ephemeral blocks) |
| OpenAI-compatible | Optional prefix-reuse hint when `NIMBUSWARE_OPENAI_PREFIX_REUSE=1` |

Critique stages share a stable harness prefix in `orchestrator/critique/prompt_assembly.py`
so critic calls reuse the same cacheable system block as slice paths.

## Consequences

- Consecutive slices share byte-identical stable prefixes when model and rules unchanged.
- Skill bodies load into CONTEXT once per stage, not at `run.created`.
- Critique stages use tier-aware assembly via the shared critic harness.
- Agent loop threads `cache_blocks` from assembly through resolver to every mapped cloud stage.
