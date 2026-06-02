from __future__ import annotations

from typing import Any

from hermes_research.read_model import research_summary_from_events


def planner_research_context_from_events(events: list[dict[str, Any]]) -> str:
    summary = research_summary_from_events(events)
    lines: list[str] = []
    for brief in summary.get("domain_briefs") or []:
        if isinstance(brief, dict):
            lines.append(
                f"Domain research ({brief.get('domain_tag', 'general')}): "
                f"{brief.get('summary', '')}",
            )
    for brief in summary.get("code_briefs") or []:
        if isinstance(brief, dict):
            lines.append(f"Code research: {brief.get('summary', '')}")
    for pattern in summary.get("patterns") or []:
        if isinstance(pattern, dict):
            paths = pattern.get("paths") or []
            path_preview = ", ".join(str(p) for p in paths[:5])
            lines.append(
                f"Indexed pattern {pattern.get('pattern_id', '')} "
                f"({pattern.get('license', '')}): {path_preview}",
            )
    if not lines:
        return ""
    return "Research context for planning:\n" + "\n".join(f"- {line}" for line in lines[:12])
