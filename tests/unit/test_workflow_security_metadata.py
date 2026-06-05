"""parse ``security_scan_metadata_on_verify`` from workflow YAML."""

from __future__ import annotations

from pathlib import Path

from nimbusware_env import find_repo_root
from nimbusware_orchestrator.workflow_security_metadata import (
    parse_security_scan_metadata_on_verify_workflow,
)

ROOT = find_repo_root(start=Path(__file__).resolve().parents[1])


def test_parse_security_scan_false_on_default_profile() -> None:
    assert not parse_security_scan_metadata_on_verify_workflow(ROOT, "default")


def test_parse_security_scan_true_on_optional_profile() -> None:
    assert (
        parse_security_scan_metadata_on_verify_workflow(ROOT, "security_scan_metadata_on") is True
    )


def test_parse_security_scan_missing_profile() -> None:
    assert not parse_security_scan_metadata_on_verify_workflow(ROOT, None)


def _write_profile(tmp_path: Path, name: str, body: str) -> None:
    wf_dir = tmp_path / "configs" / "workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.yaml").write_text(body, encoding="utf-8")


def test_parse_security_scan_dict_enabled_true(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_dict_on",
        "version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: true\n",
    )
    assert parse_security_scan_metadata_on_verify_workflow(tmp_path, "sec_dict_on") is True


def test_parse_security_scan_dict_enabled_false(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_dict_off",
        "version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: false\n",
    )
    assert not parse_security_scan_metadata_on_verify_workflow(tmp_path, "sec_dict_off")


def test_parse_security_scan_dict_empty_returns_false(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_dict_empty",
        "version: 1\nsecurity_scan_metadata_on_verify: {}\n",
    )
    assert not parse_security_scan_metadata_on_verify_workflow(tmp_path, "sec_dict_empty")


def test_parse_security_scan_dict_enabled_maybe_string_returns_false(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_dict_badstr",
        "version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: maybe\n",
    )
    assert not parse_security_scan_metadata_on_verify_workflow(tmp_path, "sec_dict_badstr")


def test_parse_security_scan_dict_enabled_list_returns_false(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_dict_badnest",
        "version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: []\n",
    )
    assert not parse_security_scan_metadata_on_verify_workflow(tmp_path, "sec_dict_badnest")


def test_parse_security_scan_top_level_list_returns_false(tmp_path: Path) -> None:
    _write_profile(
        tmp_path,
        "sec_list_top",
        "version: 1\nsecurity_scan_metadata_on_verify: []\n",
    )
    assert not parse_security_scan_metadata_on_verify_workflow(tmp_path, "sec_list_top")


def test_parse_security_scan_top_level_scalar_coercion(tmp_path: Path) -> None:
    """Pin §14 #18 ``_parse_security_scan_metadata_value`` legacy-scalar arms.

    Top-level ``security_scan_metadata_on_verify`` accepts ``bool`` (covered by repo
    profiles), and falls through to numeric / string-truthy / string-non-truthy / ``null``
    arms documented here. Numeric values use ``bool(...)`` truthiness (``0``/``0.0`` →
    False; everything else → True). Strings use the case-insensitive whitespace-trimmed
    truthy tuple ``("1", "true", "yes", "on")``; anything else → False. YAML ``null`` is
    short-circuited to False at the entrypoint (``v is not None else False``) before
    reaching the inner ladder. Locks the contract so a future refactor (e.g. unifying
    with ``env_over_yaml`` semantics from ``workflow_universal_critique``) must update
    this test on purpose.
    """
    cases: list[tuple[str, str, bool]] = [
        ("top_int_one", "1", True),
        ("top_int_zero", "0", False),
        ("top_float_truthy", "1.5", True),
        ("top_float_zero", "0.0", False),
        ("top_str_yes", '"yes"', True),
        ("top_str_true_padded", '"  TRUE  "', True),
        ("top_str_on", '"on"', True),
        ("top_str_off", '"off"', False),
        ("top_str_junk", '"junk"', False),
        ("top_null", "null", False),
    ]
    for name, raw, expected in cases:
        _write_profile(
            tmp_path,
            name,
            f"version: 1\nsecurity_scan_metadata_on_verify: {raw}\n",
        )
        actual = parse_security_scan_metadata_on_verify_workflow(tmp_path, name)
        assert actual is expected, name


