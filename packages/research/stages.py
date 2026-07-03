from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from agent_core.models import (
    CriticVerdictEmittedEvent,
    CriticVerdictEmittedPayload,
    DomainCriticProposedEvent,
    DomainCriticProposedPayload,
    EventType,
    ResearchBriefEmittedEvent,
    ResearchBriefEmittedPayload,
    ResearchBriefSourcePayload,
    ResearchPatternIndexedEvent,
    ResearchPatternIndexedPayload,
    Severity,
    StageStartedEvent,
    StageStartedPayload,
    Verdict,
)
from extensions.extension_runtime import UniversalCritiqueRouter
from orchestrator.registry import RoleRegistry
from research.artifacts import persist_research_brief
from research.bundle_promotion import (
    primary_stack_id_from_requirements,
    write_catalog_candidate,
)
from research.enterprise_index import append_enterprise_research_index
from research.models import ResearchBrief, ResearchBriefSource
from research.pattern_index import append_pattern_index, new_pattern_id
from research.prompt_security import wrap_researcher_prompt
from research.stage_builder import (
    code_brief_summary,
    domain_brief_summary,
    infer_domain_tag,
    select_research_patterns,
)
from store.protocol import EventStore


def _emit_critique_panel(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    stage_name: str,
    producer_key: str,
) -> None:
    producer = registry.resolve(producer_key)
    store.append(
        StageStartedEvent(
            event_type=EventType.STAGE_STARTED,
            event_id=uuid4(),
            run_id=run_id,
            occurred_at=datetime.now(timezone.utc),
            payload=StageStartedPayload(stage_name=stage_name, attempt=1),
        ),
    )
    critic_payloads: list[CriticVerdictEmittedPayload] = []
    for tax_key in critique_router.pairing_for(producer_key):
        critic_role = registry.resolve(tax_key)
        payload = CriticVerdictEmittedPayload(
            critic_role=critic_role,
            verdict=Verdict.PASS,
            severity=Severity.LOW,
            owner_role=producer,
            is_in_domain=True,
            evidence_refs=[f"artifact://research/{stage_name}"],
        )
        store.append(
            CriticVerdictEmittedEvent(
                event_type=EventType.CRITIC_VERDICT_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=critic_role,
                payload=payload,
            ),
        )
        critic_payloads.append(payload)
    from orchestrator.llm.common import _finalize_critique_gate

    _finalize_critique_gate(
        store,
        run_id=run_id,
        stage_name=stage_name,
        critic_payloads=critic_payloads,
    )


