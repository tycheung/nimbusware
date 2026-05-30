"""_parse_content_length_header`` / ``_scraper_stage_audit_metadata`` /."""


from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import httpx
import pytest

from hermes_orchestrator.pipeline import RunOrchestrator, make_dev_orchestrator


def _resp_with_cl(value: str | None) -> httpx.Response:
    """``MagicMock(spec=httpx.Response)`` with controlled ``content-length`` header.

    Returns a mock whose ``.headers.get("content-length")`` returns ``value``
    verbatim (including ``None`` for the missing-header axis). Keeps each axis
    one-line at the call-site.
    """
    resp = MagicMock(spec=httpx.Response)
    headers = MagicMock()
    headers.get.return_value = value
    resp.headers = headers
    return resp


def test_parse_content_length_header_5_axis() -> None:
    """Pin _parse_content_length_header at pipeline.py:233-241.

    The helper resolves to one of: ``None`` (missing header), ``int(raw)``
    (valid numeric), or ``None`` again (ValueError on non-numeric). No
    semantic clamping at this layer -- bounds enforcement lives downstream
    in ``_scraper_get_with_retries`` / ``_effective_scraper_budget_bytes``.
    """
    parse = RunOrchestrator._parse_content_length_header  # noqa: SLF001

    assert parse(_resp_with_cl(None)) is None, (
        "A1: header missing -> .headers.get returns None -> early-return None "
        "(short-circuits the int() attempt)"
    )

    assert parse(_resp_with_cl("0")) == 0, (
        "A2: valid '0' -> int('0') == 0 returned; falsy but distinct from None "
        "(pins that 0 is NOT collapsed back to None via truthy check)"
    )

    assert parse(_resp_with_cl("12345")) == 12345, (
        "A3: valid positive '12345' -> int('12345') == 12345 happy path"
    )

    assert parse(_resp_with_cl("abc")) is None, (
        "A4: malformed 'abc' -> int('abc') raises ValueError -> caught -> "
        "returns None; pins the except-ValueError swallow (does NOT re-raise)"
    )

    assert parse(_resp_with_cl("-1")) == -1, (
        "A5: negative '-1' -> int('-1') == -1 returned UNCLAMPED; pins that "
        "this layer is pure-parse with no bounds enforcement (downstream "
        "callers are responsible for rejecting nonsensical sizes)"
    )


def test_scraper_stage_audit_metadata_5_axis() -> None:
    """Pin _scraper_stage_audit_metadata at pipeline.py:243-260.

    The helper builds a ``{"scraper_fetch": <inner>}`` envelope with four
    required inner keys and one optional ``content_length`` key gated by
    ``is not None`` (NOT truthy -- distinguishes 0 from None).
    """
    audit = RunOrchestrator._scraper_stage_audit_metadata  # noqa: SLF001

    out_b1 = audit("h", 200, 100, 1)
    assert out_b1 == {
        "scraper_fetch": {
            "url_host": "h",
            "http_status": 200,
            "bytes": 100,
            "attempts": 1,
        },
    }, (
        "B1: default content_length_header=None -> inner dict has exactly 4 "
        "keys (content_length omitted); pins the conditional-key contract"
    )

    out_b2 = audit("h", 200, 100, 1, content_length_header=0)
    assert out_b2["scraper_fetch"]["content_length"] == 0, (
        "B2: content_length_header=0 -> content_length=0 IS included; "
        "CRITICAL: pins `is not None` guard (NOT `if content_length_header:` "
        "truthy check which would wrongly drop the 0 case)"
    )

    out_b3 = audit("h", 200, 100, 1, content_length_header=42)
    assert out_b3["scraper_fetch"]["content_length"] == 42, (
        "B3: content_length_header=42 -> content_length=42 happy-path included"
    )

    assert set(out_b1.keys()) == {"scraper_fetch"}, (
        "B4: outer dict has exactly one key 'scraper_fetch'; pins the "
        "envelope-shape contract (no sibling keys leak from this helper)"
    )

    out_b5 = audit("example.com", 503, 99999, 4)
    assert out_b5 == {
        "scraper_fetch": {
            "url_host": "example.com",
            "http_status": 503,
            "bytes": 99999,
            "attempts": 4,
        },
    }, (
        "B5: verbatim propagation -- host -> url_host, http_status -> http_status, "
        "nbytes -> bytes, attempts_used -> attempts; pins the literal field-name "
        "mapping surface (rename-resistant guard)"
    )


