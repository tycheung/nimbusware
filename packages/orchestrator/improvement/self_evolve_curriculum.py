from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import EventType, StagePassedEvent
from agent_core.models.events_payloads import StagePassedPayload
from maker.intent.domain_keywords import domain_keywords_from_rows
from orchestrator.improvement.improvement_council import ImprovementTrack
from orchestrator.merge import load_yaml
from orchestrator.profiles.autopilot_profiles import autopilot_profile_from_rows

DEFAULT_MIX = {
    ImprovementTrack.RESEARCH_HARNESS: 0.25,
    ImprovementTrack.TRY_DIVERSE_REPO: 0.2,
    ImprovementTrack.RESEARCH_DOMAIN: 0.35,
    ImprovementTrack.DISTILL_ARTIFACTS: 0.2,
}

DEFAULT_MIX_NO_DOMAIN = {
    ImprovementTrack.RESEARCH_HARNESS: 0.4,
    ImprovementTrack.TRY_DIVERSE_REPO: 0.35,
    ImprovementTrack.DISTILL_ARTIFACTS: 0.25,
}


def self_evolve_dir(workspace: Path) -> Path:
    path = workspace.resolve() / ".nimbusware" / "evolution" / "curriculum"
    path.mkdir(parents=True, exist_ok=True)
    return path


def tried_path(workspace: Path) -> Path:
    return self_evolve_dir(workspace) / "tried.json"


def load_tried(workspace: Path) -> dict[str, Any]:
    path = tried_path(workspace)
    if not path.is_file():
        return {"harnesses": [], "repos": [], "domains": [], "history": []}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"harnesses": [], "repos": [], "domains": [], "history": []}
    if not isinstance(raw, dict):
        return {"harnesses": [], "repos": [], "domains": [], "history": []}
    raw.setdefault("domains", [])
    return raw


