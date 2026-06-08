# ADR 008: Context artifacts file cache (Individual ship)

## Status

Accepted — Individual v1 / v1.1 ship path uses **project-scoped JSON file cache** under `.cache/nimbusware/context-artifacts/{project_id}/` with in-memory merge for tests.

## Context

Normative plan fo586 discussed Postgres persistence for context artifacts. Individual operators need durable artifacts across API restarts without requiring managed Postgres for local/dev installs.

## Decision

1. **Ship** context artifacts via `nimbusware_orchestrator.context_artifacts`:
   - In-memory bucket for unit tests
   - Optional on-disk JSON sidecars per artifact (`_persist_record` / `_load_project_from_disk`)
2. **Defer** dedicated Postgres table to Enterprise / fleet deployments where project metadata already lives in Postgres.
3. Project API (`GET/POST /v1/projects/{id}/context-artifacts`) and run insert/save-from-compaction routes operate on the merged memory+disk view.

## Consequences

- Artifacts survive API process restart on the same machine/repo root; fleet replicas must share storage or use export/import flows.
- File cache path is derived from `find_repo_root()` — document in operator README env `NIMBUSWARE_REPO_ROOT`.
- Future Postgres backing can replace `_persist_record` without changing HTTP contracts.

## Alternatives considered

| Option | Rejected because |
|--------|------------------|
| Postgres-only | Blocks Individual zip/attach installs without DB |
| Memory-only | Loses artifacts on restart; unsuitable for compaction save UX |
| Object store (S3) | Ops complexity for Individual tier |