def test_scraper_body_digest_and_snippet_5_axis() -> None:
    """Pin _scraper_body_digest_and_snippet at pipeline.py:262-268.

    The helper always returns the sha256 of FULL content; the
    ``body_snippet_preview`` key is gated by ``if snippet_max_bytes > 0:``
    (strict positive, not ``if snippet_max_bytes:`` truthy or ``>= 0``).
    Preview decode uses ``errors='replace'`` so invalid UTF-8 produces
    U+FFFD without raising.
    """
    digest = RunOrchestrator._scraper_body_digest_and_snippet  # noqa: SLF001

    content_c1 = b"Hello, world!"
    out_c1 = digest(content_c1, 0)
    assert out_c1["body_sha256_hex"] == hashlib.sha256(content_c1).hexdigest(), (
        "C1: body_sha256_hex equals hashlib.sha256(content).hexdigest() of "
        "FULL content (NOT the snippet); pins digest-of-full-bytes invariant"
    )

    assert "body_snippet_preview" not in out_c1, (
        "C2: snippet_max_bytes=0 -> preview key OMITTED via `> 0` strict guard; "
        "pins that 0 falls on the suppressed side of the boundary"
    )

    out_c3 = digest(b"Hello, world!", -1)
    assert "body_snippet_preview" not in out_c3, (
        "C3: snippet_max_bytes=-1 also suppresses preview; pins guard is "
        "strict `> 0` (NOT `if snippet_max_bytes:` truthy, which would still "
        "accept -1 since bool(-1) is True)"
    )

    out_c4 = digest(b"Hello, world!", 5)
    assert out_c4["body_snippet_preview"] == "Hello", (
        "C4: snippet_max_bytes=5 on b'Hello, world!' -> content[:5] = b'Hello' "
        "-> 'Hello'; pins (a) slice is content[:N] not content[:N+1] and "
        "(b) decode runs on the slice (not on full content then truncated)"
    )

    content_c5 = b"\xff\xfe\xfdgood"
    out_c5 = digest(content_c5, 10)
    assert "\ufffd" in out_c5["body_snippet_preview"], (
        "C5: invalid UTF-8 bytes 0xff/0xfe/0xfd -> errors='replace' produces "
        "U+FFFD replacement char(s); pins NO exception raised (without "
        "errors='replace' this would UnicodeDecodeError)"
    )
    assert out_c5["body_sha256_hex"] == hashlib.sha256(content_c5).hexdigest(), (
        "C5 cross-cut: digest still computed over raw bytes unaffected by "
        "decode-side errors; pins digest path is fully independent of "
        "snippet-decode path"
    )