def save_tried(workspace: Path, data: dict[str, Any]) -> None:
    tried_path(workspace).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_harness_catalog(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "self_evolve" / "harness_catalog.yaml"
    if not path.is_file():
        return []
    raw = load_yaml(path)
    entries = raw.get("harnesses") if isinstance(raw, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def load_diverse_repos(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "self_evolve" / "diverse_repos.yaml"
    if not path.is_file():
        return []
    raw = load_yaml(path)
    entries = raw.get("repos") if isinstance(raw, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def load_domain_seeds(repo_root: Path) -> list[dict[str, Any]]:
    path = repo_root / "configs" / "self_evolve" / "domain_seeds.yaml"
    if not path.is_file():
        return []
    raw = load_yaml(path)
    entries = raw.get("domains") if isinstance(raw, dict) else None
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def parse_self_evolve_block(workflow_doc: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(workflow_doc, dict):
        return {"enabled": False}
    block = workflow_doc.get("self_evolve")
    if not isinstance(block, dict):
        return {"enabled": False}
    mix_raw = block.get("mix") if isinstance(block.get("mix"), dict) else {}
    mix = {
        ImprovementTrack.RESEARCH_HARNESS: float(mix_raw.get("research_harness", 0.25)),
        ImprovementTrack.TRY_DIVERSE_REPO: float(mix_raw.get("try_diverse_repo", 0.2)),
        ImprovementTrack.RESEARCH_DOMAIN: float(mix_raw.get("research_domain", 0.35)),
        ImprovementTrack.DISTILL_ARTIFACTS: float(mix_raw.get("distill_artifacts", 0.2)),
    }
    return {
        "enabled": bool(block.get("enabled", True)),
        "council_every_n_slices": max(1, int(block.get("council_every_n_slices") or 2)),
        "min_autopilot": int(block.get("min_autopilot") or 8),
        "mix": mix,
    }


def effective_curriculum_mix(
    mix: dict[ImprovementTrack, float] | None,
    *,
    keywords: list[str],
) -> dict[ImprovementTrack, float]:
    """Drop domain track when operator gave no domain keywords."""
    base = dict(mix or DEFAULT_MIX)
    if keywords:
        base[ImprovementTrack.RESEARCH_DOMAIN] = max(
            float(base.get(ImprovementTrack.RESEARCH_DOMAIN, 0.35)),
            0.4,
        )
        return base
    return dict(DEFAULT_MIX_NO_DOMAIN)


def workflow_profile_from_rows(rows: list[dict[str, Any]]) -> str | None:
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata")
        if isinstance(meta, dict):
            wf = meta.get("workflow_profile")
            if isinstance(wf, str) and wf.strip():
                return wf.strip()
        payload = row.get("payload")
        if isinstance(payload, dict):
            wf = payload.get("workflow_profile")
            if isinstance(wf, str) and wf.strip():
                return wf.strip()
    return None


def is_self_evolve_run(rows: list[dict[str, Any]]) -> bool:
    wf = workflow_profile_from_rows(rows) or ""
    if wf == "campaign_self_evolve":
        return True
    for row in rows:
        if row.get("event_type") != EventType.RUN_CREATED.value:
            continue
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        if str(meta.get("work_type") or "").strip().lower() == "self_evolve":
            return True
    return False


def select_curriculum_track(
    workspace: Path,
    *,
    mix: dict[ImprovementTrack, float] | None = None,
    keywords: list[str] | None = None,
) -> ImprovementTrack:
    weights = effective_curriculum_mix(mix, keywords=list(keywords or []))
    tried = load_tried(workspace)
    history = tried.get("history") if isinstance(tried.get("history"), list) else []
    scores: dict[ImprovementTrack, float] = {}
    for track, weight in weights.items():
        if weight <= 0:
            continue
        recent = sum(1 for h in history[-6:] if h == track.value)
        scores[track] = weight / (1.0 + recent)
    if ImprovementTrack.RESEARCH_HARNESS in scores and not tried.get("harnesses"):
        scores[ImprovementTrack.RESEARCH_HARNESS] += 0.15
    if ImprovementTrack.TRY_DIVERSE_REPO in scores and not tried.get("repos"):
        scores[ImprovementTrack.TRY_DIVERSE_REPO] += 0.1
    if ImprovementTrack.RESEARCH_DOMAIN in scores and keywords and not tried.get("domains"):
        scores[ImprovementTrack.RESEARCH_DOMAIN] += 0.2
    if not scores:
        return ImprovementTrack.DISTILL_ARTIFACTS
    return max(scores, key=lambda t: scores[t])


def pick_next_harness(repo_root: Path, workspace: Path) -> dict[str, Any] | None:
    tried = load_tried(workspace)
    seen = {str(x) for x in (tried.get("harnesses") or [])}
    for entry in load_harness_catalog(repo_root):
        hid = str(entry.get("id") or "").strip()
        if hid and hid not in seen:
            return entry
    catalog = load_harness_catalog(repo_root)
    return catalog[0] if catalog else None


def pick_next_repo(repo_root: Path, workspace: Path) -> dict[str, Any] | None:
    tried = load_tried(workspace)
    seen = {str(x) for x in (tried.get("repos") or [])}
    for entry in load_diverse_repos(repo_root):
        rid = str(entry.get("id") or "").strip()
        if rid and rid not in seen:
            return entry
    catalog = load_diverse_repos(repo_root)
    return catalog[0] if catalog else None


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "domain")[:48]


def resolve_domain_candidates(
    repo_root: Path,
    *,
    keywords: list[str],
) -> list[dict[str, Any]]:
    """Match seed catalog to keywords; else synthesize search-style study targets."""
    if not keywords:
        return []
    joined = " ".join(keywords).lower()
    matched: list[dict[str, Any]] = []
    for domain in load_domain_seeds(repo_root):
        match_tokens = domain.get("match") if isinstance(domain.get("match"), list) else []
        tokens = [str(t).lower() for t in match_tokens]
        if not any(t in joined or any(t in k for k in keywords) for t in tokens):
            continue
        seeds = domain.get("seeds") if isinstance(domain.get("seeds"), list) else []
        for seed in seeds:
            if not isinstance(seed, dict):
                continue
            entry = dict(seed)
            entry["domain_id"] = str(domain.get("id") or "domain")
            entry["keywords"] = list(keywords)
            matched.append(entry)
    if matched:
        return matched
    query = "+".join(_slug(k).replace("-", "+") for k in keywords[:4])
    return [
        {
            "id": f"synth-{_slug('-'.join(keywords[:3]))}",
            "url": f"https://github.com/search?q={query}&type=repositories",
            "tags": list(keywords),
            "focus": list(keywords),
            "domain_id": "synthetic",
            "keywords": list(keywords),
            "synthetic": True,
            "query": " ".join(keywords),
        },
    ]


def pick_next_domain_target(
    repo_root: Path,
    workspace: Path,
    *,
    keywords: list[str],
) -> dict[str, Any] | None:
    tried = load_tried(workspace)
    seen = {str(x) for x in (tried.get("domains") or [])}
    candidates = resolve_domain_candidates(repo_root, keywords=keywords)
    for entry in candidates:
        eid = str(entry.get("id") or "").strip()
        if eid and eid not in seen:
            return entry
    return candidates[0] if candidates else None


def mark_tried(
    workspace: Path,
    *,
    harness_id: str | None = None,
    repo_id: str | None = None,
    domain_id: str | None = None,
    track: ImprovementTrack | None = None,
) -> None:
    data = load_tried(workspace)
    if harness_id:
        harnesses = list(data.get("harnesses") or [])
        if harness_id not in harnesses:
            harnesses.append(harness_id)
        data["harnesses"] = harnesses
    if repo_id:
        repos = list(data.get("repos") or [])
        if repo_id not in repos:
            repos.append(repo_id)
        data["repos"] = repos
    if domain_id:
        domains = list(data.get("domains") or [])
        if domain_id not in domains:
            domains.append(domain_id)
        data["domains"] = domains
    if track is not None:
        history = list(data.get("history") or [])
        history.append(track.value)
        data["history"] = history[-50:]
    save_tried(workspace, data)


def run_research_harness_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    from orchestrator.improvement.improvement_council_backlog import queue_council_backlog_slice
    from orchestrator.improvement.skill_evolution import propose_skill_from_fingerprint

    entry = pick_next_harness(repo_root, workspace)
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    if entry is None:
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc,
                ),
                metadata={"research_harness": {"skipped": True, "reason": "empty_catalog"}},
                payload=StagePassedPayload(stage_name="research.harness.skipped", duration_ms=0),
            ),
        )
        return {"skipped": True}
    hid = str(entry.get("id") or "unknown")
    url = str(entry.get("url") or "")
    focus = entry.get("focus") if isinstance(entry.get("focus"), list) else []
    distinct = str(entry.get("distinct_from") or "")
    summary = (
        f"Meta-research agentic harness `{entry.get('name') or hid}` ({url}). "
        f"Focus: {', '.join(str(f) for f in focus)}. Distinct: {distinct}. "
        "Distill reusable skills/overlays only — do not copy into packages/**."
    )
    learning_dir = workspace.resolve() / "docs" / "learnings"
    learning_dir.mkdir(parents=True, exist_ok=True)
    learning_path = learning_dir / f"harness-{hid}.md"
    learning_path.write_text(
        f"# Harness study: {hid}\n\n{summary}\n\nSource: {url}\n",
        encoding="utf-8",
    )
    propose_skill_from_fingerprint(
        store,
        rid,
        workspace,
        fingerprint=f"harness-{hid}",
        excerpt=summary,
    )
    queue_council_backlog_slice(
        store,
        rid,
        workspace,
        ImprovementTrack.RESEARCH_HARNESS,
        rationale_override=f"Study harness {hid} and distill agent-loop improvements",
        target_paths_override=(".nimbusware/evolution/", "docs/learnings/"),
    )
    mark_tried(workspace, harness_id=hid, track=ImprovementTrack.RESEARCH_HARNESS)
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ),
            metadata={
                "research_harness": {
                    "harness_id": hid,
                    "url": url,
                    "learning_path": str(learning_path),
                    "skill_ids_used": [f"evolved-harness-{hid}"[:32]],
                },
            },
            payload=StagePassedPayload(stage_name="research.harness", duration_ms=0),
        ),
    )
    return {"harness_id": hid, "url": url}


