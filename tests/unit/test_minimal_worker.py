from __future__ import annotations

from compute.minimal_worker import probe_minimal_worker_capabilities


def test_probe_minimal_worker_capabilities_flags() -> None:
    caps = probe_minimal_worker_capabilities()
    assert caps.get("mesh_worker") is True
    assert caps.get("minimal_worker") is True
    assert "hardware_tier" in caps
