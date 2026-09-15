"""Pruebas unitarias para el módulo duplicates."""

from __future__ import annotations

from unittest.mock import patch

from smc.api.exceptions import ElementNotFound

from forcepoint_smc_ip_search.duplicates import (
    check_duplicates_in_group,
    collect_duplicates_recursive,
)
from tests.conftest import make_mock_group, make_mock_iplist


class TestDuplicatesDetection:
    """Pruebas de detección de duplicados internos y cruzados."""

    @patch("smc.elements.group.Group.get")
    def test_internal_duplicates_in_single_list(self, mock_group_get):
        list_a = make_mock_iplist(
            "Lista_IP_A",
            [
                "192.0.2.1",
                "192.0.2.2",
                "192.0.2.1",  # Duplicado interno exacto
                "192.0.2.0/24",
                "192.0.2.5/24",  # Duplicado interno tras normalización CIDR
            ],
        )
        group = make_mock_group("Mi_Grupo_Ejemplo", [list_a])
        mock_group_get.return_value = group

        report = check_duplicates_in_group("Mi_Grupo_Ejemplo", debug=False)

        assert report["has_findings"] is True
        assert "Lista_IP_A" in report["internal_duplicates"]
        assert "192.0.2.1" in report["internal_duplicates"]["Lista_IP_A"]
        assert "192.0.2.0/24" in report["internal_duplicates"]["Lista_IP_A"]
        assert len(report["cross_duplicates"]) == 0

    @patch("smc.elements.group.Group.get")
    def test_cross_list_duplicates(self, mock_group_get):
        list_a = make_mock_iplist("Lista_IP_A", ["192.0.2.50", "192.0.2.51"])
        list_b = make_mock_iplist("Lista_IP_B", ["192.0.2.50", "198.51.100.1"])
        group = make_mock_group("Mi_Grupo_Ejemplo", [list_a, list_b])
        mock_group_get.return_value = group

        report = check_duplicates_in_group("Mi_Grupo_Ejemplo", debug=False)

        assert report["has_findings"] is True
        assert "192.0.2.50" in report["cross_duplicates"]
        assert report["cross_duplicates"]["192.0.2.50"] == {"Lista_IP_A", "Lista_IP_B"}
        assert len(report["internal_duplicates"]) == 0

    @patch("smc.elements.group.Group.get")
    def test_clean_group_no_duplicates(self, mock_group_get):
        list_a = make_mock_iplist("Lista_IP_A", ["192.0.2.1", "192.0.2.2"])
        list_b = make_mock_iplist("Lista_IP_B", ["198.51.100.1", "203.0.113.1"])
        group = make_mock_group("Mi_Grupo_Limpio", [list_a, list_b])
        mock_group_get.return_value = group

        report = check_duplicates_in_group("Mi_Grupo_Limpio", debug=False)

        assert report["has_findings"] is False
        assert len(report["internal_duplicates"]) == 0
        assert len(report["cross_duplicates"]) == 0

    @patch("smc.elements.group.Group.get")
    def test_nested_subgroups_duplicates(self, mock_group_get):
        list_in_sub = make_mock_iplist("Lista_Subgrupo", ["192.0.2.99"])
        subgroup = make_mock_group("Subgrupo_Nivel_1", [list_in_sub])

        list_in_root = make_mock_iplist("Lista_Raiz", ["192.0.2.99"])
        root_group = make_mock_group("Grupo_Raiz", [list_in_root, subgroup])

        def group_resolver(name):
            if name == "Grupo_Raiz":
                return root_group
            if name == "Subgrupo_Nivel_1":
                return subgroup
            raise ElementNotFound(f"Grupo {name} no encontrado")

        mock_group_get.side_effect = group_resolver

        report = check_duplicates_in_group("Grupo_Raiz", debug=True)

        assert report["has_findings"] is True
        assert "192.0.2.99" in report["cross_duplicates"]
        assert report["cross_duplicates"]["192.0.2.99"] == {"Lista_Raiz", "Lista_Subgrupo"}

    @patch("smc.elements.group.Group.get")
    def test_group_not_found(self, mock_group_get):
        mock_group_get.side_effect = ElementNotFound("No existe")

        global_map, internal_map = collect_duplicates_recursive("Grupo_Inexistente")
        assert global_map == {}
        assert internal_map == {}
