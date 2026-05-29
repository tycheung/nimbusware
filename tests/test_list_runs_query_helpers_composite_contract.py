"""``GET /v1/runs`` query helpers composite (fo111).

Four small but sharp helpers in
[packages/nimbusware_api/routes/runs.py](packages/nimbusware_api/routes/runs.py)
shape the wire-format of the ``GET /v1/runs`` list endpoint -- the
keyset cursor codec pair, the ``workflow_profile_prefix`` regex
sanitiser, and the ISO-8601 query-datetime parser. Today they are
sampled only **indirectly** by
[tests/test_api.py](tests/test_api.py) via end-to-end HTTP requests
with substring assertions
(``test_list_runs_keyset_cursor_walk``,
``test_list_runs_workflow_profile_prefix``,
``test_list_runs_invalid_created_after_returns_problem``); none pin
the wire-format / boundary contracts at the unit level. A repo-wide
``Grep`` for the four helper names returns only their definition
site.

fo111 closes that gap with 4 parts spanning 20 axes (no source
changes):

* **Part A** -- ``_encode_run_list_cursor`` (5 axes): ``str`` return
  type, exact JSON shape, compact separators, urlsafe alphabet,
  trailing ``=`` stripped.
* **Part B** -- ``_decode_run_list_cursor`` + roundtrip (5 axes):
  invariance across sample tuples, padding restoration across all 3
  valid b64 length-mod-4 residues, ``int`` coercion of ``seq``,
  ``UUID`` coercion of ``r``, 2-tuple shape.
* **Part C** -- ``_sanitize_workflow_profile_prefix`` (5 axes):
  ``None`` short-circuit, empty / whitespace-only collapse, valid
  prefix matrix (chars / leading-digit / strip-rescue), invalid
  silent-reject (NOT a ``ValueError``), 64-char accept / 65-char
  reject length boundary.
* **Part D** -- ``_parse_query_datetime`` (5 axes): ``None`` / empty
  / whitespace short-circuit, ``"Z"`` -> ``"+00:00"`` substitution,
  field-aware ``ValueError`` message interpolation, naive datetime
  assumed UTC, tz-aware datetime ``astimezone(UTC)`` shift.

KEY DIVERGENCES pinned:

* **urlsafe vs standard b64** -- the helper uses
  ``base64.urlsafe_b64encode`` which substitutes ``+`` -> ``-`` and
  ``/`` -> ``_``. A refactor that switched to plain ``b64encode``
  would silently produce URL-unsafe tokens that break clients
  treating ``next_cursor`` as an opaque query param. The cursor
  JSON's restricted byte vocabulary never produces 6-bit groups of
  62 / 63, so for ANY cursor input today the two encoders are
  bitwise identical -- meaning a refactor to ``b64encode`` would
  not affect current outputs but WOULD break a future cursor JSON
  variant that included arbitrary bytes. Part A4 pins this on two
  fronts: (1) byte-for-byte equality with
  ``urlsafe_b64encode(compact_json_bytes).rstrip('=')`` (pins the
  exact codec), AND (2) an independent self-check on the byte
  sequence ``b'\\xff\\xff\\xff'`` that confirms the two encoders DO
  diverge there (pins our reasoning that urlsafe is the safer
  choice).
* **compact JSON** -- ``separators=(",", ":")`` keeps the cursor
  token short. A refactor that dropped the kwarg would inflate
  every cursor by ~2 bytes per separator (whitespace inside the
  base64-encoded JSON). Part A3 decodes the token back and pins
  the absence of ``", "`` and ``": "`` in the JSON body.
* **int / UUID coercion at decode** -- ``int(d["s"])`` and
  ``UUID(str(d["r"]))`` are explicit type conversions. A refactor
  that returned ``d["s"]`` / ``d["r"]`` directly would silently
  switch ``seq`` to whatever JSON parses ``s`` as (e.g. ``int``
  today but ``float`` for a future ``.0`` suffix) and ``r`` to
  ``str``. Parts B3 / B4 pin both explicit casts.
* **silent reject vs ValueError** -- the sanitiser returns ``None``
  for invalid prefixes; a refactor that raised ``ValueError`` would
  bubble a 500 to the client instead of the current 200 + "filter
  ignored" behaviour. Part C4 pins the silent-reject contract.
* **field-aware error message** -- ``_parse_query_datetime`` raises
  ``ValueError(f"{field} must be a valid ISO-8601 datetime")``; the
  ``field`` interpolation lets the route layer surface
  ``created_after`` vs ``created_before`` in the 422 problem
  ``detail``. Part D3 asserts BOTH that ``ISO-8601`` appears AND
  that the supplied ``field`` name appears, using two distinct
  ``field`` values to pin the interpolation isn't hard-coded.
* **naive vs aware tz handling** -- naive datetimes are *assumed*
  UTC (``replace(tzinfo=UTC)``, no clock shift), while tz-aware
  datetimes are *converted* (``astimezone(UTC)``, clock shifts).
  Parts D4 and D5 pin both branches with hour-of-day assertions
  that catch a refactor that conflated the two (e.g. always
  ``replace``, which would silently corrupt non-UTC timestamps).
"""

