"""Shared runs route constants."""

from __future__ import annotations

# When ``include_summary=1``, list page size must stay small to avoid N+1 load.
INCLUDE_SUMMARY_MAX_LIMIT = 20

# Timeline summary emission policy (additive / presence-gated):
# - Integrator gate rows omit ranking/selection keys unless present in metadata.
# - Self-refinement omits ``max_iterations`` / ``max_iterations_exceeded`` unless
# ``max_iterations`` is a positive int on the policy marker metadata.
# - Helpers diverge on skip-vs-emit for degraded metadata
# do not unify integrator-gate skip logic with self-refinement emit-on-missing-meta.
