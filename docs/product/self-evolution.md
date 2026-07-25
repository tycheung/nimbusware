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
| `research_harness` | Meta-study other agentic harnesses |
| `try_diverse_repo` | Sample distinct external repos and capture patterns |
| `research_domain` | Domain-specific study from operator keywords |

RepoScope filters tracks (`greenfield` / `maintain` / `harden`).

## Operator knobs

- **Work type `self_evolve`** → workflow `campaign_self_evolve` (Maker Chat dropdown or classify phrases like “self evolve”, “study other harnesses”, “diverse repos”, “domain knowledge”).
- Pass **domain keywords** in the chat prompt (e.g. “Self evolve on accounting software”) or as `requirements.domain_keywords` (`["accounting", "bookkeeping"]`).
- Autopilot defaults to **10** for `self_evolve`.
- Curriculum tick every **2** slices. With domain keywords: domain ~40%+, harness/diverse/distill share the rest. Without keywords: harness ~40%, diverse ~35%, distill ~25% (domain skipped).
- Autopilot ≥10 + every 5 slices → general improvement council tick (still).
- Autopilot ≥8 → may auto-promote eligible L1 overlays (Individual).
- Autopilot ≥6 → variant promote when fitness ≥0.9.
- `GET /v1/runs/{id}/evolution` — ledger timeline + pending.
- `POST /v1/runs/{id}/evolution/promote` — approve/reject prompt artifacts.

## Self-evolve curriculum (meta research)

`campaign_self_evolve` is a **meta** version of discover/research:

1. **`research_harness`** — study other agentic harnesses from `configs/self_evolve/harness_catalog.yaml` (Aider, OpenHands, Continue, …); write learnings + skill drafts (never mutate `packages/**`).
2. **`try_diverse_repo`** — sample distinct axes from `configs/self_evolve/diverse_repos.yaml`; capture transferable patterns under `.nimbusware/evolution/curriculum/`.
3. **`research_domain`** — when keywords are present, match `configs/self_evolve/domain_seeds.yaml` (accounting, healthcare, ecommerce, crm, …) or synthesize a GitHub search target; write `docs/learnings/domain/` + skill drafts.
4. **`distill_artifacts`** — L1/L2 propose-only pass over accumulated learnings.

Chat examples:

> Self evolve and get better. Study other agentic harnesses and try diverse projects distinct from what we know.

> Self evolve on accounting software — learn QuickBooks-class products and build domain knowledge.

Classifies as `self_evolve` → campaign start with profile `campaign_self_evolve`; domain keywords frozen onto `requirements`.

## Meta-loop

```text
diagnose.learn → L1/L2 propose
slice.gate → score skills / overlays
council track → action (incl. distill / variant / domain)
completion / launch-eval → promote or shelve
```
