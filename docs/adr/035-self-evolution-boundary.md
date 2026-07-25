# ADR 035: Self-evolution boundary

## Status

Accepted.

## Context

Nimbusware needs closed-loop improvement (prompts, skills, sandboxed variants) without unbounded self-modification of the harness.

## Decision

1. **May evolve:** target workspace source; versioned artifacts under `.nimbusware/evolution/` and workspace skill drafts; `configs/skills/` status fields; agent overlay CONTEXT text.
2. **Must not auto-evolve:** `packages/**` (orchestrator/api/etc.), STABLE prompt tiers (tool schemas / JSON contracts), MCP tool schemas, secrets, `.cursor/`, deploy credentials.
3. **Meta-pattern:** propose → evaluate → keep only if better, audited as `evolution.proposed` / `.scored` / `.promoted` / `.rejected` stage events.
4. **Layers:** L1 prompt overlays; L2 skill library; L3 `VARIANT_EXPERIMENT` only (GREENFIELD; blocked under HARDEN).
5. **Tracks choose actions; evolution chooses artifacts.** `DISTILL_ARTIFACTS` is propose-only (no workspace mutate).

## Consequences

- Improvement council + RepoScope remain the action selector.
- Darwin promote rejects variants that touch forbidden prefixes (`packages/`, `.cursor/`, …).
- Operator/API promote path: `GET/POST /v1/runs/{id}/evolution`.