def run_try_diverse_repo_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    from orchestrator.improvement.improvement_council_backlog import queue_council_backlog_slice

    entry = pick_next_repo(repo_root, workspace)
    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    if entry is None:
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc,
                ),
                metadata={"try_diverse_repo": {"skipped": True, "reason": "empty_catalog"}},
                payload=StagePassedPayload(stage_name="try.diverse_repo.skipped", duration_ms=0),
            ),
        )
        return {"skipped": True}
    repo_id = str(entry.get("id") or "unknown")
    url = str(entry.get("url") or "")
    tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
    axis = str(entry.get("distinct_axis") or "")
    summary = (
        f"Diverse repo trial `{repo_id}` ({url}). Tags: {', '.join(str(t) for t in tags)}. "
        f"Distinct axis: {axis}. Smoke-study patterns; write learnings; no packages/** mutation."
    )
    trial_dir = self_evolve_dir(workspace) / "trials"
    trial_dir.mkdir(parents=True, exist_ok=True)
    trial_path = trial_dir / f"{repo_id}.md"
    trial_path.write_text(f"# Repo trial: {repo_id}\n\n{summary}\n", encoding="utf-8")
    learning_dir = workspace.resolve() / "docs" / "learnings"
    learning_dir.mkdir(parents=True, exist_ok=True)
    (learning_dir / f"repo-{repo_id}.md").write_text(
        f"# Diverse repo learning: {repo_id}\n\n{summary}\n",
        encoding="utf-8",
    )
    queue_council_backlog_slice(
        store,
        rid,
        workspace,
        ImprovementTrack.TRY_DIVERSE_REPO,
        rationale_override=f"Trial diverse repo {repo_id} ({axis}) and capture transferable patterns",
        target_paths_override=(".nimbusware/evolution/curriculum/", "docs/learnings/"),
    )
    mark_tried(workspace, repo_id=repo_id, track=ImprovementTrack.TRY_DIVERSE_REPO)
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ),
            metadata={
                "try_diverse_repo": {
                    "repo_id": repo_id,
                    "url": url,
                    "distinct_axis": axis,
                    "trial_path": str(trial_path),
                },
            },
            payload=StagePassedPayload(stage_name="try.diverse_repo", duration_ms=0),
        ),
    )
    return {"repo_id": repo_id, "url": url}


