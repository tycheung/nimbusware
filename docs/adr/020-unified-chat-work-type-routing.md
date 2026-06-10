# ADR 020: Unified chat and work-type routing

## Status

Accepted.

## Context

Operators need a single Maker entry point that classifies intent (patch, slice, campaign, factory, quick), routes to the correct workflow profile, and supports mid-run steering without spawning unnecessary campaigns.

## Decision

1. **Chat tab** (`#/chat`) is the primary Maker entry for attached projects. Classifier suggests `work_type` with rationale; operator may override before `POST /v1/chat/sessions/{id}/start`.
2. **`work_type` + `work_type_source`** are frozen on `run.created` metadata for audit (`classifier`, `operator_override`, `ide`).
3. **Patch lane** (`workflow_profile=patch`) runs a minimal stage graph with auto-apply policy caps; escalation to slice is offered in chat when patch gate fails.
4. **Interjection prefixes** extend ADR 013:
   - `[patch]` — insert one patch backlog slice at head (no campaign)
   - `[steer]` — inject into agent JIT volatile prompt
   - `[skip]` — defer current backlog slice
   - `[build]` — spawn campaign (existing)
5. **Autopilot level 8 “Nimble”** in `configs/autopilot/presets.yaml` is the default posture for patch runs (`stop_on_slice_test_fail`, `stop_at_terminal_review`).
6. **MCP parity** — `nimbusware_classify_intent`, `nimbusware_patch`, `nimbusware_interject`, `nimbusware_run_tests` mirror chat routing and steering for IDE agents.
7. **Optional LLM classifier** when `NIMBUSWARE_INTENT_CLASSIFIER_MODEL` is set; rules hard-override unsafe LLM routes; fallback to rules v0.

## Consequences

- Campaign and factory profiles are unchanged; patch is additive.
- Chat composes into Plan/Progress/Review rather than replacing the adversarial pipeline.
- Theater and maker-progress expose work type and classifier rationale on chat-routed runs.