def emit_research_stages(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    repo_root: Any,
    requirements: dict[str, Any] | None,
    research_meta: dict[str, Any],
    live: bool = False,
) -> None:
    domain_tag = infer_domain_tag(requirements)
    domain_enabled = bool(research_meta.get("domain_enabled", True))
    code_enabled = bool(research_meta.get("code_enabled", True))
    live = live or bool(research_meta.get("live", False))
    repo_path = Path(repo_root) if repo_root else Path(".")

    if domain_enabled:
        raw_domain_summary = domain_brief_summary(requirements, domain_tag=domain_tag)
        if isinstance(requirements, dict):
            prompt_bit = str(requirements.get("business_prompt") or "")
            if prompt_bit.strip():
                raw_domain_summary = wrap_researcher_prompt(
                    prompt_bit,
                    role="domain_researcher",
                )
        domain_brief = ResearchBrief(
            brief_kind="domain",
            domain_tag=domain_tag,
            summary=raw_domain_summary[:4000],
            artifact_id=str(uuid4()),
            sources=(
                ResearchBriefSource(
                    url=f"requirements://domain/{domain_tag}",
                    license="MIT",
                    trust_tier="high" if live else "medium",
                ),
            ),
        )
        persist_research_brief(repo_root, domain_brief)
        store.append(
            ResearchBriefEmittedEvent(
                event_type=EventType.RESEARCH_BRIEF_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("domain_researcher"),
                payload=ResearchBriefEmittedPayload(
                    brief_kind="domain",
                    domain_tag=domain_tag,
                    summary=domain_brief.summary,
                    artifact_id=domain_brief.artifact_id,
                    sources=[
                        ResearchBriefSourcePayload(
                            url=s.url,
                            license=s.license,
                            trust_tier=s.trust_tier,
                        )
                        for s in domain_brief.sources
                    ],
                ),
            ),
        )
        store.append(
            DomainCriticProposedEvent(
                event_type=EventType.DOMAIN_CRITIC_PROPOSED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("domain_researcher"),
                payload=DomainCriticProposedPayload(
                    critic_template=f"{domain_tag}_domain_critic",
                    allowed_domains=[domain_tag],
                    blocking_authority="ADVISORY",
                    evidence_refs=[f"artifact://{domain_brief.artifact_id}"],
                ),
            ),
        )
        _emit_critique_panel(
            store,
            registry,
            critique_router,
            run_id=run_id,
            stage_name="domain_researcher.critique",
            producer_key="domain_researcher",
        )

    if code_enabled:
        patterns = select_research_patterns(repo_path, requirements=requirements)
        primary = patterns[0] if patterns else {}
        code_source_url = str(primary.get("repo_url") or f"requirements://code/{domain_tag}")
        if live:
            from research.pattern_index import pattern_index_path

            idx = pattern_index_path(repo_path)
            if idx.is_file():
                code_source_url = f"pattern-index://{idx.name}"
        raw_summary = code_brief_summary(
            requirements,
            domain_tag=domain_tag,
            patterns=patterns,
        )
        code_brief = ResearchBrief(
            brief_kind="code",
            domain_tag=domain_tag,
            summary=raw_summary[:4000],
            artifact_id=str(uuid4()),
            sources=(
                ResearchBriefSource(
                    url=code_source_url,
                    license="MIT",
                    trust_tier="high",
                ),
            ),
        )
        persist_research_brief(repo_root, code_brief)
        store.append(
            ResearchBriefEmittedEvent(
                event_type=EventType.RESEARCH_BRIEF_EMITTED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("code_researcher"),
                payload=ResearchBriefEmittedPayload(
                    brief_kind="code",
                    domain_tag=domain_tag,
                    summary=code_brief.summary,
                    artifact_id=code_brief.artifact_id,
                    sources=[
                        ResearchBriefSourcePayload(
                            url=s.url,
                            license=s.license,
                            trust_tier=s.trust_tier,
                        )
                        for s in code_brief.sources
                    ],
                ),
            ),
        )
        pattern_id = new_pattern_id()
        seed = patterns[0] if patterns else {}
        pattern = append_pattern_index(
            repo_root,
            pattern_id=str(seed.get("pattern_id") or pattern_id),
            repo_url=str(seed.get("repo_url") or f"requirements://code/{domain_tag}"),
            paths=[str(p) for p in (seed.get("paths") or []) if str(p).strip()] or ["src/"],
            license_name=str(seed.get("license") or "MIT"),
            embedding_ref=str(seed.get("embedding_ref") or f"requirements:{domain_tag}"),
        )
        store.append(
            ResearchPatternIndexedEvent(
                event_type=EventType.RESEARCH_PATTERN_INDEXED,
                event_id=uuid4(),
                run_id=run_id,
                occurred_at=datetime.now(timezone.utc),
                actor_role=registry.resolve("code_researcher"),
                payload=ResearchPatternIndexedPayload(
                    pattern_id=pattern["pattern_id"],
                    repo_url=pattern["repo_url"],
                    paths=pattern["paths"],
                    license=pattern["license"],
                    embedding_ref=pattern["embedding_ref"],
                ),
            ),
        )
        append_enterprise_research_index(
            repo_root,
            run_id=run_id,
            pattern_id=pattern["pattern_id"],
            domain_tag=domain_tag,
        )
        write_catalog_candidate(
            repo_root,
            run_id=run_id,
            candidate_id=pattern["pattern_id"],
            bundle_hints={
                "repo_url": pattern["repo_url"],
                "license": pattern["license"],
                "domain_tag": domain_tag,
                "stack_id": primary_stack_id_from_requirements(requirements) or "",
            },
        )
        _emit_critique_panel(
            store,
            registry,
            critique_router,
            run_id=run_id,
            stage_name="code_researcher.critique",
            producer_key="code_researcher",
        )


def emit_research_stages_stub(
    store: EventStore,
    registry: RoleRegistry,
    critique_router: UniversalCritiqueRouter,
    *,
    run_id: UUID,
    repo_root: Any,
    requirements: dict[str, Any] | None,
    research_meta: dict[str, Any],
    live: bool = False,
) -> None:
    emit_research_stages(
        store,
        registry,
        critique_router,
        run_id=run_id,
        repo_root=repo_root,
        requirements=requirements,
        research_meta=research_meta,
        live=live,
    )
