"""Fixtures y mocks sintéticos para la suite de pruebas unitarias.

Proporciona fábricas de objetos mock para las clases de Forcepoint SMC
(`Host`, `Network`, `AddressRange`, `IPList` y `Group`) garantizando compatibilidad
con `isinstance` y sin requerir conexión de red ni credenciales reales.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from unittest.mock import MagicMock

import pytest
from smc.elements.group import Group
from smc.elements.network import AddressRange, Host, IPList, Network


def make_mock_host(name: str, address: str) -> MagicMock:
    """Crea un objeto simulado de tipo Host.

    Args:
        name: Nombre descriptivo del host (ej: 'Host_Servidor_01').
        address: Dirección IP del host.

    Returns:
        Mock que responde True a `isinstance(mock, Host)`.
    """
    mock = MagicMock(spec=Host)
    mock.name = name
    mock.address = address
    return mock


def make_mock_network(name: str, network_value: str) -> MagicMock:
    """Crea un objeto simulado de tipo Network.

    Args:
        name: Nombre descriptivo de la red (ej: 'Red_Interna_01').
        network_value: Bloque CIDR de la red (ej: '192.0.2.0/24').

    Returns:
        Mock que responde True a `isinstance(mock, Network)`.
    """
    mock = MagicMock(spec=Network)
    mock.name = name
    mock.network_value = network_value
    return mock


def make_mock_address_range(name: str, address_range: str) -> MagicMock:
    """Crea un objeto simulado de tipo AddressRange.

    Args:
        name: Nombre descriptivo del rango (ej: 'Rango_DHCP_01').
        address_range: Rango en formato 'inicio-fin'.

    Returns:
        Mock que responde True a `isinstance(mock, AddressRange)`.
    """
    mock = MagicMock(spec=AddressRange)
    mock.name = name
    mock.address_range = address_range
    return mock


def make_mock_iplist(
    name: str,
    entries: Iterable[Any] | None = None,
    use_content_fallback: bool = False,
) -> MagicMock:
    """Crea un objeto simulado de tipo IPList.

    Args:
        name: Nombre descriptivo de la lista (ej: 'Lista_IP_Ejemplo_A').
        entries: Lista o iterable con las entradas de la lista.
        use_content_fallback: Si es True, asigna las entradas a `.content` en vez de `.iplist`.

    Returns:
        Mock que responde True a `isinstance(mock, IPList)`.
    """
    mock = MagicMock(spec=IPList)
    mock.name = name
    entries_list = list(entries) if entries is not None else []
    if use_content_fallback:
        mock.content = entries_list
        # Simula objeto sin propiedad iplist o con excepción al acceder
        del mock.iplist
    else:
        mock.iplist = entries_list
        mock.content = entries_list
    return mock


def make_mock_group(name: str, members: list[Any] | None = None) -> MagicMock:
    """Crea un objeto simulado de tipo Group con miembros configurables.

    Args:
        name: Nombre del grupo (ej: 'Mi_Grupo_Ejemplo').
        members: Lista de elementos o subgrupos miembros.

    Returns:
        Mock que responde True a `isinstance(mock, Group)`.
    """
    mock = MagicMock(spec=Group)
    mock.name = name
    members_list = members if members is not None else []
    mock.obtain_members.return_value = members_list
    return mock


@pytest.fixture
def sample_host() -> MagicMock:
    """Fixture que devuelve un Host simulado."""
    return make_mock_host("Host_Servidor_01", "192.0.2.10")


@pytest.fixture
def sample_network() -> MagicMock:
    """Fixture que devuelve una Network simulada."""
    return make_mock_network("Red_Laboratorio_01", "198.51.100.0/24")


@pytest.fixture
def sample_address_range() -> MagicMock:
    """Fixture que devuelve un AddressRange simulado."""
    return make_mock_address_range("Rango_Servidores_01", "203.0.113.10-203.0.113.50")