def run_research_domain_track(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    *,
    repo_root: Path,
    keywords: list[str],
) -> dict[str, Any]:
    """Study domain-specific software from operator keywords; write domain knowledge."""
    from orchestrator.improvement.improvement_council_backlog import queue_council_backlog_slice
    from orchestrator.improvement.skill_evolution import propose_skill_from_fingerprint

    rid = UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id
    if not keywords:
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc,
                ),
                metadata={"research_domain": {"skipped": True, "reason": "no_keywords"}},
                payload=StagePassedPayload(stage_name="research.domain.skipped", duration_ms=0),
            ),
        )
        return {"skipped": True, "reason": "no_keywords"}
    entry = pick_next_domain_target(repo_root, workspace, keywords=keywords)
    if entry is None:
        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=rid,
                occurred_at=__import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc,
                ),
                metadata={"research_domain": {"skipped": True, "reason": "no_targets"}},
                payload=StagePassedPayload(stage_name="research.domain.skipped", duration_ms=0),
            ),
        )
        return {"skipped": True, "reason": "no_targets"}
    eid = str(entry.get("id") or "unknown")
    url = str(entry.get("url") or "")
    domain_id = str(entry.get("domain_id") or "domain")
    focus = entry.get("focus") if isinstance(entry.get("focus"), list) else []
    tags = entry.get("tags") if isinstance(entry.get("tags"), list) else []
    kw = ", ".join(keywords)
    summary = (
        f"Domain research for keywords [{kw}] via `{eid}` ({url}). "
        f"Domain bucket: {domain_id}. Tags: {', '.join(str(t) for t in tags)}. "
        f"Focus: {', '.join(str(f) for f in focus)}. "
        "Capture domain vocabulary, workflows, data models, and product patterns into "
        "learnings/skills — do not mutate packages/**."
    )
    learning_dir = workspace.resolve() / "docs" / "learnings" / "domain"
    learning_dir.mkdir(parents=True, exist_ok=True)
    learning_path = learning_dir / f"{_slug(domain_id)}-{eid}.md"
    learning_path.write_text(
        (
            f"# Domain knowledge: {kw}\n\n"
            f"{summary}\n\n"
            f"## Study checklist\n"
            f"- Product categories and competitors in this vertical\n"
            f"- Core entities / workflows unique to this domain\n"
            f"- Open-source exemplars and architecture patterns\n"
            f"- Compliance / domain constraints worth encoding as skills\n\n"
            f"Source: {url}\n"
        ),
        encoding="utf-8",
    )
    domain_dir = self_evolve_dir(workspace) / "domain"
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / f"{eid}.md").write_text(
        f"# Domain target: {eid}\n\nKeywords: {kw}\n\n{summary}\n",
        encoding="utf-8",
    )
    propose_skill_from_fingerprint(
        store,
        rid,
        workspace,
        fingerprint=f"domain-{domain_id}-{eid}",
        excerpt=summary,
    )
    queue_council_backlog_slice(
        store,
        rid,
        workspace,
        ImprovementTrack.RESEARCH_DOMAIN,
        rationale_override=(
            f"Build domain knowledge for [{kw}] from {eid}; write learnings/skills only"
        ),
        target_paths_override=(
            ".nimbusware/evolution/",
            "docs/learnings/domain/",
        ),
    )
    mark_tried(workspace, domain_id=eid, track=ImprovementTrack.RESEARCH_DOMAIN)
    store.append(
        StagePassedEvent(
            event_type=EventType.STAGE_PASSED,
            event_id=uuid4(),
            run_id=rid,
            occurred_at=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc,
            ),
            metadata={
                "research_domain": {
                    "target_id": eid,
                    "domain_id": domain_id,
                    "url": url,
                    "keywords": list(keywords),
                    "learning_path": str(learning_path),
                    "synthetic": bool(entry.get("synthetic")),
                },
            },
            payload=StagePassedPayload(stage_name="research.domain", duration_ms=0),
        ),
    )
    return {"target_id": eid, "url": url, "keywords": list(keywords)}


