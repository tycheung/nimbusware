# Collaborative chat — threat model (v1.2 Track B)

Normative mitigations for peanut-gallery sessions. Scope: invite links, LAN exposure, delegated write/interject.

## Assets

- Chat session turns, linked `run_id`, interjection queue.
- Invite tokens (`nimbusware_chat_invite`).
- Local user credentials (`nimbusware_user`).

## Threats and mitigations

| Threat | Impact | Mitigation |
|--------|--------|------------|
| **Invite token leak** | Unauthorized join with invited role | Expiring tokens; store SHA-256 hash only; one-time consume; default role `session_read`; HTTPS + `NIMBUSWARE_PUBLIC_BASE_URL` for link copy |
| **Open LAN / bind 0.0.0.0 without auth** | Anonymous API access | `NIMBUSWARE_COLLAB_ENABLED=1` requires session cookie or admin token on non-loopback; collab off preserves legacy loopback dev |
| **Guest interject / steer** | Agent manipulation | `session_write`+ required for turns and `POST …/interjection-queue` when collab on; `session_read` → 403; audit `actor_user_id` on queue item |
| **Cross-project session access** | Data leakage | Invites scoped to `session_id` + `project_id`; join validates token session |
| **Privilege escalation** | Guest becomes admin | Role changes `session_admin` only; promotion emits `system` turn |
| **Credential stuffing** | Account takeover | PBKDF2 password hashes; bootstrap owner on first signup only |
| **Cross-participant secret leak (SSE/theater)** | API keys in theater lines | `collab_output_redaction` on chat session SSE and theater stream; `ParticipantOutputPacket` wire format excludes vault secrets; mesh work units strip `connection_id` from cross-node payloads |
| **Per-participant cloud LLM with local vault** | Wrong node resolves another user's API key | `binding_credentials` resolves `connection_id` only on owning node (`user_id`-scoped vault); mesh `binding_hint` carries metadata only; worker resolves vault locally via `collab_mesh_context` |

## Residual risk

- Host machine compromise exposes local Postgres and event store (same as single-operator).
- Session SSE theater fan-out — mitigated by server-side redaction and **fo1867** API + Playwright dual-browser scan (`tests/api_http/test_collab_sse_secret_scan.py`, `tests/e2e/web/collab_sse_secret_scan.spec.ts`).

## Out of scope (v1.2)

- Mesh guest compute (Track D), host transfer consent (fo1780+), E2E encrypted invites.
