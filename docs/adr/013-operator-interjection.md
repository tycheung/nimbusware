# ADR 013: Operator interjection queue

## Status

Accepted.

## Decision

Per-run queue with **Next** (head) and **Last** (tail) priority; API at `/v1/runs/{id}/interjection-queue`. `[build]` prefix marks build-from-chat items.
