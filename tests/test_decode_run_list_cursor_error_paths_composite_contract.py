"""``_decode_run_list_cursor`` error-paths + ``invalid_cursor`` 422 composite (fo117).

Two coupled surfaces in
[packages/nimbusware_api/routes/runs.py](packages/nimbusware_api/routes/runs.py)
shape the ``cursor`` query-param error contract of ``GET /v1/runs``:

* ``_decode_run_list_cursor(value)`` -- 4-line helper at lines 204-208
  with **three** distinct exception layers:

  .. code-block:: python

      pad = "=" * ((4 - len(value) % 4) % 4)
      raw = base64.urlsafe_b64decode(value + pad)   # binascii.Error
      d = json.loads(raw.decode())                  # UnicodeDecodeError / JSONDecodeError
      return int(d["s"]), UUID(str(d["r"]))         # TypeError / KeyError / ValueError

* The route layer catch tuple at lines 466-481 maps **six** explicit
  exception classes to a ``422 invalid_cursor`` problem JSON:

  .. code-block:: python

      except (
          ValueError, KeyError, TypeError,
          json.JSONDecodeError, binascii.Error, UnicodeDecodeError,
      ) as exc:
          raise HTTPException(
              status_code=422,
              detail=problem("invalid_cursor",
                             "cursor is not a valid keyset token",
                             details={"reason": str(exc)}),
          ) from exc

fo111 Part B
([tests/test_list_runs_query_helpers_composite_contract.py:236-330](tests/test_list_runs_query_helpers_composite_contract.py))
pinned the HAPPY-path roundtrip / padding residues / coercion shape;
[tests/test_api.py:906-909](tests/test_api.py) samples ONE 422
(``"not-valid-base64!!!"``) without distinguishing which exception
fired. fo117 closes the remaining matrix in 4 parts spanning 20 axes:

* **Part A** -- base64 / UTF-8 / JSON parse-layer errors (5 axes):
  single-char ``binascii.Error``, b64-of-non-UTF-8 ``UnicodeDecodeError``,
  b64-decoding-to-empty-bytes ``json.JSONDecodeError``, b64-of-non-JSON-text
  ``json.JSONDecodeError``, 3-flavour malformed-JSON ``json.JSONDecodeError``.
* **Part B** -- JSON-to-dict structural errors (5 axes): JSON int /
  ``None`` / list / string each raise ``TypeError`` on ``d["s"]``, and
  3 missing-key sub-cases (``{}`` / ``{"s": 1}`` / ``{"r": "<uuid>"}``)
  raise ``KeyError``. Pins the **bracket-access** contract (``d["s"]``
  not ``d.get("s")``).
* **Part C** -- field-coercion errors on a valid dict (5 axes):
  ``int("abc")`` ``ValueError`` vs ``int([1, 2])`` ``TypeError`` for
  the SAME field, ``UUID("not-a-uuid")`` ``ValueError``,
  ``UUID(str(5)) == UUID("5")`` ``ValueError`` (pins the ``str()``
  wrapping behaviour around ints), ``UUID(str(None)) == UUID("None")``
  ``ValueError`` (pins ``str()`` wrapping for ``None``).
* **Part D** -- route-layer ``invalid_cursor`` 422 integration matrix
  (5 axes): TestClient ``GET /v1/runs?cursor=<malformed>`` for each
  distinct exception class, plus the empty-cursor short-circuit at
  [runs.py:449](packages/nimbusware_api/routes/runs.py) returning 200.

KEY DIVERGENCES pinned across the composite:

* **6 distinct exception classes per the catch tuple** -- ``ValueError``
  is the PARENT class of ``json.JSONDecodeError``, ``binascii.Error``,
  AND ``UnicodeDecodeError`` (verified via ``issubclass``). The explicit
  6-item tuple in the route is belt-and-suspenders. A "simplify to
  ``except ValueError``" refactor would silently DROP the ``KeyError``
  and ``TypeError`` arms, turning ``b'{}'`` / ``b'5'`` cursors into
  ``500`` server errors instead of ``422`` client problems. Part D D4
  pins **both** non-ValueError-subclass arms via 422 assertions.
* **``int(...)`` vs ``UUID(...)`` coercion error class** -- ``int("abc")``
  raises ``ValueError`` while ``int([1, 2])`` raises ``TypeError`` --
  same field, different exception class depending on value type.
  A refactor wrapping coercion in a custom error class would alter
  which exception class fires. Part C C1 / C2 pin both classes per
  field.
* **bracket access vs ``.get(...)``** -- the helper uses ``d["s"]`` /
  ``d["r"]`` which raises ``KeyError`` on a missing key. A refactor
  swapping to ``d.get("s")`` would silently produce ``int(None)``
  ``TypeError`` instead -- a DIFFERENT exception class that would
  still 422 today (because ``TypeError`` is also in the catch tuple)
  BUT would be indistinguishable from B1's "JSON parses to int" arm
  in operator logs, losing diagnostic specificity. Part B5 pins the
  bracket-access contract via the ``KeyError`` class assertion.
* **``str(...)`` wrapping in UUID coercion** -- ``UUID(str(d["r"]))``
  wraps ``d["r"]`` in ``str()`` BEFORE handing it to ``UUID(...)``.
  This means ``d["r"] == 5`` becomes ``UUID("5")`` (ValueError) NOT
  ``UUID(5)`` (TypeError -- ``UUID`` constructor rejects ints), and
  ``d["r"] is None`` becomes ``UUID("None")`` (ValueError) NOT
  ``UUID(None)`` (TypeError). A refactor that dropped the ``str()``
  wrapper would CHANGE the exception class for these inputs. Part C
  C4 / C5 pin the wrapping behaviour via the ``ValueError`` class.
* **empty-cursor short-circuit** -- the route at
  [runs.py:449](packages/nimbusware_api/routes/runs.py) computes
  ``use_cursor = cursor is not None and str(cursor).strip() != ""``
  BEFORE calling the helper. Empty / whitespace-only / omitted
  cursors return a NORMAL 200 list, NOT a 422. This is distinct from
  a malformed-but-non-empty cursor. Part D D5 pins all 3 short-circuit
  inputs.
* **``from exc`` causal chain** -- the route uses
  ``raise HTTPException(...) from exc`` at line 481 preserving the
  original exception. The ``details.reason`` field carries ``str(exc)``
  which is the operator-visible diagnostic. Part D D1 pins both that
  ``reason`` is present AND that it is a non-empty string.
"""

