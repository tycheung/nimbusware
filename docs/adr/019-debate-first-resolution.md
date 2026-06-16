# ADR 019: Debate-first resolution

## Status

Accepted.

## Decision

Remediable critic findings route through `resolution.council` — a **deterministic heuristic gate** (LOC budgets, autopilot level, hard-block classification), not a multi-agent LLM debate. Deliberation rounds in workflow YAML scale retry behavior by autopilot level; the council module scores accord and emits pause/fix-slice recommendations.

Hard-block allowlist: security P0, policy/egress, governor cap, NEEDS_OPERATOR.

## Implementation note

`improvement_council` and `resolution_council` are rule-based scorers over critic findings. Operator-facing “council” ribbons summarize gate outcomes; they do not invoke separate agent personas.
