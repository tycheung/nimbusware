"""Workflow-driven security scan metadata flag."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from nimbusware_orchestrator.pipeline import make_dev_orchestrator
from nimbusware_orchestrator.workflow_security import security_scan_metadata_on_verify_enabled
from nimbusware_env import find_repo_root


def test_security_scan_env_forces_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", "1")
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert security_scan_metadata_on_verify_enabled(root, "default") is True


def test_security_scan_env_kill_switch_overrides_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", "0")
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert security_scan_metadata_on_verify_enabled(root, "security_scan_metadata_on") is False


def test_security_scan_workflow_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", raising=False)
    (tmp_path / "configs" / "workflows").mkdir(parents=True)
    (tmp_path / "configs" / "workflows" / "customsec.yaml").write_text(
        "version: 1\nsecurity_scan_metadata_on_verify: true\n",
        encoding="utf-8",
    )
    assert security_scan_metadata_on_verify_enabled(tmp_path, "customsec") is True


def test_repo_profile_security_scan_metadata_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", raising=False)
    root = find_repo_root(start=Path(__file__).resolve().parents[1])
    assert security_scan_metadata_on_verify_enabled(root, "security_scan_metadata_on") is True


@patch(
    "nimbusware_orchestrator.pipeline.run_security_scan",
    return_value=(2, "scanlog\nline2\n", 1, 2, 0, 0, 0, 0),
)
@patch("nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(1, "verifier fail"))
def test_verifier_failure_attaches_security_metadata_when_workflow_on(
    _mock_vf: object,
    _mock_scan: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", raising=False)
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("security_scan_metadata_on")
    orch.execute_writer_verifier_pass(rid)
    evs = mem.list_run_events(str(rid))
    findings = [e for e in evs if e.get("event_type") == "finding.created"]
    assert findings
    md = findings[-1].get("metadata") or {}
    assert md.get("security_scan_exit") == 2
    assert md.get("security_scan_ruff_exit") == 1
    assert md.get("security_scan_bandit_exit") == 2
    assert "scanlog" in md.get("security_scan_snippet", "")


@patch(
    "nimbusware_orchestrator.pipeline.run_security_scan",
    return_value=(0, "should_not_attach", 0, 0, 0, 0, 0, 0),
)
@patch("nimbusware_orchestrator.pipeline.run_writer_verifier_bundle", return_value=(1, "verifier fail"))
def test_env_kill_skips_security_scan_metadata(
    _mock_vf: object,
    _mock_scan: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", "false")
    orch, mem = make_dev_orchestrator()
    rid = orch.create_run("security_scan_metadata_on")
    orch.execute_writer_verifier_pass(rid)
    evs = mem.list_run_events(str(rid))
    findings = [e for e in evs if e.get("event_type") == "finding.created"]
    assert findings
    assert not (findings[-1].get("metadata") or {})


def _write_security_profile(tmp_path: Path, name: str, enabled: bool) -> None:
    """Drop a minimal workflow profile under ``tmp_path/configs/workflows/{name}.yaml``.

    Shared by the three follow-on 62 string-arm contract tests below so each test
    can write both an ``off`` and an ``on`` profile uniformly without repeating the
    boilerplate ``mkdir`` + ``write_text`` dance. ``parents=True, exist_ok=True``
    so subsequent calls within the same test do not fail.
    """
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    val = "true" if enabled else "false"
    (wf_dir / f"{name}.yaml").write_text(
        f"version: 1\nsecurity_scan_metadata_on_verify: {val}\n",
        encoding="utf-8",
    )


def test_security_scan_metadata_env_force_on_string_arm_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #18 env force-on tuple ``.strip().lower() in ("1", "true", "yes")``.

    :func:`security_scan_metadata_on_verify_enabled` consults
    ``NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA`` *before* the YAML coercion ladder.
    Existing tests sample only `"1"`; this test exhaustively pins the
    case-folded + whitespace-trimmed variants of the force-on tuple. The
    workflow profile is ``off.yaml`` (``security_scan_metadata_on_verify:
    false``) so any ``True`` result comes only from the env force-on branch.

    Mirrors follow-on 51's tuple-asymmetry coverage for
    :func:`env_over_yaml` and follow-on 61 Parts A + B's case-folding +
    whitespace coverage for the YAML coercion ladder. Per-case
    ``force_on raw=<raw>`` message identifies the failing env scalar.
    """
    _write_security_profile(tmp_path, "off", enabled=False)
    cases: list[tuple[str, str]] = [
        ("canon_one", "1"),
        ("canon_true", "true"),
        ("canon_yes", "yes"),
        ("upper_true", "TRUE"),
        ("title_true", "True"),
        ("upper_yes", "YES"),
        ("title_yes", "Yes"),
        ("mixed_true", "trUE"),
        ("mixed_yes", "yEs"),
        ("ws_one_pad", "  1  "),
        ("ws_true_pad", " true "),
        ("ws_tab_yes_lf", "\tyes\n"),
        ("ws_upper_true_pad", "  TRUE  "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", raw)
        assert security_scan_metadata_on_verify_enabled(tmp_path, "off") is True, (
            f"force_on raw={raw!r}"
        )


def test_security_scan_metadata_env_kill_switch_string_arm_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #18 env kill-switch tuple ``.strip().lower() in ("0", "false", "no")``.

    Mirror of Part A for the falsy tuple. The workflow profile is ``on.yaml``
    (``security_scan_metadata_on_verify: true``) so any ``False`` result
    comes only from the env kill-switch branch. Existing coverage samples
    only `"0"` and `"false"`; this test pins the full case-folded +
    whitespace-trimmed variants. Per-case ``kill_switch raw=<raw>`` message
    identifies the failing env scalar.
    """
    _write_security_profile(tmp_path, "on", enabled=True)
    cases: list[tuple[str, str]] = [
        ("canon_zero", "0"),
        ("canon_false", "false"),
        ("canon_no", "no"),
        ("upper_false", "FALSE"),
        ("title_false", "False"),
        ("upper_no", "NO"),
        ("title_no", "No"),
        ("mixed_false", "fAlSe"),
        ("mixed_no", "nO"),
        ("ws_zero_pad", "  0  "),
        ("ws_false_pad", " false "),
        ("ws_tab_no_lf", "\tno\n"),
        ("ws_upper_false_pad", "  FALSE  "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", raw)
        assert security_scan_metadata_on_verify_enabled(tmp_path, "on") is False, (
            f"kill_switch raw={raw!r}"
        )


def test_security_scan_metadata_env_fallthrough_to_yaml_string_arm_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #18 exclusive-tuple-membership: env values not in either tuple fall through to YAML.

    Critical asymmetry pinned: the **YAML** coercion ladder accepts
    ``"on"`` / ``"off"`` in its truthy tuple, but the **env** layer's tuples
    are ``("1", "true", "yes")`` and ``("0", "false", "no")`` —
    they **exclude** ``"on"`` / ``"off"``. So
    ``NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA=on`` falls past both tuples to
    YAML rather than forcing-on. This is the parallel of follow-on 51's
    :func:`env_over_yaml` asymmetry slice for
    :mod:`workflow_universal_critique`.

    Each case asserts against **both** workflow profiles (``off`` → ``False``,
    ``on`` → ``True``) so a single per-case message identifies the offending
    env scalar and which workflow side regressed. Covers four fallthrough
    failure modes:

    1. **Asymmetric YAML tokens** (``"on"`` / ``"off"`` and case-folded
       ``"ON"`` / ``"  OFF  "``) — would be truthy / falsy under YAML
       coercion but are not in the env tuples.
    2. **Stripped-to-empty inputs** (``""`` / ``"   "``) — after
       ``.strip().lower()`` produce ``""``, which is not in either tuple.
    3. **Unknown tokens** (``"maybe"`` / ``"true!"``) — straightforward
       fallthrough; ``.strip()`` cannot rescue the trailing ``!``.
    4. **Interior whitespace** (``" ye s "``) — ``.strip()`` only trims
       edges, so the interior space leaves ``"ye s"`` which is not in any
       tuple.

    A future "unify the env tuple with the YAML tuple" refactor (adding
    ``"on"`` / ``"off"`` to the env tuples) would silently flip the
    semantics of ``NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA=on`` from "follow
    YAML" to "force on" — this test fails loudly on exactly that change.
    """
    _write_security_profile(tmp_path, "off", enabled=False)
    _write_security_profile(tmp_path, "on", enabled=True)
    cases: list[tuple[str, str]] = [
        ("fall_on", "on"),
        ("fall_off", "off"),
        ("fall_upper_on", "ON"),
        ("fall_padded_off", "  OFF  "),
        ("fall_empty", ""),
        ("fall_whitespace", "   "),
        ("fall_maybe", "maybe"),
        ("fall_near_miss", "true!"),
        ("fall_interior_ws", " ye s "),
    ]
    for _name, raw in cases:
        monkeypatch.setenv("NIMBUSWARE_ATTACH_SECURITY_SCAN_METADATA", raw)
        assert security_scan_metadata_on_verify_enabled(tmp_path, "off") is False, (
            f"fall_through workflow=off raw={raw!r}"
        )
        assert security_scan_metadata_on_verify_enabled(tmp_path, "on") is True, (
            f"fall_through workflow=on raw={raw!r}"
        )