from __future__ import annotations

import base64
import binascii
import json

import pytest
from fastapi.testclient import TestClient

from nimbusware_api.app import app
from nimbusware_api.routes.runs import _decode_run_list_cursor

_SAMPLE_UUID_STR = "11111111-1111-4111-8111-111111111111"


def _encode_for_cursor(raw: bytes) -> str:
    """Return a URL-safe base64 cursor token that, after the helper's
    padding restoration, decodes back to ``raw``.

    Mirrors ``_encode_run_list_cursor``'s final two operations
    (``urlsafe_b64encode(...).rstrip('=')``) so each test can target
    the **layer** of failure (b64 / utf-8 / json / non-dict /
    field-coercion) independently. Using this helper instead of
    handing raw bytes to ``base64.urlsafe_b64encode`` directly lets
    each axis state its intent in terms of "the decoded raw bytes
    look like X".
    """
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


@pytest.fixture
def client() -> TestClient:
    """Local TestClient fixture mirroring ``tests/test_api.py:32-34``.

    Defined in this file (not imported) so the test file is
    self-contained and can be run in isolation
    (``pytest tests/test_decode_run_list_cursor_error_paths_composite_contract.py``).
    """
    with TestClient(app) as c:
        yield c


# -- Inheritance / catch-tuple shape pre-flight --------------------------------


