"""Bounded context passed between Hermes roles for one micro-slice (fo154)."""

from __future__ import annotations

from pydantic import BaseModel, Field


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

    def capped(self, *, max_chars: int) -> SliceContextPacket:
        if max_chars <= 0:
            return self
        return SliceContextPacket(
            slice_id=self.slice_id,
            paths=self.paths,
            diff_unified=_truncate(self.diff_unified, max_chars // 3),
            test_output=_truncate(self.test_output, max_chars // 3),
            prior_verdicts=self.prior_verdicts,
            policy_excerpt=_truncate(self.policy_excerpt, max_chars // 4),
        )

    def char_count(self) -> int:
        return (
            len(self.slice_id)
            + sum(len(p) for p in self.paths)
            + len(self.diff_unified)
            + len(self.test_output)
            + sum(len(v.critic_role) + len(v.verdict) for v in self.prior_verdicts)
            + len(self.policy_excerpt)
        )


def _truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."