from __future__ import annotations

import base64
import json
import re
from datetime import timezone
from uuid import UUID

import pytest

from nimbusware_api.routes.runs import (
    _decode_run_list_cursor,
    _encode_run_list_cursor,
    _parse_query_datetime,
    _sanitize_workflow_profile_prefix,
)

_SAMPLE_RID = UUID("11111111-1111-4111-8111-111111111111")
_SAMPLE_RID_ALT = UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")
_URLSAFE_ALPHABET_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _restore_b64_padding(value: str) -> str:
    """Re-attach the stripped ``=`` padding using the same formula the helper does.

    Used by Part A / Part B to independently round-trip the encoded
    cursor back to JSON bytes without going through
    ``_decode_run_list_cursor`` -- so a refactor that broke decode
    would NOT mask a Part A wire-format regression.
    """
    pad = "=" * ((4 - len(value) % 4) % 4)
    return value + pad


def _self_check_urlsafe_vs_standard_alphabet_differ() -> None:
    """Independently verify ``urlsafe_b64encode`` and ``b64encode`` diverge on ``0xFF`` bytes.

    Used by Part A4. The cursor JSON's restricted byte vocabulary
    (``{``, ``}``, ``"``, ``:``, ``,``, ``0-9``, ``a-f``, ``-``) never
    produces 6-bit groups of value 62 (``+``) or 63 (``/``), so
    standard and urlsafe b64 are bitwise identical for ANY cursor
    input -- which means we cannot pin the urlsafe choice from
    helper output alone. Instead, A4 pins the helper's byte-for-byte
    equality with ``urlsafe_b64encode(...).rstrip('=')`` AND this
    self-check, which independently confirms the two encoders DO
    diverge on a forcing byte sequence outside the cursor charset.
    A refactor that swapped to ``b64encode`` would still pass A4 for
    cursor inputs today but would silently break a future cursor
    JSON variant that included arbitrary bytes (e.g. binary opaque
    tokens). This self-check guards the SHAPE of the contract.
    """
    raw_force = b"\xff\xff\xff"
    std = base64.b64encode(raw_force).decode().rstrip("=")
    urlsafe = base64.urlsafe_b64encode(raw_force).decode().rstrip("=")
    assert std != urlsafe, (
        f"A4 self-check: expected urlsafe and standard b64 to differ on "
        f"``b'\\xff\\xff\\xff'`` (std=``///``, urlsafe=``___``); got "
        f"std={std!r} urlsafe={urlsafe!r}"
    )
    assert "/" in std and "/" not in urlsafe
    assert "_" in urlsafe and "_" not in std


