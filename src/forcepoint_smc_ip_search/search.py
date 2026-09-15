"""Módulo de búsqueda recursiva de direcciones IP en grupos de Forcepoint SMC.

Permite buscar si una IP específica está contenida dentro de un grupo principal,
sus subgrupos anidados y cualquiera de sus elementos asociados (Host, Network,
AddressRange, IPList), con control de ciclos para evitar recursión infinita.
"""

from __future__ import annotations

import logging

from smc.api.exceptions import ElementNotFound
from smc.elements.group import Group
from smc.elements.network import IPList

from forcepoint_smc_ip_search.ip_matcher import check_ip_in_element

logger = logging.getLogger(__name__)


def search_in_group(
    group_name: str,
    target_ip: str,
    visited: set[str] | None = None,
    debug: bool = False,
) -> bool:
    """Busca recursivamente una dirección IP dentro de un grupo, sus subgrupos y elementos.

    Explora en profundidad los miembros del grupo mediante `obtain_members()`.
    Si encuentra un subgrupo, continúa la búsqueda recursiva. Si encuentra
    un elemento de red o una lista de IPs (`IPList`), comprueba si la IP
    objetivo está incluida en él.

    Args:
        group_name: Nombre del grupo en Forcepoint SMC a inspeccionar.
        target_ip: Dirección IP que se desea buscar (ej: '192.0.2.15').
        visited: Conjunto opcional de nombres de grupos ya explorados para evitar ciclos.
        debug: Si es True, muestra trazas detalladas de depuración sobre cada miembro
            e ítem evaluado. Por defecto es False.

    Returns:
        True si la IP está contenida en algún elemento del grupo o subgrupos; False si no.

    Examples:
        >>> search_in_group("Mi_Grupo_Ejemplo", "192.0.2.50")
        [*] Inspeccionando grupo: Mi_Grupo_Ejemplo
        ...
        True
    """
    if visited is None:
        visited = set()

    clean_group_name = group_name.strip()
    if clean_group_name in visited:
        if debug:
            print(
                f"    [DEBUG] Grupo '{clean_group_name}' ya visitado. Omitiendo para evitar ciclo."
            )
        return False

    visited.add(clean_group_name)

    try:
        group = Group.get(clean_group_name)
    except ElementNotFound:
        print(f"[ERROR] El grupo '{clean_group_name}' no existe en el SMC.")
        return False

    print(f"[*] Inspeccionando grupo: {clean_group_name}")
    try:
        members = group.obtain_members()
    except Exception as err:
        print(f"[ERROR] Error al obtener miembros del grupo '{clean_group_name}': {err}")
        return False

    for member in members:
        ip_entries = None
        is_iplist = isinstance(member, IPList) or type(member).__name__ == "IPList"

        if is_iplist:
            try:
                if hasattr(member, "iplist"):
                    ip_entries = member.iplist
            except Exception:
                pass
            if not ip_entries:
                ip_entries = getattr(member, "content", [])

        if debug:
            member_name = getattr(member, "name", "Desconocido")
            print(f"    [DEBUG] Miembro: {member_name} | Tipo real: {type(member).__name__}")
            if is_iplist:
                entries_count = len(ip_entries) if ip_entries is not None else 0
                print(f"    [DEBUG] IPList con {entries_count} entradas:")
                if ip_entries:
                    for entry in ip_entries:
                        print(f"      - {repr(entry)}")

        if isinstance(member, Group):
            member_group_name = getattr(member, "name", "")
            if search_in_group(member_group_name, target_ip, visited, debug=debug):
                print(f"  -> Encontrado en subgrupo anidado: {member_group_name}")
                return True
        else:
            if check_ip_in_element(target_ip, member, ip_entries=ip_entries):
                element_name = getattr(member, "name", "Desconocido")
                element_type = type(member).__name__
                print(f"  -> Coincidencia en elemento: {element_name} [Tipo: {element_type}]")
                return True

    return False
