"""parse and merge ``universal_critique`` workflow knobs."""

from __future__ import annotations

from pathlib import Path

import pytest

from nimbusware_orchestrator.workflow_universal_critique import (
    UniversalCritiqueWorkflowBlock,
    effective_universal_critique,
    parse_universal_critique_workflow_block,
)
from nimbusware_env import find_repo_root
from nimbusware_env.env_flags import env_over_yaml

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_parse_universal_critique_missing_profile_defaults() -> None:
    block = parse_universal_critique_workflow_block(ROOT, None)
    assert block.impl_stub is False
    assert block.tw_enabled is False
    assert block.pll_enabled is False
    assert block.fw_enabled is False
    assert block.mi_enabled is False


def test_parse_universal_critique_emit_finding_profile_loads() -> None:
    block = parse_universal_critique_workflow_block(
        ROOT,
        "universal_critique_emit_finding_on_gate_fail",
    )
    assert block.impl_emit_finding_on_gate_fail is True
    assert block.tw_emit_finding_on_gate_fail is True
    assert block.pll_emit_finding_on_gate_fail is True
    assert block.fw_emit_finding_on_gate_fail is True
    assert block.mi_emit_finding_on_gate_fail is True


def test_parse_universal_critique_hard_block_profile_loads() -> None:
    block = parse_universal_critique_workflow_block(
        ROOT,
        "universal_critique_hard_block_on",
    )
    assert block.impl_stub is True
    assert block.impl_hard_block_on_gate_fail is True


def test_parse_universal_critique_hard_block_chain_profile_loads() -> None:
    block = parse_universal_critique_workflow_block(
        ROOT,
        "universal_critique_hard_block_chain_on",
    )
    assert block.impl_hard_block_on_gate_fail is True
    assert block.tw_enabled is True and block.tw_stub is True
    assert block.pll_enabled is True and block.pll_stub is True
    assert block.fw_enabled is True and block.fw_stub is True
    assert block.mi_enabled is True and block.mi_stub is True


def test_parse_universal_critique_tw_hard_block_chain_profile_loads() -> None:
    block = parse_universal_critique_workflow_block(
        ROOT,
        "universal_critique_tw_hard_block_chain_on",
    )
    assert block.impl_hard_block_on_gate_fail is False
    assert block.tw_hard_block_on_gate_fail is True
    assert block.pll_enabled is True


def test_parse_universal_critique_malformed_block_defaults(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "broken.yaml").write_text(
        (
            "version: 1\n"
            "universal_critique:\n"
            "  implementation: [1, 2]\n"
            "  test_writer: bad\n"
            "  planner:\n"
            "    enabled: 2\n"
            "    stub: {}\n"
        ),
        encoding="utf-8",
    )
    block = parse_universal_critique_workflow_block(repo, "broken")
    assert block.impl_llm is False
    assert block.impl_stub is False
    assert block.impl_emit_finding_on_gate_fail is False
    assert block.tw_enabled is False
    assert block.tw_stub is False
    assert block.pll_enabled is False
    assert block.pll_stub is False


def test_effective_universal_critique_blank_env_uses_yaml() -> None:
    env = {"NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE": " "}
    # Local import avoids global env bleed in other tests.
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, env, clear=False):
        eff = effective_universal_critique(ROOT, "universal_critique_stub_on")
    assert eff.tw_enabled is True
    assert eff.tw_stub is True
    assert eff.impl_stub is True
    assert eff.fw_enabled is True
    assert eff.mi_enabled is True