def test_catch_tuple_exception_class_inheritance_preflight() -> None:
    """Pin the inheritance shape underpinning the entire composite.

    The route catch tuple at
    [runs.py:466-473](packages/nimbusware_api/routes/runs.py) lists 6
    explicit classes:

    .. code-block:: python

        except (ValueError, KeyError, TypeError,
                json.JSONDecodeError, binascii.Error, UnicodeDecodeError) as exc:

    Three of these are ``ValueError`` subclasses (json / binascii /
    unicode) so they could be matched by ``except ValueError`` alone.
    Two of them (``KeyError``, ``TypeError``) are **not** ``ValueError``
    subclasses, so a "simplify to ``except ValueError``" refactor
    would silently drop those arms -- a contract regression that this
    pre-flight pins as ground truth before Parts B / D exercise it.
    """
    assert issubclass(json.JSONDecodeError, ValueError), (
        "preflight: json.JSONDecodeError must be a ValueError subclass "
        "(per stdlib RFC). If Python ever changes this, the route's "
        "explicit listing of json.JSONDecodeError becomes load-bearing."
    )
    assert issubclass(binascii.Error, ValueError), (
        "preflight: binascii.Error must be a ValueError subclass "
        "(per stdlib). The explicit listing in the catch tuple is "
        "belt-and-suspenders for code-readers."
    )
    assert issubclass(UnicodeDecodeError, ValueError), (
        "preflight: UnicodeDecodeError must be a ValueError subclass "
        "(via UnicodeError -> ValueError). Same belt-and-suspenders "
        "reasoning."
    )
    assert not issubclass(KeyError, ValueError), (
        "preflight: KeyError is NOT a ValueError subclass. A refactor "
        "to ``except ValueError`` would silently 500 on missing-key "
        "cursors. Part D D4 pins the 422 contract for this arm."
    )
    assert not issubclass(TypeError, ValueError), (
        "preflight: TypeError is NOT a ValueError subclass. A refactor "
        "to ``except ValueError`` would silently 500 on non-dict-JSON "
        "cursors. Part D D4 pins the 422 contract for this arm."
    )


# -- Part A -- base64 / UTF-8 / JSON parse-layer errors (5 axes) ---------------


def test_part_a_decode_layer_errors_5_axis() -> None:
    """Pin base64 / UTF-8 / JSON-parse layer error classes (5 axes).

    Five axes pin the three exception classes raised by the FIRST
    three statements of ``_decode_run_list_cursor`` (b64 decode,
    ``.decode()``, ``json.loads``). The JSON-parse arm needs three
    sub-axes (A3 / A4 / A5) because the parser raises
    ``json.JSONDecodeError`` for three distinct upstream failures:
    empty input, valid-UTF-8 garbage, and structurally-malformed JSON
    -- each of which a refactor might handle differently (e.g. a
    "treat empty as missing-cursor" shortcut would mask A3 only).
    """
    with pytest.raises(binascii.Error) as exc_a1:
        _decode_run_list_cursor("a")
    assert "data characters" in str(exc_a1.value) or "Invalid base64" in str(exc_a1.value), (
        f"A1: single-char cursor must raise ``binascii.Error`` from "
        f"``urlsafe_b64decode('a===')`` (per CPython's "
        f"``binascii._b64decode_impl`` length check: 1 data char "
        f"cannot be 1-more-than-multiple-of-4). A refactor that "
        f"pre-validated cursor length would shift this to a different "
        f"class. Got message: {str(exc_a1.value)!r}"
    )
    for single in ("a", "X", "z"):
        with pytest.raises(binascii.Error):
            _decode_run_list_cursor(single)

    non_utf8_cursor = _encode_for_cursor(b"\xff\xfe\xfd")
    with pytest.raises(UnicodeDecodeError) as exc_a2:
        _decode_run_list_cursor(non_utf8_cursor)
    assert exc_a2.value.encoding == "utf-8", (
        f"A2: UnicodeDecodeError must specifically be a UTF-8 decode "
        f"error -- a refactor that switched to ``raw.decode('latin-1')`` "
        f"would silently accept ``\\xff`` and proceed to ``json.loads`` "
        f"(producing a different JSONDecodeError instead). Got "
        f"encoding={exc_a2.value.encoding!r}"
    )

    cursor_decoding_to_empty = "="
    with pytest.raises(json.JSONDecodeError) as exc_a3:
        _decode_run_list_cursor(cursor_decoding_to_empty)
    assert "line 1 column 1" in str(exc_a3.value), (
        f"A3: b64 of empty bytes -> ``json.loads('')`` -> "
        f"``json.JSONDecodeError`` at column 1. Pins that an empty "
        f"JSON document is rejected (a refactor that fell back to "
        f"``json.loads(raw.decode() or 'null')`` would change this). "
        f"Got message: {str(exc_a3.value)!r}"
    )

    non_json_text_cursor = _encode_for_cursor(b"hello not json")
    with pytest.raises(json.JSONDecodeError) as exc_a4:
        _decode_run_list_cursor(non_json_text_cursor)
    a4_msg = str(exc_a4.value)
    assert "Expecting value" in a4_msg, (
        f"A4: valid-UTF-8 non-JSON garbage -> ``json.loads`` raises "
        f"``JSONDecodeError('Expecting value')``. Distinct from A3 "
        f"(empty) because a refactor that handled empty-input "
        f"specially could still hit this arm. Got: {a4_msg!r}"
    )

    malformed_json_payloads = [
        b"{incomplete",
        b"{,}",
        b"[",
    ]
    for payload in malformed_json_payloads:
        cursor = _encode_for_cursor(payload)
        with pytest.raises(json.JSONDecodeError):
            _decode_run_list_cursor(cursor)