def test_encode_run_list_cursor_wire_format_5_axis() -> None:
    """Pin ``_encode_run_list_cursor`` wire format (5 axes).

    Implementation at [runs.py:199-201](packages/nimbusware_api/routes/runs.py):

    .. code-block:: python

        raw = json.dumps({"s": seq, "r": str(run_id)},
                         separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    Together the 5 axes pin a complete RFC 4648 section 5 (URL-safe
    base64) + RFC 8259 (compact JSON) wire-format contract. A
    refactor that broke ANY of these (return type, JSON shape,
    whitespace, alphabet, padding) would shift the opaque
    ``next_cursor`` shape and silently break clients echoing it
    back. The cursor codec is the only ``200 OK`` -side opaque token
    in [GET /v1/runs](packages/nimbusware_api/routes/runs.py:267-619) so
    the wire format is effectively the API contract.

    A1 / A2 / A3 / A4 / A5 pin distinct facets that no single axis
    alone could guarantee.
    """
    out_basic = _encode_run_list_cursor(1, _SAMPLE_RID)
    assert isinstance(out_basic, str), (
        f"A1: helper must return `str` (clients concatenate into URLs), got "
        f"{type(out_basic).__name__}; a refactor that dropped `.decode()` "
        f"would return `bytes` and break ``response.headers['Link']`` "
        f"f-string concatenation"
    )
    assert not isinstance(out_basic, bytes), "A1: not bytes"

    decoded_json = base64.urlsafe_b64decode(_restore_b64_padding(out_basic)).decode()
    parsed = json.loads(decoded_json)
    assert parsed == {"s": 1, "r": str(_SAMPLE_RID)}, (
        f"A2: decoded JSON must equal exact 2-key dict ``{{'s': seq, 'r': str(uuid)}}`` "
        f"-- a refactor that added a third key (e.g. ``'v': 1``) would still pass "
        f"existing API tests but break this axis. Got: {parsed!r}"
    )
    assert list(parsed.keys()) == ["s", "r"], (
        f"A2: key order must be insertion order ``s`` then ``r`` (Python 3.7+ dict "
        f"preserves it through json.dumps); got {list(parsed.keys())!r}"
    )

    assert ": " not in decoded_json, (
        f"A3: compact JSON forbids ``': '`` between keys/values -- a refactor "
        f"that dropped ``separators=(',', ':')`` would re-introduce whitespace. "
        f"Got JSON: {decoded_json!r}"
    )
    assert ", " not in decoded_json, (
        f"A3: compact JSON forbids ``', '`` between pairs; got JSON: {decoded_json!r}"
    )

    _self_check_urlsafe_vs_standard_alphabet_differ()
    a4_cases: list[tuple[int, UUID]] = [
        (1, _SAMPLE_RID),
        (12345, _SAMPLE_RID),
        (42, _SAMPLE_RID_ALT),
        (9_999_999_999, _SAMPLE_RID_ALT),
    ]
    for seq, rid in a4_cases:
        out = _encode_run_list_cursor(seq, rid)
        assert _URLSAFE_ALPHABET_RE.fullmatch(out) is not None, (
            f"A4: output must consist exclusively of [A-Za-z0-9_-] "
            f"(no ``+``, no ``/``, no padding); got seq={seq} rid={rid} "
            f"out={out!r}"
        )
        raw = json.dumps({"s": seq, "r": str(rid)}, separators=(",", ":")).encode()
        expected_urlsafe = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        assert out == expected_urlsafe, (
            f"A4: helper output must match ``urlsafe_b64encode("
            f"compact_json_bytes).rstrip('=')`` byte-for-byte. A refactor "
            f"that introduced any pre/post-processing (e.g. URL-encoding, "
            f"prefixing) would break this. Got seq={seq} rid={rid} "
            f"out={out!r} expected={expected_urlsafe!r}"
        )

    for seq in (1, 12, 123, 1234, 12345):
        out = _encode_run_list_cursor(seq, _SAMPLE_RID)
        assert not out.endswith("="), (
            f"A5: trailing ``=`` padding must be stripped -- a refactor that "
            f"dropped ``.rstrip('=')`` would leak base64 padding into the URL, "
            f"which is itself URL-reserved per RFC 3986 §2.2 and must be "
            f"percent-encoded. Got seq={seq} out={out!r}"
        )


