# ADR 023: Collaborative chat sessions

## Status

Accepted (v1.2 Track B).

## Context

ADR 021 shipped single-operator congruent Chat (`nimbusware_chat_session`, turn DAG). Operators need to invite humans into the same session thread with scoped permissions — the “peanut gallery” — without building a general messaging product.

## Decision

1. **Identity** — `nimbusware_user` (local username/password on Individual; IAM-linked on Enterprise). Auth APIs under `/v1/auth/*`; session cookie when `NIMBUSWARE_COLLAB_ENABLED=1`.
2. **Session membership** — `nimbusware_chat_participant` with roles `session_read`, `session_write`, `session_admin`. Invites via `nimbusware_chat_invite` + `POST /v1/chat/join`.
3. **Host** — `host_user_id` on session (canonical merge machine); distinct from `session_admin` (many admins allowed).
4. **Permissions** — `session_write`+ for user/participant turns and interjection; `session_admin` for invites, revokes, workload mode. Read-only guests watch via SSE; composer hidden.
5. **Workload** — `workload_distribution` on session (`host_only` default; `manual_claim`, `auto_share`, `auto_optimize` reserved).
6. **Real-time** — `GET /v1/chat/sessions/{id}/stream` SSE room fan-out (theater lines to all participants).
7. **Library (B8)** — Folders/tags on session `metadata` JSON; bulk ACL deferred to `docs/conversation-library.md`.

## Edition matrix

| Concern | Individual | Enterprise |
|---------|------------|------------|
| Accounts | Local signup on host | Directory + OIDC display names |
| Invites | Signed join URL | Org user search; external email gated by tenant policy |
| Canonical state | Host Postgres + API | Tenant Postgres + fleet |

## Non-goals

- Slack-style channels, DMs, or org-wide chat.
- Cross-tenant grants or session merge across projects.
- Replacing external webhook steering (`docs/integrations-external-chat.md`).

## Consequences

- Loopback-open dev preserved when `NIMBUSWARE_COLLAB_ENABLED=0`.
- Participant enforcement is API-side; UI gates composer for `session_read`.
- Threat model: `docs/collaborative-chat-threat-model.md`.
