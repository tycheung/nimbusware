# Compute mesh (v1.2 Track D)

Host-authoritative distributed execution for parallel agent stages. See [ADR 025](adr/025-distributed-compute-mesh.md).

## Quick start (worker)

On a collaborator machine with a full Nimbusware install (LAN or Tailscale reachability to host):

```bash
poetry run nimbusware-compute-worker \
  --host-url https://<host>:8787 \
  --session-token <invite-compute-token> \
  --session-id <chat-session-uuid>
```

The worker registers once, then sends heartbeats and **pulls work units** from the host queue until stopped. Use `--no-pull` for heartbeat-only mode.

## Host APIs (MVP)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/compute/nodes?session_id=` | List nodes registered for a chat session |
| POST | `/v1/compute/nodes/register` | Register or refresh a compute node |
| POST | `/v1/compute/nodes/{id}/heartbeat` | Liveness + capabilities update |
| POST | `/v1/compute/work-units/claim` | Worker claims next queued unit for a session |
| POST | `/v1/compute/work-units/{id}/complete` | Worker reports stage result |
| POST | `/v1/compute/work-units/{id}/terminate-restart` | Cancel in-flight unit and re-queue (fo1782 handoff) |
| GET | `/v1/compute/work-units/queue?session_id=` | Host queue depth observability |
| POST | `/v1/chat/sessions/{id}/compute/opt-in` | Session compute sharing toggle |
| GET/PUT | `/v1/chat/sessions/{id}/optimizer-weights` | Session drag-priority optimizer weights (fo1788) |

Set `NIMBUSWARE_COMPUTE_WORK_QUEUE=postgres` (requires `NIMBUSWARE_DATABASE_URL`) for durable work units; `redis` for shared fleet queue; default in-memory for solo dev.

## Host merge (ADR 025)

When mesh assigns stages to remote nodes, the host **skips local execution** for those stages and waits on work-unit completion. Worker completion payloads carry **`replay_events`** (theater rows appended on the worker during stage execution) and, for writer stages, **`workspace_files`** (UTF-8 file patches). The host merges both via `mesh_host_sync.absorb_completed_mesh_units` after `wait_for_mesh_units`. Critic `gate_fail` and writer verifier results are read from the worker `complete` payload via `mesh_host_sync`.

## Reachability

v1.2 requires **LAN or Tailscale** between host and workers. Home readiness should warn when mesh is enabled without a tailnet (fo1773).

## Scheduler (D3)

`MeshScheduler` hooks `_run_writers_parallel_dispatch` when a chat session’s `workload_distribution` is not `host_only`. Remote stages enqueue work units for session-scoped workers; workers claim via `/v1/compute/work-units/claim`, execute on the claimer node (`execute_on: self`), and complete via `/v1/compute/work-units/{id}/complete`.

## Worker execution (MVP)

`nimbusware-compute-worker` pulls queued units after each heartbeat, runs a bounded local ack executor (`work_unit_execute.py`), and posts completion. Full stage runners on remote nodes remain a v1.3+ extension.

## Minimal mesh worker (v1.2+)

Shipped as `nimbusware-mesh-worker-minimal` — same register/heartbeat/work-unit protocol as the full worker, without requiring Maker UI or Postgres on the guest machine. On register it advertises `minimal_worker: true` plus a lightweight hardware/Ollama capability probe.

```bash
poetry run nimbusware-mesh-worker-minimal \
  --host-url https://<host>:8787 \
  --token <invite-compute-token> \
  --session-id <chat-session-uuid>
```

Use `--probe` to print capability JSON locally. Stage execution still uses bounded mesh executors (`mesh_stage_runner`) when work units are claimed.

## Future extensions

## Host transfer

When canonical host moves to another machine, use the host-transfer protocol ([ADR 026](adr/026-host-transfer.md)).

**Shipped:** timed consent, session freeze on accept, artifact bundle export/import, Postgres `nimbusware_host_transfer_request` (or in-memory for dev).

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/chat/sessions/{id}/host-transfer` | Request transfer to another user |
| GET | `/v1/chat/sessions/{id}/host-transfer` | List pending transfers |
| POST | `…/host-transfer/{transfer_id}/accept` | Target accepts → **frozen** + manifest |
| GET | `…/host-transfer/{transfer_id}/bundle` | Export artifact manifest |
| POST | `…/host-transfer/{transfer_id}/import` | Import bundle + complete cutover |
| POST | `…/host-transfer/{transfer_id}/complete` | Complete without re-import |

## Security (Track D7)

- **Worker sandbox** — remote stages run agent tools inside the same jail as host (`docs/deploy/agent-sandbox.md`); workers never receive host `.env` paths.
- **No cross-user secrets** — `nimbusware_compute.worker_policy.sanitize_work_unit_payload` strips `api_key`, `secret`, and similar keys before enqueue; work units carry `executor_user_id` only.
- **Packet caps** — default 512 KB JSON payload limit per work unit.
- **Reachability** — use LAN or Tailscale; do not expose worker register endpoints on the public internet without TLS and session tokens.