def test_persist_scraper_response_artifact_5_axis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin _persist_scraper_response_artifact at pipeline.py:270-296.

    The helper writes ``<base>/<run_id>/url{NN:02d}_<sha256(content)[:32]>.bin``
    truncated to ``persist_cap`` bytes; returns ``{artifact_relpath (forward
    slash normalized), artifact_sha256 (sha256 of TRUNCATED blob),
    artifact_bytes_written}``. ``HERMES_SCRAPER_ARTIFACT_DIR`` overrides
    the default cache dir; ``resolve_scraper_artifact_base_dir`` is the
    seam (imported into pipeline at pipeline.py:104).
    """
    monkeypatch.setenv("HERMES_SCRAPER_ARTIFACT_DIR", str(tmp_path))
    orch, _ = make_dev_orchestrator()
    base_dir = Path(str(tmp_path)).expanduser().resolve()

    run_id_d1 = uuid4()
    content_d1 = b"x" * 10
    expected_digest_d1 = hashlib.sha256(content_d1).hexdigest()
    out_d1 = orch._persist_scraper_response_artifact(  # noqa: SLF001
        run_id_d1, 3, content_d1, 100,
    )
    expected_fname_d1 = f"url03_{expected_digest_d1[:32]}.bin"
    assert out_d1["artifact_relpath"].endswith(expected_fname_d1), (
        "D1: filename pattern 'url{NN:02d}_<digest[:32]>.bin' -- url_index=3 "
        "renders as 'url03' (pins :02d zero-pad), digest truncated to first "
        "32 hex chars (pins [:32] slice on hexdigest)"
    )

    run_id_d2 = uuid4()
    content_d2 = b"abc"
    out_d2 = orch._persist_scraper_response_artifact(  # noqa: SLF001
        run_id_d2, 0, content_d2, 100,
    )
    assert out_d2["artifact_bytes_written"] == 3, (
        "D2: content (3 bytes) under persist_cap (100) -> "
        "artifact_bytes_written == 3 (full content written, no truncation)"
    )
    on_disk_d2 = (base_dir / str(run_id_d2) / Path(out_d2["artifact_relpath"]).name).read_bytes()
    assert on_disk_d2 == b"abc", (
        "D2 cross-cut: on-disk bytes equal full content b'abc' (pins the "
        "write happens with the untruncated blob when content fits under cap)"
    )

    run_id_d3 = uuid4()
    content_d3 = b"a" * 10
    out_d3 = orch._persist_scraper_response_artifact(  # noqa: SLF001
        run_id_d3, 0, content_d3, 4,
    )
    assert out_d3["artifact_bytes_written"] == 4, (
        "D3: content (10 bytes) over persist_cap (4) -> artifact_bytes_written "
        "== 4; pins truncation at slice content[:persist_cap]"
    )
    on_disk_d3 = (base_dir / str(run_id_d3) / Path(out_d3["artifact_relpath"]).name).read_bytes()
    assert on_disk_d3 == b"aaaa", (
        "D3 cross-cut: on-disk bytes equal b'aaaa' (truncated blob), NOT the "
        "full b'aaaaaaaaaa'; pins the write happens with content[:persist_cap]"
    )

    expected_full_digest_d3 = hashlib.sha256(b"a" * 10).hexdigest()
    expected_blob_digest_d3 = hashlib.sha256(b"aaaa").hexdigest()
    assert expected_full_digest_d3 != expected_blob_digest_d3, (
        "D4 sanity: pre-image proof that the two digests differ in the "
        "truncated case (no point asserting the asymmetric contract if "
        "they happen to collide)"
    )
    assert f"_{expected_full_digest_d3[:32]}.bin" in out_d3["artifact_relpath"], (
        "D4: filename uses sha256 of FULL content (digest_full = sha256(content) "
        "at pipeline.py:283); pins which digest goes into the filename"
    )
    assert out_d3["artifact_sha256"] == expected_blob_digest_d3, (
        "D4: artifact_sha256 in returned metadata uses sha256 of TRUNCATED "
        "blob (pipeline.py:287 -- hashlib.sha256(blob).hexdigest()); pins the "
        "asymmetric dual-digest contract (filename = full; metadata = blob)"
    )

    run_id_d5 = uuid4()
    out_d5 = orch._persist_scraper_response_artifact(  # noqa: SLF001
        run_id_d5, 1, b"data", 1024,
    )
    assert "\\" not in out_d5["artifact_relpath"], (
        "D5: artifact_relpath has NO backslash separators; pins the "
        "str(rel).replace('\\\\', '/') normalization at pipeline.py:293 "
        "(cross-platform invariant -- on Windows the raw rel uses '\\\\', on "
        "POSIX it uses '/' natively; the replace makes both produce '/')"
    )
    assert out_d5["artifact_relpath"].startswith(f"{run_id_d5}/url"), (
        "D5 cross-cut: relpath begins with '<run_id>/url' (pins that rel is "
        "relative_to(base_dir) so the base_dir prefix is stripped and the "
        "run_id subdir + 'url' filename prefix are visible)"
    )
