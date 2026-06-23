# ADR 026: Collaborative session host transfer

## Status

Accepted (v1.2 Track D8 — shipped Jun 2026).

## Context

Track B collaborative sessions designate a **host** (canonical Postgres, workspace, merge). Operators may need to move host authority to another `session_admin` machine (laptop handoff) or Enterprise fleet coordinator without multi-master replication.

## Decision

1. **Bidirectional request** — `POST /v1/chat/sessions/{id}/host-transfer`: (a) session_admin requests to become host, or (b) current host nominates another admin.
2. **Timed consent** — current host accepts/declines before `consent_expires_at` (tenant default `host_transfer_consent_hours`, typically 24h).
3. **Session-scoped freeze** — on accept, freeze turns, claims, and in-flight work units for that `session_id` only.
4. **Artifact bundle** — new host imports workspace paths + session-scoped rows into local Postgres (Individual recommended install); Enterprise updates `host_user_id` in tenant Postgres without laptop migration.
5. **Events** — `host.transfer.requested`, `host.transfer.completed` appended to event store for audit.

## Consequences

- Table `nimbusware_host_transfer_request` (see normative plan **§20.30.4**); decline API shipped.
- Compute mesh workers re-register against new host base URL after cutover.
- Declined or expired requests leave host unchanged.