def test_decode_run_list_cursor_roundtrip_and_coercion_5_axis() -> None:
    """Pin ``_decode_run_list_cursor`` + roundtrip + coercion (5 axes).

    Implementation at [runs.py:204-208](packages/nimbusware_api/routes/runs.py):

    .. code-block:: python

        pad = "=" * ((4 - len(value) % 4) % 4)
        raw = base64.urlsafe_b64decode(value + pad)
        d = json.loads(raw.decode())
        return int(d["s"]), UUID(str(d["r"]))

    Five axes pin: roundtrip invariance, padding restoration across
    every valid base64 length-mod-4 residue (0 / 2 / 3 -- residue 1
    is impossible from b64 encoding so excluded), explicit ``int``
    coercion, explicit ``UUID`` coercion, and 2-tuple return shape.
    A refactor that dropped the ``int(...)`` would silently change
    the public type of ``cursor_seq`` (currently ``int``, fed into
    ``store.list_recent_run_rows_cursor(cursor_after_seq=...)`` at
    [runs.py:494](packages/nimbusware_api/routes/runs.py)); a refactor
    that dropped ``UUID(str(...))`` would change ``cursor_rid``'s
    public type and break the SQL parameter binding downstream.
    """
    sample_tuples = [
        (1, _SAMPLE_RID),
        (42, _SAMPLE_RID_ALT),
        (12345, _SAMPLE_RID),
        (9_999_999_999, _SAMPLE_RID_ALT),
    ]
    for seq, rid in sample_tuples:
        encoded = _encode_run_list_cursor(seq, rid)
        decoded = _decode_run_list_cursor(encoded)
        assert decoded == (seq, rid), (
            f"B1: roundtrip ``decode(encode(seq, rid))`` must equal "
            f"``(seq, rid)`` for {(seq, rid)!r}; got {decoded!r}"
        )

    by_residue: dict[int, tuple[int, str]] = {}
    for s in range(1, 10_000):
        enc = _encode_run_list_cursor(s, _SAMPLE_RID)
        residue = len(enc) % 4
        if residue not in by_residue:
            by_residue[residue] = (s, enc)
        if {0, 2, 3}.issubset(by_residue.keys()):
            break
    assert {0, 2, 3}.issubset(by_residue.keys()), (
        "B2 setup: failed to find encoded values covering all 3 valid b64 "
        f"length residues (0 / 2 / 3); got residues={sorted(by_residue.keys())!r}"
    )
    for residue, (s, enc) in sorted(by_residue.items()):
        decoded_seq, decoded_rid = _decode_run_list_cursor(enc)
        assert (decoded_seq, decoded_rid) == (s, _SAMPLE_RID), (
            f"B2: padding restoration must work for length residue {residue} "
            f"(needs {(4 - residue) % 4} ``=`` pads); decode({enc!r}) failed "
            f"to recover (seq={s}, rid={_SAMPLE_RID}). Got "
            f"({decoded_seq!r}, {decoded_rid!r})"
        )
        manual = enc + ("=" * ((4 - residue) % 4))
        manual_decoded_json = base64.urlsafe_b64decode(manual).decode()
        manual_parsed = json.loads(manual_decoded_json)
        assert manual_parsed == {"s": s, "r": str(_SAMPLE_RID)}, (
            f"B2: manual padding restoration (appending {((4 - residue) % 4)} "
            f"``=`` chars) must yield the same JSON the helper's internal "
            f"pad logic does for residue {residue}; got {manual_parsed!r}"
        )

    encoded_for_types = _encode_run_list_cursor(7, _SAMPLE_RID)
    decoded_seq, decoded_rid = _decode_run_list_cursor(encoded_for_types)
    assert type(decoded_seq) is int, (
        f"B3: ``seq`` must be coerced to ``int`` (json may parse ``7`` as int "
        f"today but a refactor that returned ``d['s']`` directly would let "
        f"a future ``.0`` suffix slip through as float). Got "
        f"type={type(decoded_seq).__name__}"
    )
    assert decoded_seq == 7
    assert not isinstance(decoded_seq, bool), (
        "B3: ``bool`` is a subclass of ``int`` in Python -- a refactor that "
        "kept ``int(d['s'])`` but passed ``d['s'] is True/False`` would slip "
        "past a naive isinstance check; ``type(...) is int`` rejects bools"
    )

    assert isinstance(decoded_rid, UUID), (
        f"B4: ``r`` must be coerced to ``UUID`` (json returns ``str``); a "
        f"refactor that returned ``d['r']`` directly would break the SQL "
        f"binding in ``store.list_recent_run_rows_cursor`` which expects "
        f"``UUID``. Got type={type(decoded_rid).__name__}"
    )
    assert decoded_rid == _SAMPLE_RID

    result = _decode_run_list_cursor(encoded_for_types)
    assert isinstance(result, tuple), (
        f"B5: return must be a 2-tuple (route layer destructures as "
        f"``cs, cr = _decode_run_list_cursor(...)``); got {type(result).__name__}"
    )
    assert len(result) == 2, f"B5: tuple must have exactly 2 elements; got len={len(result)}"


