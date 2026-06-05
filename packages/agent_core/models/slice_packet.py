"""Bounded context passed between Nimbusware roles for one micro-slice."""

from __future__ import annotations

from pydantic import BaseModel


class SliceVerdictSummary(BaseModel):
    critic_role: str = ""
    verdict: str = ""
    severity: str | None = None


class SliceContextPacket(BaseModel):
    slice_id: str
    paths: tuple[str, ...] = ()
    diff_unified: str = ""
    test_output: str = ""
    prior_verdicts: tuple[SliceVerdictSummary, ...] = ()
    policy_excerpt: str = ""
    memory_excerpt: str = ""
    repo_map_excerpt: str = ""

    def capped(self, *, max_chars: int) -> SliceContextPacket:
        if max_chars <= 0:
            return self
        budget = max_chars
        mem_cap = min(len(self.memory_excerpt), max(0, budget // 5))
        repo_cap = min(len(self.repo_map_excerpt), max(0, budget * 3 // 20))
        body_cap = max(0, budget - mem_cap - repo_cap)
        return SliceContextPacket(
            slice_id=self.slice_id,
            paths=self.paths,
            diff_unified=_truncate(self.diff_unified, body_cap // 3),
            test_output=_truncate(self.test_output, body_cap // 3),
            prior_verdicts=self.prior_verdicts,
            policy_excerpt=_truncate(self.policy_excerpt, body_cap // 4),
            memory_excerpt=_truncate(self.memory_excerpt, mem_cap),
            repo_map_excerpt=_truncate(self.repo_map_excerpt, repo_cap),
        )

    def char_count(self) -> int:
        return (
            len(self.slice_id)
            + sum(len(p) for p in self.paths)
            + len(self.diff_unified)
            + len(self.test_output)
            + sum(len(v.critic_role) + len(v.verdict) for v in self.prior_verdicts)
            + len(self.policy_excerpt)
            + len(self.memory_excerpt)
            + len(self.repo_map_excerpt)
        )


def _truncate(text: str, limit: int) -> str:
    from agent_core.context_budget import truncate_for_llm_history

    return truncate_for_llm_history(text, max_chars=limit)