def test_parse_universal_critique_missing_workflow_file_returns_defaults(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    (repo / "configs" / "workflows").mkdir(parents=True)
    block = parse_universal_critique_workflow_block(repo, "profile_file_missing_here")
    assert block == UniversalCritiqueWorkflowBlock()


def test_parse_universal_critique_root_scalar_or_list_yields_defaults(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "scalar_root.yaml").write_text(
        "version: 1\nuniversal_critique: true\n",
        encoding="utf-8",
    )
    (wf_dir / "list_root.yaml").write_text(
        "version: 1\nuniversal_critique: []\n",
        encoding="utf-8",
    )
    assert parse_universal_critique_workflow_block(repo, "scalar_root") == (
        UniversalCritiqueWorkflowBlock()
    )
    assert parse_universal_critique_workflow_block(repo, "list_root") == (
        UniversalCritiqueWorkflowBlock()
    )


def test_env_over_yaml_empty_or_whitespace_uses_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "NIMBUSWARE_TEST_ENV_OVER_YAML_EMPTY"
    monkeypatch.delenv(key, raising=False)
    assert env_over_yaml(key, True) is True
    monkeypatch.setenv(key, "")
    assert env_over_yaml(key, False) is False
    monkeypatch.setenv(key, "   ")
    assert env_over_yaml(key, True) is True


def test_env_over_yaml_truthy_tokens_override_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "NIMBUSWARE_TEST_ENV_OVER_YAML_TRUTHY"
    monkeypatch.setenv(key, "yes")
    assert env_over_yaml(key, False) is True
    monkeypatch.setenv(key, "TRUE")
    assert env_over_yaml(key, False) is True
    monkeypatch.setenv(key, "1")
    assert env_over_yaml(key, False) is True


def test_env_over_yaml_non_truthy_token_overrides_yaml_to_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = "NIMBUSWARE_TEST_ENV_OVER_YAML_FALSY"
    for val in ("no", "0", "false", "off", "junk"):
        monkeypatch.setenv(key, val)
        assert env_over_yaml(key, True) is False, val


def test_effective_universal_critique_impl_emit_finding_env_overrides_yaml(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NIMBUSWARE_IMPLEMENTATION_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL", "yes")
    eff = effective_universal_critique(ROOT, "universal_critique_stub_on")
    assert eff.impl_emit_finding_on_gate_fail is True


def test_effective_universal_critique_non_truthy_env_disables_yaml() -> None:
    import os
    from unittest.mock import patch

    with patch.dict(
        os.environ,
        {
            "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE": "0",
            "NIMBUSWARE_STUB_TEST_WRITER_CRITICS": "no",
        },
        clear=False,
    ):
        eff = effective_universal_critique(ROOT, "universal_critique_stub_on")
    assert eff.tw_enabled is False
    assert eff.tw_stub is False
    assert eff.impl_stub is True


def test_env_over_yaml_on_token_does_not_enable_knob(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #16 ``env_over_yaml`` / YAML ``"on"`` asymmetry (env-layer half).

    The YAML coercion accepts ``"on"`` as truthy (see ``_coerce_yaml_bool``: ``"1" / "true" /
    "yes" / "on"``) but :func:`env_over_yaml` deliberately accepts only ``"1" / "true" / "yes"``
    so a bare ``NIMBUSWARE_*_LLM=on`` falls into the non-truthy override branch and *disables* the
    knob even when YAML had it on. This mirrors the existing ``"off"`` coverage in
    :func:`test_env_over_yaml_non_truthy_token_overrides_yaml_to_false` and locks the contract
    so any future env-layer unification (e.g. extending the tuple to include ``"on"``) must
    update this pin on purpose. Whitespace and case parity are checked alongside to match how
    operators actually export env vars.
    """
    key = "NIMBUSWARE_TEST_ENV_OVER_YAML_ON"
    for val in ("on", "ON", " on ", "  On  "):
        monkeypatch.setenv(key, val)
        assert env_over_yaml(key, False) is False, val
        assert env_over_yaml(key, True) is False, val


def test_parse_universal_critique_yaml_string_on_enables_knob(
    tmp_path: Path,
) -> None:
    """Pin §14 #16 ``env_over_yaml`` / YAML ``"on"`` asymmetry (YAML-layer half).

    Workflow YAML ``llm: "on"`` and ``enabled: "on"`` must be coerced to ``True`` via
    ``_coerce_yaml_bool``'s ``("1", "true", "yes", "on")`` truthy tuple. Pairs with the
    env-layer pin above so a single future change to either tuple breaks exactly one test
    (the one whose contract was actually altered) rather than silently flipping behavior.
    Mirrors the tmp_path pattern from
    :func:`test_parse_universal_critique_root_scalar_or_list_yields_defaults`.
    """
    repo = tmp_path / "repo"
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "yaml_on_token.yaml").write_text(
        "version: 1\n"
        "universal_critique:\n"
        "  implementation:\n"
        '    llm: "on"\n'
        "  test_writer:\n"
        '    enabled: "on"\n',
        encoding="utf-8",
    )
    block = parse_universal_critique_workflow_block(repo, "yaml_on_token")
    assert block.impl_llm is True
    assert block.tw_enabled is True


def _write_universal_critique_profile(repo: Path, name: str, body: str) -> None:
    """Write ``configs/workflows/{name}.yaml`` under ``repo`` with the given body.

    Uses ``exist_ok=True`` so a single test can drop many per-case profiles into the
    same tmp directory; mirrors ``_write_integrator_gate_profile`` (follow-on 56) and
    ``_write_agent_evaluator_profile`` (follow-on 55).
    """
    wf_dir = repo / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_coerce_yaml_bool_numeric_strict_one_via_parse(tmp_path: Path) -> None:
    """Pin §14 #16 ``_coerce_yaml_bool`` strict ``raw == 1`` numeric semantics.

    Unlike sibling parsers (``parse_self_refinement_workflow_block`` /
    ``parse_agent_evaluator_workflow_block`` pinned in follow-ons 53 / 55, plus
    ``_coerce_security_scan_metadata_enabled_value`` pinned in follow-on 54), this
    coercion ladder deliberately rejects any non-``1`` numeric value: ``1`` and
    ``1.0`` enable a knob, but ``0`` / ``2`` / ``1.5`` / ``-1`` all disable it
    (``raw == 1`` strict equality). A future "unify the coercion across all workflow
    parsers" refactor would flip ``llm: 2`` from disabled → enabled with no test
    failure today. Exercised via ``parse_universal_critique_workflow_block`` since
    ``_coerce_yaml_bool`` is module-private.
    """
    repo = tmp_path / "repo"
    cases: list[tuple[str, str, bool]] = [
        ("num_int_one", "1", True),
        ("num_float_one", "1.0", True),
        ("num_int_zero", "0", False),
        ("num_int_two", "2", False),
        ("num_float_one_half", "1.5", False),
        ("num_neg_one", "-1", False),
    ]
    for name, raw, expected in cases:
        _write_universal_critique_profile(
            repo,
            name,
            f"version: 1\nuniversal_critique:\n  implementation:\n    llm: {raw}\n",
        )
        block = parse_universal_critique_workflow_block(repo, name)
        assert block.impl_llm is expected, name


def test_coerce_yaml_bool_truthy_case_insensitive_strings_via_parse(
    tmp_path: Path,
) -> None:
    """Pin §14 #16 ``_coerce_yaml_bool`` ``.lower()`` case-folding for the string arm.

    The coercer's string branch lowercases before tuple membership
    (``raw.strip().lower() in ("1", "true", "yes", "on")``). Follow-on 51 already
    pinned the lowercase ``"on"`` token via
    :func:`test_parse_universal_critique_yaml_string_on_enables_knob`, but the
    full case-insensitivity contract for the rest of the truthy tuple was only
    spot-exercised at the *env* layer in ``test_env_over_yaml_truthy_tokens_override_yaml``
    (which uses a different ladder — ``env_over_yaml`` excludes ``"on"``, pinned
    in follow-on 51). This test locks the *YAML* layer's ``.lower()`` call for
    every truthy token: any refactor that drops case-folding (e.g. swapping to
    strict equality on the original token, or restricting to ``str.casefold``
    on locale-sensitive input) flips at least one case here with a per-case
    ``case_id`` message naming the offending scalar.

    All YAML scalars are **quoted** so PyYAML's YAML 1.1 bool resolver does not
    eagerly convert unquoted ``TRUE`` / ``YES`` / ``On`` to Python ``True`` —
    that would hit the ``isinstance(raw, bool)`` arm and bypass the string
    ladder entirely.
    """
    repo = tmp_path / "repo"
    cases: list[tuple[str, str]] = [
        ("upper_true", '"TRUE"'),
        ("title_true", '"True"'),
        ("upper_yes", '"YES"'),
        ("title_yes", '"Yes"'),
        ("upper_on", '"ON"'),
        ("title_on", '"On"'),
        ("mixed_on", '"oN"'),
        ("mixed_yes", '"yEs"'),
    ]
    for name, raw in cases:
        _write_universal_critique_profile(
            repo,
            name,
            f"version: 1\nuniversal_critique:\n  implementation:\n    llm: {raw}\n",
        )
        block = parse_universal_critique_workflow_block(repo, name)
        assert block.impl_llm is True, f"impl.llm={raw}"


def test_coerce_yaml_bool_truthy_whitespace_trimmed_strings_via_parse(
    tmp_path: Path,
) -> None:
    """Pin §14 #16 ``_coerce_yaml_bool`` ``.strip()`` whitespace trimming for the string arm.

    The coercer applies ``.strip()`` before lowercasing and tuple membership.
    Today the only direct coverage of edge-whitespace is the lowercase ``"on"``
    pin from follow-on 51 (no leading / trailing whitespace) and indirect env
    coverage via ``test_env_over_yaml_empty_or_whitespace_uses_yaml``. This test
    locks the YAML-layer ``.strip()`` call for **every** truthy token plus
    combined case + whitespace and non-ASCII whitespace (tab / newline) edges.

    YAML double-quoted scalars preserve embedded ``\\t`` / ``\\n`` escape
    sequences which PyYAML decodes to literal tab / line-feed characters in the
    Python string — so the values that hit ``_coerce_yaml_bool`` actually
    contain whitespace beyond plain ASCII space. ``str.strip()`` strips all
    Unicode whitespace by default, including these. Any refactor that narrows
    the strip class (e.g. ``raw.strip(" ")``) flips the ``ws_true`` /
    ``ws_tab_only`` / ``ws_trailing`` cases here with a per-case ``case_id``.
    """
    repo = tmp_path / "repo"
    cases: list[tuple[str, str]] = [
        ("ws_one", '"  1  "'),
        ("ws_yes", '" yes "'),
        ("ws_true", '"\\ttrue\\n"'),
        ("ws_on", '"  on  "'),
        ("ws_case_combo", '"  TRUE  "'),
        ("ws_tab_only", '"\\tyes"'),
        ("ws_trailing", '"yes\\t"'),
    ]
    for name, raw in cases:
        _write_universal_critique_profile(
            repo,
            name,
            f"version: 1\nuniversal_critique:\n  implementation:\n    llm: {raw}\n",
        )
        block = parse_universal_critique_workflow_block(repo, name)
        assert block.impl_llm is True, f"impl.llm={raw}"


def test_coerce_yaml_bool_falsy_and_unknown_strings_via_parse(
    tmp_path: Path,
) -> None:
    """Pin §14 #16 ``_coerce_yaml_bool`` exclusive-membership negative branch.

    The coercer's string arm returns ``False`` for anything that, after
    ``.strip().lower()``, is not in ``("1", "true", "yes", "on")``. This test
    locks three failure modes that a future refactor could quietly flip:

    1. **Case-folded falsy tokens** (``"FALSE"`` / ``"  OFF  "`` / ``"NO"``)
       reach the membership check as ``"false"`` / ``"off"`` / ``"no"`` and
       fall through. A refactor that adds ``"false"`` / ``"off"`` / ``"no"``
       as *explicit* falsy guards (rather than implicit fallthrough) would not
       change behavior — but a refactor that adds ``"off"`` to the truthy tuple
       (mirroring env vs YAML asymmetry from follow-on 51 in the *opposite*
       direction) would flip ``upper_off_padded`` here.

    2. **Near-miss truthy tokens** (``"true!"`` / ``" ye s "``) demonstrate the
       contract that ``.strip()`` only trims *edges* — interior whitespace and
       trailing punctuation are kept and break tuple membership. A refactor
       to ``raw.replace(...)``-based normalization would flip these.

    3. **Stripped-to-empty inputs** (``""`` / ``"   "``) reach the membership
       check as ``""``, which is not in the truthy tuple. Distinct from the
       ``cur is not None`` short-circuit pinned in
       :func:`test_leaf_bool_null_value_and_missing_key_via_parse` — empty
       string is *not* ``None`` and *does* enter the coercer's string arm,
       falling through to ``False`` from the tuple check itself rather than
       the ``return default`` floor.

    All YAML scalars are quoted to keep PyYAML's bool resolver from eagerly
    converting ``FALSE`` / ``No`` to Python ``False`` and bypassing the string
    arm.
    """
    repo = tmp_path / "repo"
    cases: list[tuple[str, str]] = [
        ("upper_false", '"FALSE"'),
        ("title_false", '"False"'),
        ("upper_off_padded", '"  OFF  "'),
        ("upper_no", '"NO"'),
        ("mixed_no", '"nO"'),
        ("unknown_maybe", '"maybe"'),
        ("trailing_bang", '"true!"'),
        ("interior_ws_yes", '" ye s "'),
        ("empty_quoted", '""'),
        ("only_whitespace", '"   "'),
    ]
    for name, raw in cases:
        _write_universal_critique_profile(
            repo,
            name,
            f"version: 1\nuniversal_critique:\n  implementation:\n    llm: {raw}\n",
        )
        block = parse_universal_critique_workflow_block(repo, name)
        assert block.impl_llm is False, f"impl.llm={raw}"


# Shared wiring map for follow-on 58 multi-part wiring-contract tests below.
# One row per critique knob: (stage_section, leaf_key, env_key, dataclass_attr).
# Mirrors the 17-arg constructors in ``parse_universal_critique_workflow_block`` and
# ``effective_universal_critique`` so any reorder / copy-paste error in either body
# fails Part A / B / C with a per-knob assertion message identifying the regression.
_WIRING_MAP: list[tuple[str, str, str, str]] = [
    ("implementation", "llm", "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_LLM", "impl_llm"),
    ("implementation", "stub", "NIMBUSWARE_STUB_IMPLEMENTATION_CRITICS", "impl_stub"),
    (
        "implementation",
        "stage_failed_on_gate_fail",
        "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        "impl_stage_failed_on_gate_fail",
    ),
    (
        "implementation",
        "emit_finding_on_gate_fail",
        "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        "impl_emit_finding_on_gate_fail",
    ),
    (
        "implementation",
        "hard_block_on_gate_fail",
        "NIMBUSWARE_IMPLEMENTATION_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        "impl_hard_block_on_gate_fail",
    ),
    ("test_writer", "enabled", "NIMBUSWARE_ENABLE_TEST_WRITER_CRITIQUE", "tw_enabled"),
    ("test_writer", "llm", "NIMBUSWARE_TEST_WRITER_CRITIQUE_LLM", "tw_llm"),
    ("test_writer", "stub", "NIMBUSWARE_STUB_TEST_WRITER_CRITICS", "tw_stub"),
    (
        "test_writer",
        "stage_failed_on_gate_fail",
        "NIMBUSWARE_TEST_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        "tw_stage_failed_on_gate_fail",
    ),
    (
        "test_writer",
        "emit_finding_on_gate_fail",
        "NIMBUSWARE_TEST_WRITER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        "tw_emit_finding_on_gate_fail",
    ),
    (
        "test_writer",
        "hard_block_on_gate_fail",
        "NIMBUSWARE_TEST_WRITER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        "tw_hard_block_on_gate_fail",
    ),
    ("planner", "enabled", "NIMBUSWARE_ENABLE_PLANNER_CRITIQUE", "pll_enabled"),
    ("planner", "llm", "NIMBUSWARE_PLANNER_CRITIQUE_LLM", "pll_llm"),
    ("planner", "stub", "NIMBUSWARE_STUB_PLANNER_CRITICS", "pll_stub"),
    (
        "planner",
        "stage_failed_on_gate_fail",
        "NIMBUSWARE_PLANNER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        "pll_stage_failed_on_gate_fail",
    ),
    (
        "planner",
        "emit_finding_on_gate_fail",
        "NIMBUSWARE_PLANNER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        "pll_emit_finding_on_gate_fail",
    ),
    (
        "planner",
        "hard_block_on_gate_fail",
        "NIMBUSWARE_PLANNER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        "pll_hard_block_on_gate_fail",
    ),
    ("frontend_writer", "enabled", "NIMBUSWARE_ENABLE_FRONTEND_WRITER_CRITIQUE", "fw_enabled"),
    ("frontend_writer", "llm", "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_LLM", "fw_llm"),
    ("frontend_writer", "stub", "NIMBUSWARE_STUB_FRONTEND_WRITER_CRITICS", "fw_stub"),
    (
        "frontend_writer",
        "stage_failed_on_gate_fail",
        "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        "fw_stage_failed_on_gate_fail",
    ),
    (
        "frontend_writer",
        "emit_finding_on_gate_fail",
        "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        "fw_emit_finding_on_gate_fail",
    ),
    (
        "frontend_writer",
        "hard_block_on_gate_fail",
        "NIMBUSWARE_FRONTEND_WRITER_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        "fw_hard_block_on_gate_fail",
    ),
    ("module_integrator", "enabled", "NIMBUSWARE_ENABLE_MODULE_INTEGRATOR_CRITIQUE", "mi_enabled"),
    ("module_integrator", "llm", "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_LLM", "mi_llm"),
    ("module_integrator", "stub", "NIMBUSWARE_STUB_MODULE_INTEGRATOR_CRITICS", "mi_stub"),
    (
        "module_integrator",
        "stage_failed_on_gate_fail",
        "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_STAGE_FAILED_ON_GATE_FAIL",
        "mi_stage_failed_on_gate_fail",
    ),
    (
        "module_integrator",
        "emit_finding_on_gate_fail",
        "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_EMIT_FINDING_ON_GATE_FAIL",
        "mi_emit_finding_on_gate_fail",
    ),
    (
        "module_integrator",
        "hard_block_on_gate_fail",
        "NIMBUSWARE_MODULE_INTEGRATOR_CRITIQUE_HARD_BLOCK_ON_GATE_FAIL",
        "mi_hard_block_on_gate_fail",
    ),
]


def _one_knob_on_yaml(stage: str, leaf: str) -> str:
    """Workflow YAML body with exactly one ``universal_critique`` knob set true.

    All sibling knobs are absent (and therefore evaluated as ``False`` via
    ``_leaf_bool``'s missing-key fallback), so the resulting
    :class:`UniversalCritiqueWorkflowBlock` has the target field True and every
    other field False. Pairs with ``_WIRING_MAP`` for Parts A / C.
    """
    return f"version: 1\nuniversal_critique:\n  {stage}:\n    {leaf}: true\n"


def _clear_all_wiring_envs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset every env var referenced by ``_WIRING_MAP`` (defensive isolation).

    Outer environment may export a subset of ``NIMBUSWARE_*_CRITIQUE_*`` for local
    runs; Parts B / C need a known-empty starting state before flipping one
    target env to "1" / "0" so the unset siblings cleanly fall through to YAML.
    """
    for _stage, _leaf, env_key, _attr in _WIRING_MAP:
        monkeypatch.delenv(env_key, raising=False)


def test_universal_critique_yaml_field_wiring_contract(tmp_path: Path) -> None:
    """Pin §14 #16 YAML leaf-path → :class:`UniversalCritiqueWorkflowBlock` field wiring.

    For every entry in ``_WIRING_MAP`` (17 critique knobs total) write a workflow
    profile with **only that knob** set ``true`` and verify the parser sets exactly
    that dataclass field to ``True`` while every other field remains ``False``. A
    copy-paste error in the 17-arg ``return UniversalCritiqueWorkflowBlock(...)``
    constructor (e.g. ``impl_llm=_leaf_bool(impl_d, "stub")``) would surface as a
    targeted assertion failure naming the affected knob via the per-iteration
    ``case_id`` message rather than a single opaque ``AssertionError``.
    """
    repo = tmp_path / "repo"
    all_attrs = [row[3] for row in _WIRING_MAP]
    for stage, leaf, _env_key, attr in _WIRING_MAP:
        profile = f"yaml_{attr}"
        _write_universal_critique_profile(repo, profile, _one_knob_on_yaml(stage, leaf))
        block = parse_universal_critique_workflow_block(repo, profile)
        case_id = f"{stage}.{leaf} -> {attr}"
        assert getattr(block, attr) is True, case_id
        for other in all_attrs:
            if other == attr:
                continue
            assert getattr(block, other) is False, f"{case_id} leaked into {other}"


def test_universal_critique_env_truthy_overrides_yaml_wiring_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #16 env truthy → :class:`EffectiveUniversalCritique` field wiring.

    For every entry in ``_WIRING_MAP``, set exactly that knob's env var to ``"1"``
    (with all 16 sibling envs cleared) against an **all-false** workflow profile
    (no ``universal_critique`` block at all), and verify
    :func:`effective_universal_critique` sets exactly that field to ``True`` while
    every other field stays ``False``. Catches both the "env override propagates"
    failure mode and the "env leaks into a sibling field" failure mode that a
    copy-paste error in ``effective_universal_critique``'s 17 ``env_over_yaml(...)``
    calls would introduce.
    """
    repo = tmp_path / "repo"
    _write_universal_critique_profile(repo, "all_false", "version: 1\n")
    all_attrs = [row[3] for row in _WIRING_MAP]
    for _stage, _leaf, env_key, attr in _WIRING_MAP:
        _clear_all_wiring_envs(monkeypatch)
        monkeypatch.setenv(env_key, "1")
        eff = effective_universal_critique(repo, "all_false")
        case_id = f"{env_key}=1 -> {attr}"
        assert getattr(eff, attr) is True, case_id
        for other in all_attrs:
            if other == attr:
                continue
            assert getattr(eff, other) is False, f"{case_id} leaked into {other}"


def test_universal_critique_env_non_truthy_disables_yaml_wiring_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin §14 #16 env non-truthy disables YAML for every wired knob.

    For every entry in ``_WIRING_MAP`` write a one-knob-on profile (the matching
    YAML field is ``true``) and verify two things in sequence:

    1. **Sanity:** with every wiring env cleared, the YAML alone enables the
       target field through :func:`effective_universal_critique`.
    2. **Override:** setting *only that knob's* env var to ``"0"`` (non-truthy)
       disables the field even though YAML still has it ``true``.

    Together with Part B this proves the env arm wins in **both** directions for
    every knob — a refactor that mis-wires ``env_over_yaml(env_key, wf.x)`` to
    consult the wrong ``wf`` attribute breaks here via the per-knob ``case_id``
    assertion message.
    """
    repo = tmp_path / "repo"
    for stage, leaf, env_key, attr in _WIRING_MAP:
        profile = f"env_disable_{attr}"
        _write_universal_critique_profile(repo, profile, _one_knob_on_yaml(stage, leaf))
        _clear_all_wiring_envs(monkeypatch)
        sanity = effective_universal_critique(repo, profile)
        assert getattr(sanity, attr) is True, f"YAML-only sanity for {env_key} -> {attr}"
        monkeypatch.setenv(env_key, "0")
        eff = effective_universal_critique(repo, profile)
        case_id = f"{env_key}=0 + YAML {stage}.{leaf}=true -> {attr}"
        assert getattr(eff, attr) is False, case_id


def test_leaf_bool_null_value_and_missing_key_via_parse(tmp_path: Path) -> None:
    """Pin §14 #16 ``_leaf_bool`` fallback arms + ``_coerce_yaml_bool`` unknown-type.

    ``_leaf_bool`` returns the default (False) in three distinct ways at a leaf
    knob:

    1. ``llm: null`` (key present, value ``None``) short-circuits at the
       ``cur is not None`` guard *before* reaching ``_coerce_yaml_bool``.
    2. Key absent (``implementation: {}``) makes ``block.get("llm")`` return
       ``None`` and hits the same guard.
    3. ``llm: []`` / ``llm: {nested: 1}`` (unknown leaf type) flows through
       ``_coerce_yaml_bool`` past every ``isinstance`` arm to ``return default``.

    Locks the contract so a refactor that wants to accept list / dict shortcuts at
    leaf knobs (or change the ``None``-short-circuit to call into the coercer)
    must update this test on purpose. Distinct from the structural-malformation
    coverage in ``test_parse_universal_critique_malformed_block_defaults`` (which
    pins the *stage*-level non-dict arms, not the leaf-level fallbacks).
    """
    repo = tmp_path / "repo"
    cases: list[tuple[str, str]] = [
        ("leaf_null", "  implementation:\n    llm: null\n"),
        ("leaf_missing_key", "  implementation: {}\n"),
        ("leaf_list_value", "  implementation:\n    llm: []\n"),
        ("leaf_dict_value", "  implementation:\n    llm: {nested: 1}\n"),
    ]
    for name, impl_body in cases:
        _write_universal_critique_profile(
            repo,
            name,
            f"version: 1\nuniversal_critique:\n{impl_body}",
        )
        block = parse_universal_critique_workflow_block(repo, name)
        assert block.impl_llm is False, name
