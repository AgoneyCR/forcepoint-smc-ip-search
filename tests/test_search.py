"""Pruebas unitarias para el módulo search."""

from __future__ import annotations

from unittest.mock import patch

from smc.api.exceptions import ElementNotFound

from forcepoint_smc_ip_search.search import search_in_group
from tests.conftest import (
    make_mock_address_range,
    make_mock_group,
    make_mock_host,
    make_mock_iplist,
    make_mock_network,
)


class TestSearchInGroup:
    """Pruebas de búsqueda recursiva de IPs en grupos y elementos."""

    @patch("smc.elements.group.Group.get")
    def test_search_direct_match_host(self, mock_group_get):
        host = make_mock_host("Host_Servidor_01", "192.0.2.10")
        group = make_mock_group("Mi_Grupo_Ejemplo", [host])
        mock_group_get.return_value = group

        assert search_in_group("Mi_Grupo_Ejemplo", "192.0.2.10") is True
        assert search_in_group("Mi_Grupo_Ejemplo", "192.0.2.99") is False

    @patch("smc.elements.group.Group.get")
    def test_search_direct_match_network(self, mock_group_get):
        net = make_mock_network("Red_Laboratorio_01", "198.51.100.0/24")
        group = make_mock_group("Mi_Grupo_Ejemplo", [net])
        mock_group_get.return_value = group

        assert search_in_group("Mi_Grupo_Ejemplo", "198.51.100.25") is True
        assert search_in_group("Mi_Grupo_Ejemplo", "10.0.0.1") is False

    @patch("smc.elements.group.Group.get")
    def test_search_direct_match_address_range(self, mock_group_get):
        ar = make_mock_address_range("Rango_Pool_01", "203.0.113.10-203.0.113.20")
        group = make_mock_group("Mi_Grupo_Ejemplo", [ar])
        mock_group_get.return_value = group

        assert search_in_group("Mi_Grupo_Ejemplo", "203.0.113.15") is True
        assert search_in_group("Mi_Grupo_Ejemplo", "203.0.113.50") is False

    @patch("smc.elements.group.Group.get")
    def test_search_direct_match_iplist(self, mock_group_get):
        iplist = make_mock_iplist("Lista_IP_01", ["192.0.2.1", "192.0.2.2"])
        group = make_mock_group("Mi_Grupo_Ejemplo", [iplist])
        mock_group_get.return_value = group

        assert search_in_group("Mi_Grupo_Ejemplo", "192.0.2.1") is True
        assert search_in_group("Mi_Grupo_Ejemplo", "192.0.2.3") is False

    @patch("smc.elements.group.Group.get")
    def test_search_nested_subgroup(self, mock_group_get):
        host_in_sub = make_mock_host("Host_Profundo", "192.0.2.88")
        subgroup = make_mock_group("Subgrupo_Nivel_2", [host_in_sub])

        middle_group = make_mock_group("Subgrupo_Nivel_1", [subgroup])
        root_group = make_mock_group("Grupo_Raiz", [middle_group])

        def group_resolver(name):
            if name == "Grupo_Raiz":
                return root_group
            if name == "Subgrupo_Nivel_1":
                return middle_group
            if name == "Subgrupo_Nivel_2":
                return subgroup
            raise ElementNotFound(f"Grupo {name} no encontrado")

        mock_group_get.side_effect = group_resolver

        assert search_in_group("Grupo_Raiz", "192.0.2.88", debug=True) is True
        assert search_in_group("Grupo_Raiz", "10.10.10.10", debug=False) is False

    @patch("smc.elements.group.Group.get")
    def test_search_handles_cyclic_references(self, mock_group_get):
        # Grupo_A contiene a Grupo_B, y Grupo_B contiene a Grupo_A (bucle cíclico)
        group_a = make_mock_group("Grupo_A", [])
        group_b = make_mock_group("Grupo_B", [])

        group_a.obtain_members.return_value = [group_b]
        group_b.obtain_members.return_value = [group_a]

        def group_resolver(name):
            if name == "Grupo_A":
                return group_a
            if name == "Grupo_B":
                return group_b
            raise ElementNotFound(f"Grupo {name} no encontrado")

        mock_group_get.side_effect = group_resolver

        # Debe terminar retornando False sin entrar en recursión infinita
        assert search_in_group("Grupo_A", "192.0.2.1", debug=True) is False

    @patch("smc.elements.group.Group.get")
    def test_search_group_not_found(self, mock_group_get):
        mock_group_get.side_effect = ElementNotFound("Grupo no existe")
        assert search_in_group("Grupo_Inexistente", "192.0.2.1") is False
