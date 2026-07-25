# ADR 016: Repo exploration and variant arena

## Status

Accepted (amended 2026-07 — evolution ledger).

## Decision

`CodeGraphIndex` + `repo.explore` findings; variant worktrees scored by test pass + LOC penalty with Pareto-style winner selection.

## Amendment

`VARIANT_EXPERIMENT` emits `evolution.promoted` / `.rejected` via the evolution ledger. Promote is denied when the winner touches forbidden prefixes (`packages/`, `.cursor/`, …). Arena is skipped while L1/L2 proposals are pending. See ADR 035.
