"""Pruebas unitarias para el módulo ip_matcher."""

from __future__ import annotations

from forcepoint_smc_ip_search.ip_matcher import (
    check_ip_in_element,
    normalize_ip_entry,
)
from tests.conftest import (
    make_mock_address_range,
    make_mock_host,
    make_mock_iplist,
    make_mock_network,
)


class TestNormalizeIpEntry:
    """Pruebas para la función normalize_ip_entry."""

    def test_empty_or_whitespace(self):
        assert normalize_ip_entry("") is None
        assert normalize_ip_entry("   ") is None
        assert normalize_ip_entry(None) is None

    def test_comments(self):
        assert normalize_ip_entry("# Esta es una nota") is None
        assert normalize_ip_entry("  # Comentario indentado") is None

    def test_single_ipv4(self):
        assert normalize_ip_entry("192.0.2.1") == "192.0.2.1"
        assert normalize_ip_entry("  198.51.100.5  ") == "198.51.100.5"

    def test_single_ipv6(self):
        assert normalize_ip_entry("2001:db8::1") == "2001:db8::1"

    def test_cidr_ipv4(self):
        assert normalize_ip_entry("192.0.2.0/24") == "192.0.2.0/24"
        assert normalize_ip_entry("192.0.2.5/24") == "192.0.2.0/24"

    def test_cidr_ipv6(self):
        assert normalize_ip_entry("2001:db8::/32") == "2001:db8::/32"

    def test_range_ipv4(self):
        assert normalize_ip_entry("192.0.2.10 - 192.0.2.20") == "192.0.2.10-192.0.2.20"

    def test_inverted_range_returns_none(self):
        assert normalize_ip_entry("192.0.2.50 - 192.0.2.10") is None

    def test_dict_entry(self):
        assert normalize_ip_entry({"value": "192.0.2.15"}) == "192.0.2.15"
        assert normalize_ip_entry({"ip": "192.0.2.0/24"}) == "192.0.2.0/24"

    def test_invalid_string(self):
        assert normalize_ip_entry("texto_aleatorio") is None
        assert normalize_ip_entry("999.999.999.999") is None
        assert normalize_ip_entry("192.0.2.1-no_es_ip") is None


class TestCheckIpInHost:
    """Pruebas de pertenencia en objetos Host."""

    def test_exact_match_ipv4(self):
        host = make_mock_host("Host_Web_01", "192.0.2.10")
        assert check_ip_in_element("192.0.2.10", host) is True

    def test_mismatch_ipv4(self):
        host = make_mock_host("Host_Web_01", "192.0.2.10")
        assert check_ip_in_element("192.0.2.11", host) is False

    def test_exact_match_ipv6(self):
        host = make_mock_host("Host_IPv6_01", "2001:db8::10")
        assert check_ip_in_element("2001:db8::10", host) is True

    def test_ipv4_target_against_ipv6_host(self):
        host = make_mock_host("Host_IPv6_01", "2001:db8::10")
        assert check_ip_in_element("192.0.2.10", host) is False


class TestCheckIpInNetwork:
    """Pruebas de pertenencia en objetos Network."""

    def test_target_inside_subnet(self):
        net = make_mock_network("Red_Interna_01", "192.0.2.0/24")
        assert check_ip_in_element("192.0.2.50", net) is True
        assert check_ip_in_element("192.0.2.0", net) is True
        assert check_ip_in_element("192.0.2.255", net) is True

    def test_target_outside_subnet(self):
        net = make_mock_network("Red_Interna_01", "192.0.2.0/24")
        assert check_ip_in_element("192.0.3.1", net) is False

    def test_target_in_ipv6_network(self):
        net = make_mock_network("Red_IPv6_01", "2001:db8::/32")
        assert check_ip_in_element("2001:db8::abcd", net) is True
        assert check_ip_in_element("2001:db9::1", net) is False

    def test_ipv4_target_against_ipv6_network(self):
        net = make_mock_network("Red_IPv6_01", "2001:db8::/32")
        assert check_ip_in_element("192.0.2.1", net) is False


class TestCheckIpInAddressRange:
    """Pruebas de pertenencia en objetos AddressRange."""

    def test_inside_and_bounds(self):
        ar = make_mock_address_range("Rango_Pool_01", "192.0.2.10-192.0.2.50")
        assert check_ip_in_element("192.0.2.10", ar) is True
        assert check_ip_in_element("192.0.2.30", ar) is True
        assert check_ip_in_element("192.0.2.50", ar) is True

    def test_outside_bounds(self):
        ar = make_mock_address_range("Rango_Pool_01", "192.0.2.10-192.0.2.50")
        assert check_ip_in_element("192.0.2.9", ar) is False
        assert check_ip_in_element("192.0.2.51", ar) is False

    def test_ipv4_target_against_ipv6_range(self):
        ar = make_mock_address_range("Rango_IPv6_01", "2001:db8::1-2001:db8::10")
        assert check_ip_in_element("192.0.2.5", ar) is False


class TestCheckIpInIPList:
    """Pruebas de pertenencia en objetos IPList."""

    def test_mixed_entries_in_iplist(self):
        entries = [
            "# Cabecera de prueba",
            "",
            "192.0.2.1",
            "192.0.2.50-192.0.2.60",
            "198.51.100.0/24",
            {"value": "203.0.113.88"},
            "entrada_invalida_no_rompe",
        ]
        iplist = make_mock_iplist("Lista_Pruebas_01", entries)

        assert check_ip_in_element("192.0.2.1", iplist) is True
        assert check_ip_in_element("192.0.2.55", iplist) is True
        assert check_ip_in_element("198.51.100.99", iplist) is True
        assert check_ip_in_element("203.0.113.88", iplist) is True
        assert check_ip_in_element("10.0.0.1", iplist) is False

    def test_iplist_content_fallback(self):
        entries = ["192.0.2.77"]
        iplist = make_mock_iplist("Lista_Fallback_01", entries, use_content_fallback=True)
        assert check_ip_in_element("192.0.2.77", iplist) is True


class TestCheckIpMalformedTargets:
    """Pruebas con entradas de IP objetivo inválidas o corruptas."""

    def test_invalid_targets(self):
        host = make_mock_host("Host_Web_01", "192.0.2.10")
        assert check_ip_in_element("", host) is False
        assert check_ip_in_element("no_es_ip", host) is False
        assert check_ip_in_element("999.999.999.999", host) is False
        assert check_ip_in_element("192.0.2.300", host) is False