def test_sanitize_workflow_profile_prefix_regex_5_axis() -> None:
    """Pin ``_sanitize_workflow_profile_prefix`` regex contract (5 axes).

    Implementation at [runs.py:190-196](packages/nimbusware_api/routes/runs.py):

    .. code-block:: python

        if value is None or not str(value).strip():
            return None
        s = str(value).strip()
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", s):
            return None
        return s

    Five axes pin the early-out short-circuit, the strip-and-collapse
    rule, the accept matrix, the reject-without-raise contract, and
    the length boundary (1..64 chars). A refactor that tightened the
    regex (e.g. first char ``[a-z]`` only) would silently drop
    UPPERCASE prefixes today's tests don't exercise; a refactor that
    raised ``ValueError`` would propagate a 500 instead of the route
    layer's current 200 + "filter ignored" behaviour.
    """
    assert _sanitize_workflow_profile_prefix(None) is None, (
        "C1: ``None`` input short-circuits to ``None`` BEFORE the ``.strip()`` "
        "call -- a refactor that dropped the ``value is None`` guard would "
        "``str(None).strip()`` -> ``'None'`` which then PASSES the regex "
        "and returns the string ``'None'`` -- a silent and dangerous leak"
    )

    for empty in ("", "   ", "\t", "\n", "  \t\n  ", " "):
        assert _sanitize_workflow_profile_prefix(empty) is None, (
            f"C2: whitespace-only inputs must collapse to ``None`` via "
            f"``not str(value).strip()``; got non-None for input {empty!r}"
        )

    valid_cases: list[tuple[str, str, str]] = [
        ("lowercase", "default", "default"),
        ("uppercase", "ADMIN", "ADMIN"),
        ("digits_only", "12345", "12345"),
        ("leading_digit", "1abc", "1abc"),
        ("mixed_alnum", "abc123XYZ", "abc123XYZ"),
        ("hyphens", "abc-def", "abc-def"),
        ("underscores", "abc_def", "abc_def"),
        ("dots", "abc.def", "abc.def"),
        ("single_char_lower", "a", "a"),
        ("single_char_digit", "0", "0"),
        ("strip_rescue_padded", "  default  ", "default"),
        ("strip_rescue_tabs", "\tdefault\t", "default"),
        ("all_special_after_first", "A_._-_.-_", "A_._-_.-_"),
    ]
    for name, raw, expected in valid_cases:
        got = _sanitize_workflow_profile_prefix(raw)
        assert got == expected, (
            f"C3 case={name!r} raw={raw!r}: expected stripped value {expected!r}, "
            f"got {got!r}"
        )

    invalid_leading: list[tuple[str, str]] = [
        ("leading_underscore", "_foo"),
        ("leading_dot", ".foo"),
        ("leading_hyphen", "-foo"),
    ]
    for name, raw in invalid_leading:
        got = _sanitize_workflow_profile_prefix(raw)
        assert got is None, (
            f"C4 case={name!r} raw={raw!r}: first char must be ``[a-zA-Z0-9]``; "
            f"expected None, got {got!r}"
        )

    invalid_chars: list[tuple[str, str]] = [
        ("space_mid", "foo bar"),
        ("slash_mid", "foo/bar"),
        ("colon_mid", "foo:bar"),
        ("plus_mid", "foo+bar"),
        ("at_mid", "foo@bar"),
        ("paren_mid", "foo(bar)"),
    ]
    for name, raw in invalid_chars:
        try:
            got = _sanitize_workflow_profile_prefix(raw)
        except ValueError as exc:  # pragma: no cover - the assertion catches it
            pytest.fail(
                f"C4 case={name!r} raw={raw!r}: sanitiser must silently return "
                f"``None``, NOT raise ``ValueError``. A refactor to ``raise`` "
                f"would propagate a 500 instead of the current 200 + filter-"
                f"ignored behaviour. Raised: {exc!s}"
            )
        assert got is None, (
            f"C4 case={name!r} raw={raw!r}: expected None silent reject, got {got!r}"
        )

    accept_64 = "a" + "b" * 63
    assert len(accept_64) == 64
    assert _sanitize_workflow_profile_prefix(accept_64) == accept_64, (
        "C5: exactly 64 chars must be accepted (regex is ``[a-zA-Z0-9]"
        "[a-zA-Z0-9_.-]{0,63}`` -> 1 + up to 63 = 1..64 inclusive). "
        "Got rejection for len-64 input"
    )

    accept_1 = "a"
    assert _sanitize_workflow_profile_prefix(accept_1) == accept_1, (
        "C5: exactly 1 char must be accepted (min length); a refactor "
        "that required ``{1,63}`` instead of ``{0,63}`` would reject "
        "single-char prefixes silently"
    )

    reject_65 = "a" + "b" * 64
    assert len(reject_65) == 65
    assert _sanitize_workflow_profile_prefix(reject_65) is None, (
        "C5: 65 chars must be rejected with ``None`` (one over the "
        "inclusive max); a refactor that used ``{0,64}`` would silently "
        "accept it"
    )

    strip_rescue = "  " + "a" * 60 + "  "
    expected_stripped = "a" * 60
    assert _sanitize_workflow_profile_prefix(strip_rescue) == expected_stripped, (
        "C5: surrounding whitespace must be stripped before length is "
        "evaluated -- ``len('  ' + 'a'*60 + '  ')=64`` would pass the regex "
        "raw, but the helper ``.strip()`` first so the regex sees "
        "the 60-char inner string. Got mismatch."
    )


