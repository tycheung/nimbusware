# Self-evolution

Nimbusware improves under selection pressure via three layers on top of the existing improvement council and gates — not by rewriting the harness.

## Boundary

| Allowed | Forbidden |
|---------|-----------|
| Target workspace code | `packages/**` (platform) |
| `.nimbusware/evolution/` drafts | STABLE prompt tiers |
| Skill drafts / status | Secrets, `.cursor/`, deploy creds |

See [ADR 035](../adr/035-self-evolution-boundary.md).

## Layers

1. **L1 prompts** — CONTEXT overlays from diagnose learnings; golden/soft A/B; promote via Maker API or autopilot ≥8 (Individual).
2. **L2 skills** — draft → probation → promoted/shelved with `skill_ids_used` attribution.
3. **L3 variants** — `VARIANT_EXPERIMENT` arena only; fitness + forbidden-path deny; skipped while L1/L2 proposals pending.

## Improvement tracks

| Track | Role |
|-------|------|
| `simplify` / `refactor_cohesion` | Complexity reduction |
| `improve_coverage` | Tests (HARDEN) |
| `security_harden` | Security finding fixes |
| `performance_tune` | Perf critique follow-ups |
| `architecture_revise` | Same executor as maintenance architecture |
| `document_contracts` | ISM / contract alignment |
| `discover_features` | Product/market backlog + research |
| `implement_planned` | Feature-gap delivery |
| `research_transplant` | Stitch catalog / patterns |
| `distill_artifacts` | Propose-only L1/L2 |
| `variant_experiment` | Darwin–Gödel (GREENFIELD) |

RepoScope filters tracks (`greenfield` / `maintain` / `harden`).

## Operator knobs

- Autopilot ≥10 + every 5 slices → improvement council tick.
- Autopilot ≥8 → may auto-promote eligible L1 overlays (Individual).
- Autopilot ≥6 → variant promote when fitness ≥0.9.
- `GET /v1/runs/{id}/evolution` — ledger timeline + pending.
- `POST /v1/runs/{id}/evolution/promote` — approve/reject prompt artifacts.

## Meta-loop

```text
diagnose.learn → L1/L2 propose
slice.gate → score skills / overlays
council track → action (incl. distill / variant)
completion / launch-eval → promote or shelve
```
