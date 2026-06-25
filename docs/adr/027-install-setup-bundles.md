# ADR 027: Install setup bundles (default vs enterprise)

## Status

Accepted (§20.33.6, Jun 2026).

## Context

Consumer archetypes A1 (Safe Coding) and A2 (Engineer workspace) share Individual edition,
Postgres posture, and Ollama install profiles. A3 (Enterprise AI) needs Enterprise edition,
strict env defaults, and fleet policy seeds. Operators previously chose edition via
`--edition` and LLM footprint via ADR 024 `recommended`/`barebones` only — no bundled
runtime defaults for autopilot, enforcement, slice budget, or collab.

## Decision

1. **`--setup-bundle`** — `default` (Individual safe-lean) or `enterprise` (strict); persisted
   as `NIMBUSWARE_SETUP_BUNDLE` in `.env`.
2. **SSOT** — `configs/install/bundles/{default,enterprise}.env.yaml` (+ optional `.config.yaml`).
3. **A1 + A2 merged at install** — first Maker launch prompts Safe Coding vs Engineer sub-choice
   (fo1950); install writes shared default env.
4. **Orthogonal to install profile** — ADR 024 `recommended`/`barebones` unchanged (Ollama size).
5. **Launcher** — Quick/Full use `default` bundle; new **Enterprise setup** uses `enterprise`.
6. **Interactive installer** — setup bundle prompt before install profile when TTY and not explicit.

## Consequences

- `docs/install-profiles.md` documents both dimensions.
- Maker bootstrap exposes `default_profiles` from env for first-run apply.
- Enterprise bundle may patch `fleet_enforcement_policies.yaml` default tenant min level on seed.

## References

- §20.33.6 `nimbusware-orchestrator-local-plan.md`
- ADR 024 install profiles
