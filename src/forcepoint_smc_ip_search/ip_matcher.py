"""Módulo de validación y comparación de direcciones IP con elementos de red.

Contiene las funciones necesarias para comprobar la pertenencia de una dirección IP
(IPv4 o IPv6) a elementos de red de Forcepoint SMC (Host, Network, AddressRange, IPList)
y la normalización de entradas de red para análisis de duplicados.
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from typing import Any

from smc.elements.network import AddressRange, Host, IPList, Network


def normalize_ip_entry(entry: Any) -> str | None:
    """Normaliza una entrada de IP, subred o rango a una representación canónica.

    Args:
        entry: Entrada en formato texto o diccionario (ej: `{"value": "192.0.2.1"}`).

    Returns:
        Cadena normalizada canónica (ej: '192.0.2.1', '192.0.2.0/24', '192.0.2.10-192.0.2.20')
        o None si la entrada está vacía, es un comentario o tiene un formato no válido.

    Examples:
        >>> normalize_ip_entry(" 192.0.2.1 ")
        '192.0.2.1'
        >>> normalize_ip_entry("192.0.2.0/24")
        '192.0.2.0/24'
        >>> normalize_ip_entry("# Comentario descriptivo")
        None
    """
    if not entry:
        return None

    if isinstance(entry, dict):
        entry = entry.get("value") or (list(entry.values())[0] if entry.values() else "")

    line_str = str(entry).strip()
    if not line_str or line_str.startswith("#"):
        return None

    try:
        if "-" in line_str:
            parts = line_str.split("-")
            if len(parts) == 2:
                start = ipaddress.ip_address(parts[0].strip())
                end = ipaddress.ip_address(parts[1].strip())
                if start.version == end.version and start <= end:
                    return f"{start}-{end}"
        elif "/" in line_str:
            net = ipaddress.ip_network(line_str, strict=False)
            return str(net)
        else:
            addr = ipaddress.ip_address(line_str)
            return str(addr)
    except (ValueError, TypeError):
        return None

    return None


def check_ip_in_element(
    target_ip: str,
    element: Any,
    ip_entries: Iterable[Any] | None = None,
) -> bool:
    """Valida si una IP pertenece o coincide con un elemento de red específico.

    Soporta los siguientes tipos de elementos de Forcepoint SMC:
    - `Host`: Coincidencia exacta con la dirección configurada en el host.
    - `Network`: Pertenencia dentro del bloque de red CIDR (IPv4 o IPv6).
    - `AddressRange`: Pertenencia dentro del rango continuo de IPs (start <= IP <= end).
    - `IPList`: Inspección sobre la lista de entradas expuesta por `.iplist` o `.content`.

    Esta función es tolerante a errores: si el formato de la IP es incorrecto
    o se comparan familias de IP incompatibles (IPv4 vs IPv6), devuelve False
    sin propagar excepciones no deseadas.

    Args:
        target_ip: Cadena con la dirección IP a comprobar (ej: '192.0.2.45').
        element: Objeto elemento de red de Forcepoint SMC.
        ip_entries: Entradas opcionales pre-extraídas si el elemento es una IPList.

    Returns:
        True si la IP objetivo coincide o está contenida en el elemento; False en caso contrario.

    Examples:
        >>> check_ip_in_element("192.0.2.1", host_obj)
        True
        >>> check_ip_in_element("192.0.2.99", network_obj)
        True
    """
    try:
        target_obj = ipaddress.ip_address(target_ip.strip())
    except (ValueError, AttributeError):
        return False

    try:
        if isinstance(element, Host):
            addr = ipaddress.ip_address(getattr(element, "address", ""))
            return addr == target_obj

        if isinstance(element, Network):
            net = ipaddress.ip_network(getattr(element, "network_value", ""), strict=False)
            return target_obj in net

        if isinstance(element, AddressRange):
            raw_range = getattr(element, "address_range", "")
            parts = str(raw_range).split("-")
            if len(parts) == 2:
                start = ipaddress.ip_address(parts[0].strip())
                end = ipaddress.ip_address(parts[1].strip())
                if start.version == target_obj.version == end.version:
                    return start <= target_obj <= end
            return False

        is_iplist = isinstance(element, IPList) or type(element).__name__ == "IPList"
        if is_iplist:
            if ip_entries is None:
                ip_entries = []
                try:
                    if hasattr(element, "iplist"):
                        ip_entries = element.iplist
                except Exception:
                    pass
                if not ip_entries:
                    ip_entries = getattr(element, "content", [])

            for line in ip_entries:
                if not line:
                    continue
                if isinstance(line, dict):
                    line = line.get("value") or (list(line.values())[0] if line.values() else "")
                line_str = str(line).strip()

                if not line_str or line_str.startswith("#"):
                    continue

                try:
                    if "-" in line_str:
                        subparts = line_str.split("-")
                        if len(subparts) == 2:
                            start = ipaddress.ip_address(subparts[0].strip())
                            end = ipaddress.ip_address(subparts[1].strip())
                            if start.version == target_obj.version == end.version:
                                if start <= target_obj <= end:
                                    return True
                    elif "/" in line_str:
                        net = ipaddress.ip_network(line_str, strict=False)
                        if target_obj in net:
                            return True
                    else:
                        addr = ipaddress.ip_address(line_str)
                        if addr == target_obj:
                            return True
                except (ValueError, TypeError):
                    continue

    except (ValueError, TypeError):
        return False

    return False
