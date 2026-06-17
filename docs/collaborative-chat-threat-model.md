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
| **Enterprise external collaborators** | Off-org access | Tenant `allow_external_collaborators` default false (config stub B5) |

## Residual risk

- Host machine compromise exposes local Postgres and event store (same as single-operator).
- SSE room is stub fan-out without E2E encryption of theater content — acceptable on trusted operator networks; Enterprise uses ingress TLS.

## Out of scope (v1.2)

- Mesh guest compute (Track D), host transfer consent (fo1780+), E2E encrypted invites.
