"""Normalize ``domain_allowlist`` entries at merge/freeze."""

from __future__ import annotations

from ipaddress import AddressValueError, IPv4Address, IPv6Address

import idna


def _canonical_ipv4_dotted_quad(text: str) -> str | None:
    parts = text.split(".")
    if len(parts) != 4:
        return None
    octets: list[int] = []
    for p in parts:
        if not p.isdigit():
            return None
        v = int(p, 10)
        if v > 255:
            return None
        octets.append(v)
    return ".".join(str(x) for x in octets)


def normalize_domain_allowlist_entry(entry: str) -> str:
    """Lowercase hostnames; IDN → punycode; canonicalize IPv4; compress IPv6 (strip zone id).

    ASCII or punycode hostnames may use suffix form with a leading dot (e.g. ``.pypi.org``).
    Scheme, port, path, and userinfo are rejected for v1 hostname entries.
    """
    raw = entry.strip()
    if not raw:
        raise ValueError("empty allowlist entry")
    if "%" in raw:
        host_part, _, _zone = raw.partition("%")
        try:
            return IPv6Address(host_part.strip()).compressed
        except AddressValueError:
            raise ValueError("invalid IPv6 address with zone/scope-id") from None
    loose_v4 = _canonical_ipv4_dotted_quad(raw)
    if loose_v4 is not None:
        return str(IPv4Address(loose_v4))
    try:
        return str(IPv4Address(raw))
    except AddressValueError:
        pass
    try:
        return IPv6Address(raw).compressed
    except AddressValueError:
        pass

    leading_dot = raw.startswith(".")
    host = raw[1:] if leading_dot else raw
    if not host:
        raise ValueError("empty hostname in allowlist entry")
    if ".." in host:
        raise ValueError("empty hostname label (..) not allowed")
    if "/" in host or "@" in host or ":" in host:
        raise ValueError("scheme, port, path, or userinfo not allowed in v1 hostname entries")
    try:
        ascii_host = idna.encode(host, uts46=True, std3_rules=False).decode("ascii").lower()
    except idna.IDNAError as exc:
        msg = f"invalid hostname or IDN label: {exc}"
        raise ValueError(msg) from exc
    return f".{ascii_host}" if leading_dot else ascii_host