def test_parse_security_scan_dict_enabled_numeric_and_str_truthy_arms(
    tmp_path: Path,
) -> None:
    """Pin §14 #18 ``_coerce_security_scan_metadata_enabled_value`` nested-dict arms.

    Complements the existing ``_dict_enabled_true``/``_false``/``_maybe_string``/``_list``
    tests by pinning the numeric (``int`` / ``float``), case-insensitive
    whitespace-trimmed string-truthy (``"ON"`` / ``"  on  "`` / ``"yes"``), and
    ``null``-fallthrough arms inside the dict form
    ``security_scan_metadata_on_verify: { enabled: ... }``. ``null`` is **not**
    short-circuited at the entrypoint for the dict form — it flows into the coercer
    and falls past the ``bool``/``int``/``float``/``str`` ladder to the final
    ``return False``. Locks the contract so any future refactor that wants to widen the
    string-truthy tuple (e.g. adding ``"y"``) must update this test on purpose.
    """
    cases: list[tuple[str, str, bool]] = [
        ("dict_int_one", "1", True),
        ("dict_int_zero", "0", False),
        ("dict_float_truthy", "1.5", True),
        ("dict_float_zero", "0.0", False),
        ("dict_str_upper", '"ON"', True),
        ("dict_str_padded", '"  on  "', True),
        ("dict_str_yes", '"yes"', True),
        ("dict_str_off", '"off"', False),
        ("dict_null", "null", False),
    ]
    for name, raw, expected in cases:
        _write_profile(
            tmp_path,
            name,
            f"version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: {raw}\n",
        )
        actual = parse_security_scan_metadata_on_verify_workflow(tmp_path, name)
        assert actual is expected, name


def test_security_scan_metadata_truthy_case_insensitive_strings_round_trip(
    tmp_path: Path,
) -> None:
    """Pin §14 #18 ``.lower()`` case-folding for **both** string-arm ladders.

    :mod:`workflow_security_metadata` exposes two related entry points that share an
    identical string-arm tuple ladder (``raw.strip().lower() in ("1", "true", "yes",
    "on")``):

    - **Top-level legacy form** (``security_scan_metadata_on_verify: "TRUE"``) routes
      through :func:`_parse_security_scan_metadata_value`.
    - **Nested dict form** (``security_scan_metadata_on_verify:\\n  enabled: "TRUE"``)
      routes through :func:`_coerce_security_scan_metadata_enabled_value`.

    Follow-on 54 sampled a handful of case-folded variants per entry point
    (top-level `"  TRUE  "`, nested `"ON"` / `"  on  "`); this test adds 8 NEW
    case-folded variants and exercises **both entry points per case** so a
    refactor that drops ``.lower()`` from only one of the two ladders surfaces
    via the per-case ``top:<raw>`` / ``nested:<raw>`` message identifying the
    failing form. Mirrors follow-on 59 Part A's case-folding contract for
    ``_coerce_yaml_bool`` and follow-on 60 Part C's tuple-ladder contract for
    escalation.

    All YAML scalars are quoted so PyYAML's YAML 1.1 bool resolver does not
    eagerly convert unquoted ``TRUE`` / ``Yes`` / ``On`` to Python ``bool`` and
    bypass the string arm — same caveat documented in follow-on 59.
    """
    cases: list[tuple[str, str]] = [
        ("upper_true", '"TRUE"'),
        ("title_true", '"True"'),
        ("title_yes", '"Yes"'),
        ("upper_yes", '"YES"'),
        ("title_on", '"On"'),
        ("mixed_on", '"oN"'),
        ("mixed_yes", '"yEs"'),
        ("mixed_true", '"trUE"'),
    ]
    for name, raw in cases:
        _write_profile(
            tmp_path,
            f"top_{name}",
            f"version: 1\nsecurity_scan_metadata_on_verify: {raw}\n",
        )
        assert (
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                f"top_{name}",
            )
            is True
        ), f"top:{raw}"
        _write_profile(
            tmp_path,
            f"nested_{name}",
            f"version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: {raw}\n",
        )
        assert (
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                f"nested_{name}",
            )
            is True
        ), f"nested:{raw}"


