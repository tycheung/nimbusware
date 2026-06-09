from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class DebugProbe:
    probe_id: str
    kind: str
    content: str
    temporary: bool = True


@dataclass
class DiagnoseLearnResult:
    fingerprint: str
    learning_path: Path | None = None
    probes: list[DebugProbe] = field(default_factory=list)
    detail: str = ""


def stack_fingerprint(error_text: str, *, stack: str = "") -> str:
    blob = f"{stack}|{error_text.strip()[:2000]}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def learnings_dir(workspace: Path) -> Path:
    path = workspace.resolve() / "docs" / "learnings"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_learning_doc(
    workspace: Path,
    *,
    title: str,
    body: str,
    fingerprint: str,
) -> Path:
    directory = learnings_dir(workspace)
    slug = fingerprint[:12]
    path = directory / f"{slug}.md"
    content = f"# {title}\n\nFingerprint: `{fingerprint}`\n\n{body.strip()}\n"
    path.write_text(content, encoding="utf-8")
    return path


def create_debug_probe(workspace: Path, *, kind: str, content: str) -> DebugProbe:
    probe_id = hashlib.sha256(f"{kind}:{content}".encode()).hexdigest()[:12]
    probe_dir = workspace.resolve() / ".nimbusware" / "debug_probes"
    probe_dir.mkdir(parents=True, exist_ok=True)
    path = probe_dir / f"{probe_id}.json"
    path.write_text(
        json.dumps(
            {
                "probe_id": probe_id,
                "kind": kind,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return DebugProbe(probe_id=probe_id, kind=kind, content=content)


def diagnose_from_failure(
    workspace: Path,
    *,
    error_text: str,
    stack: str = "",
) -> DiagnoseLearnResult:
    fp = stack_fingerprint(error_text, stack=stack)
    probe = create_debug_probe(workspace, kind="log_excerpt", content=error_text[:4000])
    learning_path = write_learning_doc(
        workspace,
        title="Regression failure learning",
        body=f"Observed failure:\n\n```\n{error_text[:2000]}\n```",
        fingerprint=fp,
    )
    return DiagnoseLearnResult(
        fingerprint=fp,
        learning_path=learning_path,
        probes=[probe],
        detail="learning_written",
    )


def agent_packet_from_learning(workspace: Path, fingerprint: str) -> dict[str, Any]:
    path = learnings_dir(workspace) / f"{fingerprint[:12]}.md"
    if not path.is_file():
        return {"available": False}
    return {
        "available": True,
        "fingerprint": fingerprint,
        "path": str(path),
        "excerpt": path.read_text(encoding="utf-8")[:2000],
    }
