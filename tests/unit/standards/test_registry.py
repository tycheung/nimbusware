from __future__ import annotations

from standards.registry import (
    load_bundle_manifest,
    load_facade_manifest,
    mart_catalog,
    profile_stream_ids,
    stream_ids,
)


def test_stream_ids_include_core_streams() -> None:
    ids = stream_ids()
    assert "architecture" in ids
    assert "complexity" in ids
    assert "lint" in ids


def test_nimbusware_core_profile_streams() -> None:
    streams = profile_stream_ids("nimbusware-core")
    assert streams == ["architecture", "complexity"]


def test_mart_catalog_has_bundles_and_facades() -> None:
    catalog = mart_catalog()
    assert "python-agent-hygiene" in catalog["bundles"]
    assert "python-fastapi" in catalog["facades"]
    assert "semgrep" in catalog["connectors"]


def test_load_python_fastapi_facade() -> None:
    manifest = load_facade_manifest("python-fastapi")
    assert manifest is not None
    assert "python-agent-hygiene" in manifest.get("bundles", [])


def test_load_python_agent_hygiene_bundle() -> None:
    manifest = load_bundle_manifest("python-agent-hygiene")
    assert manifest is not None
    checks = manifest.get("checks")
    assert isinstance(checks, list) and checks