# -- Part B -- JSON-to-dict structural errors (5 axes) -------------------------


def test_part_b_json_non_dict_typeerror_and_missing_key_keyerror_5_axis() -> None:
    """Pin ``d["s"]`` / ``d["r"]`` bracket-access contract (5 axes).

    Once ``json.loads`` returns successfully, ``d`` may be ANY JSON
    type, not just a dict. The helper performs ``d["s"]`` immediately
    -- which raises ``TypeError`` on non-dict ``d`` and ``KeyError``
    on a dict missing the key. Five axes pin both classes across the
    four non-dict JSON types plus three missing-key shapes.

    KEY DIVERGENCE: ``TypeError`` and ``KeyError`` are NOT ``ValueError``
    subclasses. A refactor that simplified the route catch tuple to
    ``except ValueError`` would silently 500 on every one of these
    inputs. Part D D4 pins the route 422 mapping for both arms.
    """
    cursor_b1_int = _encode_for_cursor(b"5")
    with pytest.raises(TypeError) as exc_b1:
        _decode_run_list_cursor(cursor_b1_int)
    assert "subscriptable" in str(exc_b1.value), (
        f"B1: JSON parses to ``int`` -> ``5['s']`` -> "
        f"``TypeError: 'int' object is not subscriptable``. A refactor "
        f"using ``d.get('s')`` would silently produce ``int(None)`` "
        f"-> TypeError (different message). Got: {str(exc_b1.value)!r}"
    )

    cursor_b2_null = _encode_for_cursor(b"null")
    with pytest.raises(TypeError) as exc_b2:
        _decode_run_list_cursor(cursor_b2_null)
    assert "NoneType" in str(exc_b2.value), (
        f"B2: JSON parses to ``None`` -> ``None['s']`` -> "
        f"``TypeError: 'NoneType' object is not subscriptable``. "
        f"Got: {str(exc_b2.value)!r}"
    )

    cursor_b3_list = _encode_for_cursor(b"[1, 2, 3]")
    with pytest.raises(TypeError) as exc_b3:
        _decode_run_list_cursor(cursor_b3_list)
    b3_msg = str(exc_b3.value)
    assert "list indices" in b3_msg or "integers or slices" in b3_msg, (
        f"B3: JSON parses to ``list`` -> ``[1, 2, 3]['s']`` -> "
        f"``TypeError: list indices must be integers or slices, not str``. "
        f"Distinct error MESSAGE from B1 / B2 even though same CLASS -- "
        f"pins that the route catch doesn't depend on message content. "
        f"Got: {b3_msg!r}"
    )

    cursor_b4_str = _encode_for_cursor(b'"plain_string"')
    with pytest.raises(TypeError) as exc_b4:
        _decode_run_list_cursor(cursor_b4_str)
    assert "string indices" in str(exc_b4.value), (
        f"B4: JSON parses to ``str`` -> ``'plain_string'['s']`` -> "
        f"``TypeError: string indices must be integers``. Pins that "
        f"even though ``str`` is iterable / indexable, str-indexing "
        f"with a str-key still raises ``TypeError`` (NOT silently "
        f"returns a character). Got: {str(exc_b4.value)!r}"
    )

    missing_key_payloads: list[tuple[bytes, str]] = [
        (b"{}", "s"),
        (b'{"s": 1}', "r"),
        (b'{"r": "%s"}' % _SAMPLE_UUID_STR.encode(), "s"),
    ]
    for payload, expected_missing_key in missing_key_payloads:
        cursor = _encode_for_cursor(payload)
        with pytest.raises(KeyError) as exc_b5:
            _decode_run_list_cursor(cursor)
        assert exc_b5.value.args == (expected_missing_key,), (
            f"B5: missing-key dict {payload!r} must raise "
            f"``KeyError({expected_missing_key!r})``. Pins the "
            f"bracket-access contract: a refactor to "
            f"``d.get('s')`` / ``d.get('r')`` would silently produce "
            f"``int(None)`` -> TypeError instead -- a different "
            f"exception class. Got args: {exc_b5.value.args!r}"
        )


