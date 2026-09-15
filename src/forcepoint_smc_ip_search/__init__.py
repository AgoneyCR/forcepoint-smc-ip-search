"""Forcepoint SMC IP Search and Duplicate Detection Package.

Herramienta profesional para búsqueda de direcciones IP y detección
de duplicados en grupos y listas de elementos de Forcepoint SMC
(Stonesoft Management Center) utilizando el SDK fp-NGFW-SMC-python.
"""

from forcepoint_smc_ip_search.duplicates import (
    check_duplicates_in_group,
    collect_duplicates_recursive,
)
from forcepoint_smc_ip_search.ip_matcher import (
    check_ip_in_element,
    normalize_ip_entry,
)
from forcepoint_smc_ip_search.search import search_in_group
from forcepoint_smc_ip_search.smc_client import SMCClient

__version__ = "0.1.0"

__all__ = [
    "SMCClient",
    "check_duplicates_in_group",
    "check_ip_in_element",
    "collect_duplicates_recursive",
    "normalize_ip_entry",
    "search_in_group",
]
