# Compute mesh (v1.2 Track D)

Host-authoritative distributed execution for parallel agent stages. See [ADR 025](adr/025-distributed-compute-mesh.md).

## Quick start (worker)

On a collaborator machine with a full Nimbusware install (LAN or Tailscale reachability to host):

```bash
poetry run nimbusware-compute-worker \
  --host-url https://<host>:8787 \
  --session-token <invite-compute-token>
```

The worker registers once, then sends heartbeats until stopped.

## Host APIs (MVP)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/v1/compute/nodes/register` | Register or refresh a compute node |
| POST | `/v1/compute/nodes/{id}/heartbeat` | Liveness + capabilities update |
| POST | `/v1/chat/sessions/{id}/compute/opt-in` | Session compute sharing toggle |

## Reachability

v1.2 requires **LAN or Tailscale** between host and workers. Home readiness should warn when mesh is enabled without a tailnet (fo1773).

## Future minimal worker agent

Not shipped in v1.2. A reduced-footprint agent would sync only: node registry client, hardware/Ollama probe, work-unit pull/execute, and bounded stage executors — without full Maker UI or Postgres. Protocol remains the same register/heartbeat/work-unit envelopes documented in `alllms.md` § Track D.

## Host transfer

When canonical host moves to another machine, use the host-transfer protocol ([ADR 026](adr/026-host-transfer.md)): timed consent, session-scoped freeze, artifact bundle import on the new host.
