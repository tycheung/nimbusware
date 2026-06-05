"""Cross-slice handoff summary carried between micro-slices."""

from __future__ import annotations

import re

from pydantic import BaseModel


class SliceHandoffSummary(BaseModel):
    goal: str = ""
    progress: tuple[str, ...] = ()
    key_decisions: tuple[str, ...] = ()
    next_steps: tuple[str, ...] = ()
    read_files: tuple[str, ...] = ()
    modified_files: tuple[str, ...] = ()

    def render_markdown(self) -> str:
        lines = ["## Goal", self.goal or "(none)", "", "## Progress"]
        lines.extend(f"- {p}" for p in self.progress) or lines.append("- (none)")
        lines.extend(["", "## Key decisions"])
        lines.extend(f"- {d}" for d in self.key_decisions) or lines.append("- (none)")
        lines.extend(["", "## Next steps"])
        lines.extend(f"- {n}" for n in self.next_steps) or lines.append("- (none)")
        lines.append("")
        lines.append("<read-files>")
        lines.extend(self.read_files)
        lines.append("</read-files>")
        lines.append("")
        lines.append("<modified-files>")
        lines.extend(self.modified_files)
        lines.append("</modified-files>")
        return "\n".join(lines)

    @classmethod
    def parse_sections(cls, text: str) -> SliceHandoffSummary:
        goal = _section(text, "Goal") or ""
        progress = _bullets(_section(text, "Progress"))
        decisions = _bullets(_section(text, "Key decisions"))
        next_steps = _bullets(_section(text, "Next steps"))
        read_files = _xml_paths(text, "read-files")
        modified_files = _xml_paths(text, "modified-files")
        return cls(
            goal=goal,
            progress=progress,
            key_decisions=decisions,
            next_steps=next_steps,
            read_files=read_files,
            modified_files=modified_files,
        )


def _section(text: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\n<|\Z)"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ""
    return match.group(1).strip()


def _bullets(block: str) -> tuple[str, ...]:
    items: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return tuple(items)


def _xml_paths(text: str, tag: str) -> tuple[str, ...]:
    pattern = rf"<{tag}>\s*(.*?)\s*</{tag}>"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return ()
    paths: list[str] = []
    for line in match.group(1).splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            paths.append(line.replace("\\", "/"))
    return tuple(dict.fromkeys(paths))
