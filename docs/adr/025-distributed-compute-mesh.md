# ADR 025: Distributed compute mesh (host-authoritative)

## Status

Accepted (v1.2 Track D0).

## Context

Parallel writer and critic stages today run via `asyncio.gather` on a single host. Track B collaborative sessions add participants whose GPUs/CPUs remain idle. Enterprise Redis fleet workers handle verify/campaign dispatch only — not LLM stage units tied to chat sessions.

## Decision

1. **Host-centric mesh** — the session host (project owner machine or Enterprise API pod) remains system of record: Postgres event store, workspace authority, chat thread, merge, and gates.
2. **Worker nodes** are stateless executors: they receive bounded `work_unit` envelopes (context packets, model binding snapshots) and return structured events for host replay — not peer-to-peer git or multi-master events.
3. **Node registry** — `nimbusware_compute_node` + heartbeat APIs; workers run `nimbusware-compute-worker` on full installs (LAN/Tailscale in v1.2).
4. **Scheduling** — `MeshScheduler` assigns parallelizable units (`writers`, `parallel_critics`) per session policy (`host_only`, `manual_claim`, `auto_share`, `auto_optimize`); sequential stages stay on host.
5. **Threat model** — workers never receive host admin tokens; session-scoped `compute_token` or Enterprise API key; workspace writes merged only on host; tool jail matches local JIT loop.

## Consequences

- `docs/compute-mesh.md` operator + worker runbook; `docs/audits/parallel-inventory.md` remote-eligibility matrix (fo1701).
- Phases D1–D8 ship incrementally; MVP stubs registry, queue, scheduler hook points, opt-in API, and UI placeholders.
- Host transfer (ADR 026) handles canonical host migration without multi-master Postgres.
