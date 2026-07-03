# compute

**Distributed compute mesh** — node registry, work-unit queue, and worker execution policy.

## Responsibility

- Register and heartbeat compute nodes (`compute/node_registry.py`, API `/v1/compute/*`)
- Queue and dispatch work units for mesh worker stages
- Session compute opt-in from Maker chat

## CLI

```bash
poetry run nimbusware-compute-worker
poetry run nimbusware-mesh-worker-minimal   # minimal worker profile
```

## Docs

- [compute-mesh.md](../../docs/compute-mesh.md)
- [ADR 025](../../docs/adr/025-distributed-compute-mesh.md)
- [packages/README.md](../README.md)
