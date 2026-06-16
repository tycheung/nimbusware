from __future__ import annotations

from pathlib import Path

from agent_core.prompt_tiers import stable_slice_agent_block
from nimbusware_env import find_repo_root

_DEFAULT_STABLE_REL = Path("configs") / "prompts" / "agent_implement_stable.txt"


def agent_implement_stable_path(*, repo_root: Path | None = None) -> Path:
    root = repo_root or find_repo_root()
    return root / _DEFAULT_STABLE_REL


def load_agent_implement_stable_prompt(*, repo_root: Path | None = None) -> str:
    path = agent_implement_stable_path(repo_root=repo_root)
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return (
        "Implement one micro-slice using ONLY allowlisted tools.\n"
        "Read before edit; prefer edit over write; shell only for pytest or ruff."
    )


def build_agent_stable_prompt(
    *,
    base_prompt: str | None = None,
    tool_list: str | None = None,
    repo_root: Path | None = None,
) -> str:
    rules = load_agent_implement_stable_prompt(repo_root=repo_root)
    if tool_list:
        rules = rules.replace(
            "read, write, edit, grep, shell (optional: find, ls when enabled).",
            tool_list,
        )
    if base_prompt and base_prompt.strip():
        rules = f"{base_prompt.strip()}\n{rules}"
    return stable_slice_agent_block(tool_rules=rules)
