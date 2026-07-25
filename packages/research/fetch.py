from __future__ import annotations


def fetch_url(url: str, *, client=None) -> dict:
    """Broker-first research fetch; no local network fallback after peel."""
    _ = client
    from research.broker_route import raise_research_peel_miss
    from research.research_bridge import try_broker_research_fetch

    hit = try_broker_research_fetch(url)
    if hit is not None:
        return {"backend": "broker", **(hit if isinstance(hit, dict) else {"result": hit})}
    raise_research_peel_miss("research_fetch")  # sak494-e / sak496-d: broker_miss: research_fetch
    raise RuntimeError(
        "research local fetch removed (sak416-h); set NIMBUSWARE_BROKER_RESEARCH=1|2"
    )