# -- Part C -- field-coercion errors on a valid dict (5 axes) ------------------


def test_part_c_field_coercion_errors_5_axis() -> None:
    """Pin ``int(d["s"])`` / ``UUID(str(d["r"]))`` field-coercion errors (5 axes).

    With ``d`` a valid dict carrying both ``"s"`` and ``"r"`` keys,
    the FINAL line of the helper performs two explicit coercions. Each
    can fail in distinct ways -- five axes pin both classes per
    field and the ``str(...)`` wrapping behaviour around ``UUID``.
    """
    cursor_c1 = _encode_for_cursor(
        b'{"s": "abc", "r": "%s"}' % _SAMPLE_UUID_STR.encode()
    )
    with pytest.raises(ValueError) as exc_c1:
        _decode_run_list_cursor(cursor_c1)
    assert "invalid literal for int" in str(exc_c1.value), (
        f"C1: ``int('abc')`` must raise ``ValueError`` with the "
        f"stdlib's ``invalid literal for int() with base 10`` "
        f"message. A refactor that wrapped coercion in a custom "
        f"``CursorCoercionError`` would change the class -- breaking "
        f"the route catch tuple's ``ValueError`` arm match. "
        f"Got: {str(exc_c1.value)!r}"
    )
    assert not isinstance(exc_c1.value, TypeError), (
        "C1 KEY DIVERGENCE: a STRING value raises ``ValueError`` from "
        "``int(...)``, NOT ``TypeError``. C2 pins the opposite class "
        "for a LIST value -- same field, different exception class."
    )

    cursor_c2 = _encode_for_cursor(
        b'{"s": [1, 2], "r": "%s"}' % _SAMPLE_UUID_STR.encode()
    )
    with pytest.raises(TypeError) as exc_c2:
        _decode_run_list_cursor(cursor_c2)
    c2_msg = str(exc_c2.value)
    assert "int()" in c2_msg or "non-string" in c2_msg or "list" in c2_msg, (
        f"C2 KEY DIVERGENCE: ``int([1, 2])`` raises ``TypeError`` "
        f"(NOT ``ValueError``). Same field as C1, DIFFERENT exception "
        f"class depending on value type. A refactor that wrapped "
        f"coercion in ``except (ValueError, TypeError)`` would mask "
        f"this distinction. Got: {c2_msg!r}"
    )
    assert not isinstance(exc_c2.value, ValueError), (
        "C2: TypeError is NOT a ValueError subclass -- this is the "
        "reason the route catch tuple lists TypeError explicitly."
    )

    cursor_c3 = _encode_for_cursor(b'{"s": 1, "r": "not-a-uuid"}')
    with pytest.raises(ValueError) as exc_c3:
        _decode_run_list_cursor(cursor_c3)
    assert "badly formed" in str(exc_c3.value) or "UUID" in str(exc_c3.value), (
        f"C3: ``UUID('not-a-uuid')`` must raise ``ValueError`` "
        f"(``badly formed hexadecimal UUID string``). Pins the UUID "
        f"validation arm distinct from the ``int(...)`` arm above. "
        f"Got: {str(exc_c3.value)!r}"
    )

    cursor_c4 = _encode_for_cursor(b'{"s": 1, "r": 5}')
    with pytest.raises(ValueError) as exc_c4:
        _decode_run_list_cursor(cursor_c4)
    assert not isinstance(exc_c4.value, TypeError), (
        f"C4 KEY DIVERGENCE: ``str(5) == '5'`` so ``UUID(str(5))`` is "
        f"``UUID('5')`` which raises ``ValueError`` (NOT ``TypeError`` "
        f"from ``UUID(5)`` directly). The ``str(...)`` wrapper around "
        f"``d['r']`` is LOAD-BEARING -- a refactor that dropped it "
        f"(``UUID(d['r'])``) would change this to ``TypeError`` and "
        f"BOTH classes are in the route catch tuple so the 422 status "
        f"would survive, but the EXCEPTION CLASS in the chain would "
        f"flip. Got: {type(exc_c4.value).__name__}: {str(exc_c4.value)!r}"
    )

    cursor_c5 = _encode_for_cursor(b'{"s": 1, "r": null}')
    with pytest.raises(ValueError) as exc_c5:
        _decode_run_list_cursor(cursor_c5)
    assert not isinstance(exc_c5.value, TypeError), (
        f"C5 KEY DIVERGENCE: ``str(None) == 'None'`` (Python builtin "
        f"behaviour, NOT an exception) so ``UUID(str(None))`` is "
        f"``UUID('None')`` which raises ``ValueError``. A refactor to "
        f"``UUID(d['r'])`` would raise ``TypeError`` from ``UUID(None)`` "
        f"instead. Pins that the ``str(...)`` wrapper converts ``None`` "
        f"to the LITERAL STRING ``'None'`` rather than short-circuiting. "
        f"Got: {type(exc_c5.value).__name__}: {str(exc_c5.value)!r}"
    )


