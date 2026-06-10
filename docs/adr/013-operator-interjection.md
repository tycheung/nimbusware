# ADR 013: Operator interjection queue

## Status

Accepted.

## Decision

Per-run queue with **Next** (head) and **Last** (tail) priority; API at `/v1/runs/{id}/interjection-queue`. Message prefixes: `[build]` (spawn campaign), `[patch]` (head patch slice), `[steer]` (JIT volatile prompt), `[skip]` (defer backlog slice). Extended in [ADR 020](020-unified-chat-work-type-routing.md).