def test_parse_query_datetime_iso8601_tz_5_axis() -> None:
    """Pin ``_parse_query_datetime`` ISO-8601 + tz handling (5 axes).

    Implementation at [runs.py:249-260](packages/nimbusware_api/routes/runs.py):

    .. code-block:: python

        if value is None or not str(value).strip():
            return None
        try:
            s = str(value).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
        except ValueError as exc:
            msg = f"{field} must be a valid ISO-8601 datetime"
            raise ValueError(msg) from exc
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    Five axes pin the empty-input short-circuit, the ``Z`` -> UTC
    substitution (Python 3.10 ``fromisoformat`` does not accept
    ``Z`` natively even in 3.11+), the field-aware ``ValueError``
    message interpolation, the naive-assumed-UTC arm, and the
    tz-aware-astimezone(UTC) arm. The two tz arms catch a refactor
    that conflated them by using ``replace(tzinfo=UTC)``
    unconditionally -- which would silently corrupt non-UTC
    timestamps (axis D5).
    """
    for empty in (None, "", "   ", "\t", "\n"):
        got = _parse_query_datetime("created_after", empty)
        assert got is None, (
            f"D1: empty / whitespace input must short-circuit to ``None`` "
            f"BEFORE the try/except -- a refactor that dropped the guard "
            f"would feed ``''`` to ``datetime.fromisoformat`` and raise "
            f"``ValueError`` (visible as 422 to clients filtering nothing). "
            f"Got non-None for input {empty!r}: {got!r}"
        )

    dt_with_z = _parse_query_datetime("created_after", "2020-01-01T00:00:00Z")
    dt_with_offset = _parse_query_datetime("created_after", "2020-01-01T00:00:00+00:00")
    assert dt_with_z is not None and dt_with_offset is not None
    assert dt_with_z == dt_with_offset, (
        f"D2: ``Z`` suffix must be substituted to ``+00:00`` so both literals "
        f"produce the same UTC datetime. A refactor that dropped the "
        f"``.replace('Z', '+00:00')`` would raise ``ValueError`` on the Z "
        f"form (Python <3.11 ``fromisoformat`` rejects ``Z``). Got "
        f"Z={dt_with_z!r} offset={dt_with_offset!r}"
    )
    assert dt_with_z.tzinfo == timezone.utc, (
        f"D2: result of Z-form parse must have ``tzinfo=UTC``; got "
        f"{dt_with_z.tzinfo!r}"
    )

    with pytest.raises(ValueError) as exc_a:
        _parse_query_datetime("created_after", "not-a-date")
    msg_a = str(exc_a.value)
    assert "created_after" in msg_a, (
        f"D3: ``ValueError`` message must interpolate ``field`` name "
        f"(``created_after``) so the route layer surfaces it in the 422 "
        f"problem detail. Got: {msg_a!r}"
    )
    assert "ISO-8601" in msg_a, (
        f"D3: ``ValueError`` message must mention ``ISO-8601`` to help "
        f"clients debug the format expectation. Got: {msg_a!r}"
    )

    with pytest.raises(ValueError) as exc_b:
        _parse_query_datetime("created_before", "garbage")
    msg_b = str(exc_b.value)
    assert "created_before" in msg_b, (
        f"D3: distinct ``field=created_before`` must appear in the error "
        f"message (catches a refactor that hard-coded the field name as a "
        f"literal). Got: {msg_b!r}"
    )
    assert "created_after" not in msg_b, (
        f"D3: hard-coded ``created_after`` must NOT leak into a "
        f"``created_before`` error; got: {msg_b!r}"
    )

    naive = _parse_query_datetime("created_after", "2020-06-15T12:34:56")
    assert naive is not None
    assert naive.tzinfo == timezone.utc, (
        f"D4: naive datetime must have ``tzinfo`` ASSUMED to UTC via "
        f"``replace(tzinfo=UTC)`` (NOT shifted); got tzinfo={naive.tzinfo!r}"
    )
    assert (naive.year, naive.month, naive.day) == (2020, 6, 15)
    assert (naive.hour, naive.minute, naive.second) == (12, 34, 56), (
        f"D4: naive datetime must NOT shift wall-clock (replace, not "
        f"astimezone) -- input ``2020-06-15T12:34:56`` -> UTC 12:34:56. "
        f"A refactor that called ``.astimezone(UTC)`` on a naive would "
        f"raise on Python <3.6 or use local TZ on 3.6+ (host-dependent). "
        f"Got hour={naive.hour} minute={naive.minute} second={naive.second}"
    )

    aware = _parse_query_datetime("created_after", "2020-06-15T12:00:00+05:00")
    assert aware is not None
    assert aware.tzinfo == timezone.utc, (
        f"D5: tz-aware result must be normalised to UTC tzinfo; got "
        f"{aware.tzinfo!r}"
    )
    assert (aware.year, aware.month, aware.day) == (2020, 6, 15)
    assert aware.hour == 7, (
        f"D5: tz-aware input must be CONVERTED via ``astimezone(UTC)`` -- "
        f"``2020-06-15T12:00:00+05:00`` is ``2020-06-15T07:00:00+00:00``. "
        f"A refactor that used ``replace(tzinfo=UTC)`` on the aware branch "
        f"would silently corrupt the timestamp to ``12:00:00+00:00`` (a "
        f"5-hour future-shift). Got hour={aware.hour}"
    )
    assert (aware.minute, aware.second) == (0, 0)

    aware_negative = _parse_query_datetime("created_after", "2020-06-15T03:00:00-04:00")
    assert aware_negative is not None
    assert aware_negative.tzinfo == timezone.utc
    assert aware_negative.hour == 7, (
        f"D5: negative tz offset must also convert correctly -- "
        f"``2020-06-15T03:00:00-04:00`` is ``2020-06-15T07:00:00+00:00`` "
        f"(adding 4 hours). Got hour={aware_negative.hour}"
    )
