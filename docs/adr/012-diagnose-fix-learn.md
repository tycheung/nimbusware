# ADR 012: Diagnose-fix-learn loop

## Status

Accepted (amended 2026-07 — self-evolution).

## Decision

Failures write curated learnings under `docs/learnings/` with stack fingerprint; temporary debug probes under `.nimbusware/debug_probes/`.

## Amendment

`handle_gate_failure_learning` emits `diagnose.learn` then invokes `evolution_loop.after_diagnose_learn` to propose L1 prompt overlays and (on repeated fingerprints) L2 skill drafts. See ADR 035.
