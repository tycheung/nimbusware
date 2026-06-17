"""Invoke ollama_setup.bootstrap_ollama from the API."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


def bootstrap_ollama_from_repo(
    repo_root: Path,
    *,
    choice: str | None = None,
    skip_pull: bool = True,
    log: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    scripts_install = repo_root.resolve() / "scripts" / "install"
    if str(scripts_install) not in sys.path:
        sys.path.insert(0, str(scripts_install))
    from ollama_setup import OllamaSetupError, bootstrap_ollama, ollama_api_host  # noqa: PLC0415

    writer = log or (lambda _msg: None)
    host = ollama_api_host()
    try:
        ok = bootstrap_ollama(
            repo=repo_root,
            host=host,
            choice=choice,
            non_interactive=True,
            skip_pull=skip_pull,
            models=None,
            enable_llm=False,
            log=writer,
        )
    except OllamaSetupError as exc:
        return {"ok": False, "message": str(exc), "base_url": host}
    return {
        "ok": bool(ok),
        "message": "Ollama is reachable" if ok else "Ollama bootstrap did not complete",
        "base_url": host,
    }
