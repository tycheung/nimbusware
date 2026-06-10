from __future__ import annotations

from pathlib import Path
from typing import Any

from nimbusware_orchestrator.workflow_scan_critique import (
    ScanCritiqueBlock as NetworkResilienceCritiqueBlock,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    parse_scan_critique_workflow_block as _parse,
)
from nimbusware_orchestrator.workflow_scan_critique import (
    scan_critique_effective,
    scan_critique_llm_effective,
)


def parse_network_resilience_critique_workflow_block(
    repo_root: Path,
    workflow_profile: str | None,
    *,
    config_materializer: Any | None = None,
) -> NetworkResilienceCritiqueBlock:
    return _parse(
        repo_root,
        workflow_profile,
        "network_resilience_critique",
        config_materializer=config_materializer,
        extra_bool_defaults={"backend_only": True},
    )


def network_resilience_critique_effective(block: NetworkResilienceCritiqueBlock) -> bool:
    return scan_critique_effective(block, "NIMBUSWARE_NETWORK_RESILIENCE_CRITIQUE")


def network_resilience_critique_llm_branch_effective(
    block: NetworkResilienceCritiqueBlock,
) -> bool:
    return scan_critique_llm_effective(block, "NIMBUSWARE_NETWORK_RESILIENCE_CRITIQUE_LLM")


__all__ = (
    "NetworkResilienceCritiqueBlock",
    "parse_network_resilience_critique_workflow_block",
    "network_resilience_critique_effective",
    "network_resilience_critique_llm_branch_effective",
)
