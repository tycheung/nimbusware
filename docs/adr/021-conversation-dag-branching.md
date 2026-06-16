# ADR 021: Conversation DAG and non-destructive branching

## Status

Accepted.

## Context

§20.27 shipped work-type routing but Chat used an in-memory flat `messages[]` list and redirected to Progress after run start. Operators expect a Cursor-like single thread with fork/restore that retains sibling branches.

## Decision

1. **Persistent store** — `nimbusware_chat_session` and `nimbusware_chat_turn` tables (or in-memory `ChatStore` when no Postgres URL); `parent_turn_id` forms a DAG.
2. **Active path** — `active_leaf_turn_id` on session; UI renders root→leaf turns only; `GET .../graph` exposes full DAG including siblings.
3. **Fork** — `POST .../fork` sets active leaf to a prior turn; next append creates a sibling branch; branches are never deleted.
4. **Branch navigation** — `PUT .../active-leaf` selects an existing leaf; congruent Chat tab stays primary observability surface.
5. **Mid-turn mode switch** — `POST .../turns/{id}/switch-mode` emits `work_type_switch` turn with `work_type_source: mode_switch`.
6. **MCP parity** — `nimbusware_chat_graph`, `nimbusware_chat_fork`, `nimbusware_chat_select_branch`.
7. **Execution alignment** — optional `replay_from_seq` on switch-mode payload; conversation branch remains orthogonal to run `replay-from` unless operator opts in.

## Consequences

- Chat sessions survive API restart when Postgres is configured.
- Progress tab remains the drill-down for full multi-agent theater; `#/chat?run_id=` deep links retain a live digest in the main thread.
- Flat `messages[]` on session GET is a projection of the active path for backward compatibility.

## Current UI (verified)

| Shipped | Not yet in Chat UI |
|---------|-------------------|
| Active-path thread, fork, sibling branch list + badges | Visual tree of turns; session history browser (`GET /chat/sessions` is API-only) |
| Inline theater SSE (last 12 lines, text digest) | Per-`actor_display` labels and full `body_md` (see Progress theater) |
