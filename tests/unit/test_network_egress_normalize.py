"""§6.3A domain allowlist normalization (IDN / punycode, IPs, suffix form)."""
from __future__ import annotations
import pytest
from hermes_orchestrator.network_egress_normalize import normalize_domain_allowlist_entry
def test_ipv4_canonical() -> None:
    assert normalize_domain_allowlist_entry(" 192.168.001.010 ") == "192.168.1.10"
def test_ipv6_compressed_no_zone() -> None:
    assert normalize_domain_allowlist_entry("2001:db8::1") == "2001:db8::1"
def test_rejects_percent_zone() -> None:
    with pytest.raises(ValueError, match="%"):
        normalize_domain_allowlist_entry("fe80::1%eth0")
def test_ascii_lowercase() -> None:
    assert normalize_domain_allowlist_entry("Example.COM") == "example.com"
def test_suffix_leading_dot_preserved() -> None:
    assert normalize_domain_allowlist_entry(".PyPI.ORG") == ".pypi.org"
def test_idn_to_punycode() -> None:
    assert normalize_domain_allowlist_entry("münchen.de") == "xn--mnchen-3ya.de"
def test_idn_suffix_form() -> None:
    assert normalize_domain_allowlist_entry(".München.DE") == ".xn--mnchen-3ya.de"
def test_rejects_scheme_or_port() -> None:
    with pytest.raises(ValueError):
        normalize_domain_allowlist_entry("https://example.com")
    with pytest.raises(ValueError):
        normalize_domain_allowlist_entry("example.com:443")
def test_rejects_empty_label() -> None:
    with pytest.raises(ValueError, match=r"\.\."):
        normalize_domain_allowlist_entry("foo..bar")