# -- Part D -- route-layer ``invalid_cursor`` 422 integration matrix (5 axes) --


def test_part_d_route_layer_invalid_cursor_422_5_axis(client: TestClient) -> None:
    """Pin ``GET /v1/runs`` route-layer ``invalid_cursor`` 422 mapping (5 axes).

    Each axis exercises a DIFFERENT exception class from the
    [runs.py:466-481](packages/nimbusware_api/routes/runs.py) catch tuple
    by crafting a cursor that triggers it inside
    ``_decode_run_list_cursor``. The empty-cursor short-circuit axis
    (D5) pins the route's ``use_cursor`` guard at line 449 that
    short-circuits BEFORE the helper is ever called.

    KEY DIVERGENCES pinned here:

    * D1 pins the FULL problem-JSON shape per
      [packages/nimbusware_api/errors.py:8-18](packages/nimbusware_api/errors.py):
      ``code`` / ``message`` / ``details.reason`` -- a refactor that
      changed the ``code`` literal would break clients matching on it.
    * D4 covers the TWO non-ValueError-subclass arms (``KeyError`` +
      ``TypeError``) in ONE axis: a "simplify to ``except ValueError``"
      refactor would 500 on these specifically.
    * D5 pins that empty-cursor inputs are NOT 422 (they're 200) --
      distinct from malformed-cursor inputs.
    """
    r_d1 = client.get("/v1/runs", params={"cursor": "a", "limit": 5})
    assert r_d1.status_code == 422, (
        f"D1: single-char cursor must yield 422 (binascii.Error path); "
        f"got {r_d1.status_code} body={r_d1.text!r}"
    )
    body_d1 = r_d1.json()
    assert body_d1.get("code") == "invalid_cursor", (
        f"D1: problem ``code`` must be the exact literal "
        f"``invalid_cursor`` (clients pin this string). Got: {body_d1!r}"
    )
    assert body_d1.get("message") == "cursor is not a valid keyset token", (
        f"D1: problem ``message`` must be the exact literal at "
        f"[runs.py:478](packages/nimbusware_api/routes/runs.py). Got: "
        f"{body_d1.get('message')!r}"
    )
    details_d1 = body_d1.get("details") or {}
    assert isinstance(details_d1, dict) and "reason" in details_d1, (
        f"D1: ``details.reason`` must be present (carries ``str(exc)`` "
        f"for operator-visible diagnostics per [runs.py:479]"
        f"(packages/nimbusware_api/routes/runs.py)). Got details: "
        f"{details_d1!r}"
    )
    reason_d1 = details_d1["reason"]
    assert isinstance(reason_d1, str) and reason_d1.strip() != "", (
        f"D1: ``details.reason`` must be a non-empty string (it's "
        f"``str(exc)`` where ``exc`` is the helper exception). Got: "
        f"{reason_d1!r}"
    )

    cursor_d2 = base64.urlsafe_b64encode(b"\xff\xfe\xfd").decode().rstrip("=")
    r_d2 = client.get("/v1/runs", params={"cursor": cursor_d2, "limit": 5})
    assert r_d2.status_code == 422, (
        f"D2: b64-of-non-UTF-8 cursor must yield 422 "
        f"(UnicodeDecodeError path); got {r_d2.status_code} "
        f"body={r_d2.text!r}"
    )
    assert r_d2.json().get("code") == "invalid_cursor", (
        f"D2: code must be ``invalid_cursor``; got {r_d2.json()!r}"
    )

    cursor_d3 = base64.urlsafe_b64encode(b"not_json").decode().rstrip("=")
    r_d3 = client.get("/v1/runs", params={"cursor": cursor_d3, "limit": 5})
    assert r_d3.status_code == 422, (
        f"D3: b64-of-non-JSON cursor must yield 422 "
        f"(json.JSONDecodeError path); got {r_d3.status_code} "
        f"body={r_d3.text!r}"
    )
    assert r_d3.json().get("code") == "invalid_cursor", (
        f"D3: code must be ``invalid_cursor``; got {r_d3.json()!r}"
    )

    cursor_d4_keyerror = base64.urlsafe_b64encode(b"{}").decode().rstrip("=")
    r_d4_key = client.get(
        "/v1/runs", params={"cursor": cursor_d4_keyerror, "limit": 5}
    )
    assert r_d4_key.status_code == 422, (
        f"D4 KEY DIVERGENCE (KeyError arm): cursor decoding to "
        f"``{{}}`` must yield 422 (KeyError is NOT a ValueError "
        f"subclass; its inclusion in the catch tuple is the ONLY "
        f"thing preventing a 500 here). Got {r_d4_key.status_code} "
        f"body={r_d4_key.text!r}"
    )
    assert r_d4_key.json().get("code") == "invalid_cursor", (
        f"D4 (KeyError): code must be ``invalid_cursor``; got "
        f"{r_d4_key.json()!r}"
    )

    cursor_d4_typeerror = base64.urlsafe_b64encode(b"5").decode().rstrip("=")
    r_d4_type = client.get(
        "/v1/runs", params={"cursor": cursor_d4_typeerror, "limit": 5}
    )
    assert r_d4_type.status_code == 422, (
        f"D4 KEY DIVERGENCE (TypeError arm): cursor decoding to "
        f"``5`` must yield 422 (TypeError is NOT a ValueError "
        f"subclass). Got {r_d4_type.status_code} "
        f"body={r_d4_type.text!r}"
    )
    assert r_d4_type.json().get("code") == "invalid_cursor", (
        f"D4 (TypeError): code must be ``invalid_cursor``; got "
        f"{r_d4_type.json()!r}"
    )

    r_d5_empty = client.get("/v1/runs", params={"cursor": "", "limit": 5})
    assert r_d5_empty.status_code == 200, (
        f"D5a: empty cursor (``cursor=``) must short-circuit BEFORE "
        f"the helper at [runs.py:449](packages/nimbusware_api/routes/runs.py) "
        f"and return 200 (NOT 422). A refactor that dropped the "
        f"``str(cursor).strip() != ''`` check would call the helper "
        f"on ``''``, which would raise ``binascii.Error`` from "
        f"``urlsafe_b64decode('')`` -- wait, actually empty decodes "
        f"to ``b''`` so it'd then JSONDecodeError -- and shift this "
        f"to 422. Got {r_d5_empty.status_code} body={r_d5_empty.text!r}"
    )

    r_d5_omitted = client.get("/v1/runs", params={"limit": 5})
    assert r_d5_omitted.status_code == 200, (
        f"D5b: omitted cursor must yield 200 (``cursor is None`` "
        f"branch of the ``use_cursor`` guard). Got "
        f"{r_d5_omitted.status_code} body={r_d5_omitted.text!r}"
    )

    r_d5_whitespace = client.get("/v1/runs", params={"cursor": "   ", "limit": 5})
    assert r_d5_whitespace.status_code == 200, (
        f"D5c: whitespace-only cursor (``cursor=   ``) must yield 200 "
        f"(``str(cursor).strip() != ''`` is False). Pins that the "
        f"guard uses ``.strip()`` -- a refactor that dropped strip "
        f"would treat whitespace as a real cursor and 422 it. Got "
        f"{r_d5_whitespace.status_code} body={r_d5_whitespace.text!r}"
    )
