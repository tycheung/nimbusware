# Parallel execution inventory (fo1701)

Matrix: every parallel dispatch site → remote mesh eligibility. **Exit:** signed off in [ADR 025](../adr/025-distributed-compute-mesh.md).

| Site | Module / workflow | Parallelism | Remote eligible (v1.2) | Notes |
|------|-------------------|-------------|------------------------|-------|
| Writer group | `writers.py`, `parallel_group: writers` | `implementation`, `test_writer`, `frontend_writer` | **Yes** | Disjoint packets; host merges `workspace_files` after remote complete |
| Parallel critics | `lifecycle_verify.py`, `parallel_critics_enabled` | `security_critic`, `performance_critic`, `network_resilience_critic` | **Yes** | Read-only inputs; JSON verdict |
| Redis verify dispatch | `run_dispatch.py`, `run_worker.py` | verify shards | **Stretch (Enterprise)** | Existing fleet queue; host merges logs |
| Campaign ticks | `campaign_driver` | independent ticks | **No (post-v1.2)** | Host-orchestrated chain |
| Plan / slice.plan | orchestrator | sequential | **No** | Strong consistency |
| Gates / stitch / integrator | orchestrator | sequential | **No** | Workspace lock on host |

## Scheduler policies

| Policy | Remote behavior |
|--------|-----------------|
| `host_only` | All units on host (default) |
| `manual_claim` | Remote only for claimed roles on claimer node |
| `auto_share` | Opted-in nodes when model fits; else host bindings |
| `auto_optimize` | Optimizer across delegate-capable nodes |