def maybe_run_self_evolve_curriculum_tick(
    store: Any,
    run_id: UUID | str,
    workspace: Path,
    rows: list[dict[str, Any]],
    *,
    slices_completed: int,
    repo_root: Path | None = None,
) -> bool:
    """Curriculum tick for campaign_self_evolve — harness / diverse / domain / distill."""
    if not is_self_evolve_run(rows):
        return False
    from env import find_repo_root
    from orchestrator.improvement.evolution_loop import run_distill_artifacts
    from orchestrator.slice.cycle_improvement import execute_improvement_track
    from orchestrator.workflow.profiles import workflow_profile_dict

    root = (repo_root or find_repo_root(start=workspace)).resolve()
    profile = autopilot_profile_from_rows(rows)
    wf_name = workflow_profile_from_rows(rows) or "campaign_self_evolve"
    try:
        wf_doc = workflow_profile_dict(root, wf_name)
    except (FileNotFoundError, KeyError, OSError, ValueError, UnicodeDecodeError):
        wf_doc = {"self_evolve": {"enabled": True}}
    cfg = parse_self_evolve_block(wf_doc)
    if not cfg.get("enabled"):
        return False
    if profile.level < int(cfg["min_autopilot"]):
        return False
    every_n = int(cfg["council_every_n_slices"])
    if slices_completed <= 0 or slices_completed % every_n != 0:
        return False
    keywords = domain_keywords_from_rows(rows)
    track = select_curriculum_track(
        workspace,
        mix=cfg.get("mix"),
        keywords=keywords,
    )
    if track == ImprovementTrack.DISTILL_ARTIFACTS:
        run_distill_artifacts(store, run_id, workspace)
        mark_tried(workspace, track=track)
        from datetime import datetime, timezone

        store.append(
            StagePassedEvent(
                event_type=EventType.STAGE_PASSED,
                event_id=uuid4(),
                run_id=UUID(str(run_id)) if not isinstance(run_id, UUID) else run_id,
                occurred_at=datetime.now(timezone.utc),
                metadata={"distill_artifacts": {"via": "self_evolve_curriculum"}},
                payload=StagePassedPayload(stage_name="distill.artifacts", duration_ms=0),
            ),
        )
    elif track == ImprovementTrack.RESEARCH_DOMAIN:
        run_research_domain_track(
            store,
            run_id,
            workspace,
            repo_root=root,
            keywords=keywords,
        )
    else:
        execute_improvement_track(
            store,
            run_id,
            workspace,
            track,
            repo_root=root,
        )
    return True
