"""Módulo de detección de duplicados en listas de IP de Forcepoint SMC.

Permite analizar de manera recursiva un grupo en busca de:
1. Duplicados internos: entradas de red repetidas dentro de una misma `IPList`.
2. Duplicados cruzados: entradas de red presentes en dos o más `IPList` distintas
   pertenecientes al grupo o a sus subgrupos anidados.
"""

from __future__ import annotations

import logging
from typing import Any

from smc.api.exceptions import ElementNotFound
from smc.elements.group import Group
from smc.elements.network import IPList

from forcepoint_smc_ip_search.ip_matcher import normalize_ip_entry

logger = logging.getLogger(__name__)


def collect_duplicates_recursive(
    group_name: str,
    visited: set[str] | None = None,
    global_ip_map: dict[str, set[str]] | None = None,
    internal_dups_summary: dict[str, set[str]] | None = None,
    debug: bool = False,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Recorre recursivamente un grupo identificando duplicados internos y cruzados.

    Args:
        group_name: Nombre del grupo en Forcepoint SMC a analizar.
        visited: Conjunto opcional de nombres de grupos visitados para evitar ciclos.
        global_ip_map: Diccionario acumulativo que mapea cada entrada IP canónica
            con el conjunto de nombres de listas en las que aparece.
        internal_dups_summary: Diccionario acumulativo que mapea cada nombre de lista
            con el conjunto de entradas duplicadas en su propio contenido.
        debug: Si es True, emite mensajes de depuración detallados por consola.

    Returns:
        Tupla `(global_ip_map, internal_dups_summary)` con la información recopilada.
    """
    if visited is None:
        visited = set()
    if global_ip_map is None:
        global_ip_map = {}
    if internal_dups_summary is None:
        internal_dups_summary = {}

    clean_group_name = group_name.strip()
    if clean_group_name in visited:
        if debug:
            print(f"    [DEBUG] Grupo '{clean_group_name}' ya visitado. Omitiendo.")
        return global_ip_map, internal_dups_summary

    visited.add(clean_group_name)

    try:
        group = Group.get(clean_group_name)
    except ElementNotFound:
        print(f"[ERROR] El grupo '{clean_group_name}' no existe en el SMC.")
        return global_ip_map, internal_dups_summary

    print(f"[*] Analizando grupo: {clean_group_name}")
    try:
        members = group.obtain_members()
    except Exception as err:
        print(f"[ERROR] Error al obtener miembros del grupo '{clean_group_name}': {err}")
        return global_ip_map, internal_dups_summary

    for member in members:
        if isinstance(member, Group):
            member_group_name = getattr(member, "name", "")
            collect_duplicates_recursive(
                member_group_name,
                visited=visited,
                global_ip_map=global_ip_map,
                internal_dups_summary=internal_dups_summary,
                debug=debug,
            )
        elif isinstance(member, IPList) or type(member).__name__ == "IPList":
            member_name = getattr(member, "name", "Desconocido")
            ip_entries = None
            try:
                if hasattr(member, "iplist"):
                    ip_entries = member.iplist
            except Exception:
                pass
            if not ip_entries:
                ip_entries = getattr(member, "content", [])

            seen_in_this_list: set[str] = set()
            internal_dups: set[str] = set()

            for line in ip_entries:
                normalized_entry = normalize_ip_entry(line)
                if not normalized_entry:
                    continue

                # 1. Detección interna en la misma lista
                if normalized_entry in seen_in_this_list:
                    internal_dups.add(normalized_entry)
                else:
                    seen_in_this_list.add(normalized_entry)

                # 2. Acumulación global para cruzar entre listas distintas
                if normalized_entry not in global_ip_map:
                    global_ip_map[normalized_entry] = set()
                global_ip_map[normalized_entry].add(member_name)

            if internal_dups:
                internal_dups_summary[member_name] = internal_dups
                if debug:
                    print(
                        f"    [DEBUG] IPList '{member_name}': Detectados "
                        f"{len(internal_dups)} duplicados internos acumulados."
                    )
            else:
                if debug:
                    print(f"    [DEBUG] IPList '{member_name}': Sin duplicados internos.")

    return global_ip_map, internal_dups_summary


def check_duplicates_in_group(
    group_name: str,
    debug: bool = False,
) -> dict[str, Any]:
    """Analiza y presenta un informe completo de duplicados dentro de un grupo.

    Imprime en consola un resumen con formato legible separando:
    - Duplicados internos dentro de cada lista individual.
    - Entradas de IP/bloques repetidos entre diferentes listas.

    Args:
        group_name: Nombre del grupo principal en Forcepoint SMC.
        debug: Si es True, activa trazas de depuración adicionales.

    Returns:
        Diccionario estructurado con los resultados del análisis:
        `{"internal_duplicates": ..., "cross_duplicates": ..., "has_findings": bool}`.

    Examples:
        >>> report = check_duplicates_in_group("Mi_Grupo_Ejemplo")
        >>> print(report["has_findings"])
        False
    """
    clean_name = group_name.strip()
    print(f"\nIniciando revisión de IPs duplicadas en el grupo '{clean_name}'...")
    global_ip_map, internal_dups_summary = collect_duplicates_recursive(
        clean_name,
        debug=debug,
    )

    # Filtrar aquellas entradas que aparecen en más de una lista distinta
    cross_dups: dict[str, set[str]] = {
        ip: lists for ip, lists in global_ip_map.items() if len(lists) > 1
    }

    print("\n================== RESUMEN FINAL DE DUPLICADOS ==================")

    has_findings = False

    if internal_dups_summary:
        has_findings = True
        print("[!] Se han encontrado elementos duplicados internos dentro de listas individuales:")
        for list_name, dups in sorted(internal_dups_summary.items()):
            print(f"  - Lista '{list_name}':")
            for dup in sorted(dups):
                print(f"      * {dup}")

    if cross_dups:
        if has_findings:
            print("")
        has_findings = True
        print("[!] Se han encontrado IPs/bloques repetidos entre distintas listas de IP:")
        for ip, lists in sorted(cross_dups.items()):
            lists_str = ", ".join(sorted(lists))
            print(f"  - Elemento '{ip}' aparece en {len(lists)} listas: [{lists_str}]")

    if not has_findings:
        print(
            "[RESULTADO] No se han encontrado IPs duplicadas ni internas ni entre listas distintas."
        )

    print("=================================================================")

    return {
        "internal_duplicates": internal_dups_summary,
        "cross_duplicates": cross_dups,
        "has_findings": has_findings,
    }