def test_security_scan_metadata_truthy_whitespace_trimmed_strings_round_trip(
    tmp_path: Path,
) -> None:
    """Pin §14 #18 ``.strip()`` whitespace handling for **both** string-arm ladders.

    Complements Part A by covering the ``.strip()`` half of the
    ``raw.strip().lower() in (...)`` contract. Cases include plain-ASCII space
    padding, tab + newline escape sequences (preserved by PyYAML's double-quoted
    decoder and stripped by Python's default Unicode-whitespace ``.strip()``),
    and combined case + whitespace edges. Each variant is exercised through
    **both** entry points so a regression in only one ladder surfaces via the
    per-case ``top:<raw>`` / ``nested:<raw>`` message.

    The ``ws_on_pad_double`` case mirrors a follow-on 54 nested-form sample but
    adds the missing top-level coverage; the ``ws_true_pad`` case is the
    inverse — top-level was sampled in follow-on 54 but nested was not. Both
    are intentionally kept so the dual-entry-point sweep is uniform.

    Mirrors follow-on 59 Part B's ``.strip()`` contract for ``_coerce_yaml_bool``
    and follow-on 60 Part C's whitespace coverage for escalation.
    """
    cases: list[tuple[str, str]] = [
        ("ws_one", '"  1  "'),
        ("ws_yes_pad", '" yes "'),
        ("ws_tab_true_lf", '"\\ttrue\\n"'),
        ("ws_on_pad_double", '"  on  "'),
        ("ws_true_pad", '"  TRUE  "'),
        ("ws_tab_yes", '"\\tyes"'),
        ("ws_yes_tab", '"yes\\t"'),
    ]
    for name, raw in cases:
        _write_profile(
            tmp_path,
            f"top_{name}",
            f"version: 1\nsecurity_scan_metadata_on_verify: {raw}\n",
        )
        assert (
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                f"top_{name}",
            )
            is True
        ), f"top:{raw}"
        _write_profile(
            tmp_path,
            f"nested_{name}",
            f"version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: {raw}\n",
        )
        assert (
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                f"nested_{name}",
            )
            is True
        ), f"nested:{raw}"


def test_security_scan_metadata_falsy_and_unknown_strings_round_trip(
    tmp_path: Path,
) -> None:
    """Pin §14 #18 exclusive-tuple-membership negative branch for **both** ladders.

    The string arm returns ``False`` for anything that, after ``.strip().lower()``,
    is not in ``("1", "true", "yes", "on")``. Follow-on 54 sampled a handful of
    falsy / unknown tokens (top-level ``"off"`` / ``"junk"``, nested ``"off"`` /
    unquoted ``maybe``); this test pins 9 additional variants across three
    failure modes, with each case exercised through **both** entry points:

    1. **Case-folded falsy tokens** (``"FALSE"`` / ``"False"`` / ``"  OFF  "`` /
       ``"NO"`` / ``"nO"``) reach the tuple as ``"false"`` / ``"off"`` / ``"no"``
       and fall through.
    2. **Near-miss / interior-whitespace tokens** (``"true!"`` extra char /
       ``" ye s "`` interior whitespace) demonstrate that ``.strip()`` only
       trims edges — interior whitespace and trailing punctuation break tuple
       membership.
    3. **Stripped-to-empty inputs** (``""`` / ``"   "``) reach the tuple as
       ``""``, distinct from the entry-point ``null`` short-circuit pinned in
       follow-on 54 because empty string actually enters the string arm and
       falls through tuple membership rather than the entry-point guard.

    Mirrors follow-on 59 Part C's exclusive-membership contract for
    ``_coerce_yaml_bool`` and follow-on 60 Part C's falsy / near-miss coverage
    for escalation. Per-case ``top:<raw>`` / ``nested:<raw>`` messages identify
    both the failing entry point and the offending YAML scalar.
    """
    cases: list[tuple[str, str]] = [
        ("upper_false", '"FALSE"'),
        ("title_false", '"False"'),
        ("upper_off_padded", '"  OFF  "'),
        ("upper_no", '"NO"'),
        ("mixed_no", '"nO"'),
        ("near_miss_bang", '"true!"'),
        ("interior_ws_yes", '" ye s "'),
        ("empty_quoted", '""'),
        ("only_whitespace", '"   "'),
    ]
    for name, raw in cases:
        _write_profile(
            tmp_path,
            f"top_{name}",
            f"version: 1\nsecurity_scan_metadata_on_verify: {raw}\n",
        )
        assert (
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                f"top_{name}",
            )
            is False
        ), f"top:{raw}"
        _write_profile(
            tmp_path,
            f"nested_{name}",
            f"version: 1\nsecurity_scan_metadata_on_verify:\n  enabled: {raw}\n",
        )
        assert (
            parse_security_scan_metadata_on_verify_workflow(
                tmp_path,
                f"nested_{name}",
            )
            is False
        ), f"nested:{raw}"
