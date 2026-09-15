"""Interfaz de línea de comandos (CLI) para Forcepoint SMC IP Search.

Permite ejecutar búsquedas de direcciones IP y detección de duplicados
tanto de forma interactiva a través de un menú de consola, como mediante
parámetros directos de línea de comandos para automatización y scripts.
"""

from __future__ import annotations

import argparse
import getpass
import logging
import os
import sys

from dotenv import load_dotenv
from smc.api.exceptions import ElementNotFound, SMCConnectionError

from forcepoint_smc_ip_search.duplicates import check_duplicates_in_group
from forcepoint_smc_ip_search.search import search_in_group
from forcepoint_smc_ip_search.smc_client import SMCClient

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construye y configura el analizador de argumentos de línea de comandos.

    Returns:
        Instancia configurada de `argparse.ArgumentParser`.
    """
    parser = argparse.ArgumentParser(
        prog="smc-ip-tool",
        description=(
            "Herramienta CLI para búsqueda de direcciones IP y detección de "
            "duplicados en Forcepoint SMC (Stonesoft Management Center)."
        ),
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="URL o dirección IP del SMC (o variable SMC_URL).",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="API Key para autenticación en SMC (o variable SMC_API_KEY).",
    )
    parser.add_argument(
        "--group",
        type=str,
        default=None,
        help="Nombre del grupo en SMC a consultar (o variable SMC_GROUP).",
    )
    parser.add_argument(
        "--search",
        type=str,
        default=None,
        metavar="IP",
        help="Ejecuta directamente la búsqueda de la IP especificada sin menú interactivo.",
    )
    parser.add_argument(
        "--duplicates",
        action="store_true",
        help="Ejecuta directamente la revisión de duplicados sin menú interactivo.",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        default=False,
        help="Activa la verificación de certificados SSL (por defecto es False).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Activa el modo de depuración con información detallada de elementos inspeccionados.",
    )
    return parser


def run_interactive_menu(group_name: str, debug: bool = False) -> None:
    """Ejecuta el menú interactivo principal para el usuario en consola.

    Args:
        group_name: Nombre del grupo validado en el SMC.
        debug: Indicador de modo depuración.
    """
    while True:
        print("\n================== MENÚ PRINCIPAL ==================")
        print("1. Buscar una dirección IP específica dentro del grupo")
        print("2. Revisar IPs duplicadas dentro de las listas de IP del grupo")
        print("3. Salir")
        opcion = input("Selecciona una opción (1-3): ").strip()

        if opcion == "1":
            target_ip = input("Introduce la dirección IP que deseas buscar: ").strip()
            if not target_ip:
                print("[ERROR] La dirección IP no puede estar vacía.")
                continue

            print(f"\nIniciando búsqueda de la IP '{target_ip}' dentro de '{group_name}'...")
            found = search_in_group(group_name, target_ip, debug=debug)

            if found:
                print(
                    f"\n[RESULTADO POSITIVO] La IP {target_ip} SÍ está utilizada dentro "
                    f"del grupo '{group_name}' (o sus subelementos/listas)."
                )
            else:
                print(
                    f"\n[RESULTADO NEGATIVO] La IP {target_ip} NO se encuentra en el "
                    f"grupo '{group_name}'."
                )

        elif opcion == "2":
            check_duplicates_in_group(group_name, debug=debug)

        elif opcion == "3":
            print("Saliendo del programa...")
            break
        else:
            print("[ERROR] Opción no válida. Por favor, selecciona 1, 2 o 3.")


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada principal para la aplicación CLI.

    Carga variables de entorno, procesa argumentos, inicializa la conexión SMC
    y coordina la búsqueda o análisis según las opciones proporcionadas.

    Args:
        argv: Lista opcional de argumentos de línea de comandos. Por defecto usa sys.argv[1:].

    Returns:
        Código de salida (0 para éxito, 1 para error).
    """
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    # 1. Obtener URL del SMC
    smc_url = args.url or os.getenv("SMC_URL")
    if not smc_url:
        smc_url = input(
            "Introduce la IP o URL del SMC (ej: 192.0.2.10 o https://...:8082): "
        ).strip()
    if not smc_url:
        print("[ERROR] La URL del SMC es obligatoria.")
        return 1

    # 2. Obtener API Key
    api_key = args.api_key or os.getenv("SMC_API_KEY")
    if not api_key:
        api_key = getpass.getpass("Introduce la API Key del SMC: ").strip()
    if not api_key:
        print("[ERROR] La API Key del SMC es obligatoria.")
        return 1

    # 3. Obtener Grupo
    group_name = args.group or os.getenv("SMC_GROUP")
    if not group_name:
        group_name = input("Introduce el nombre del grupo principal en el SMC: ").strip()
    if not group_name:
        print("[ERROR] El nombre del grupo es obligatorio.")
        return 1

    # 4. Verificación SSL
    env_ssl = os.getenv("SMC_SSL_VERIFY", "false").strip().lower() in ("true", "1", "yes")
    verify_ssl = args.verify_ssl or env_ssl

    client = SMCClient(url=smc_url, api_key=api_key, verify_ssl=verify_ssl)

    try:
        print(f"\nConectando a {client.url}...")
        client.login()

        try:
            client.validate_group(group_name)
            print(f"[OK] El grupo '{group_name}' ha sido validado correctamente en el SMC.")
        except ElementNotFound:
            print(f"[ERROR] El grupo '{group_name}' NO existe en el SMC.")
            return 1

        # Modo no interactivo directo
        if args.search:
            print(f"\nIniciando búsqueda directa de la IP '{args.search}' en '{group_name}'...")
            found = search_in_group(group_name, args.search, debug=args.debug)
            if found:
                print(
                    f"\n[RESULTADO POSITIVO] La IP {args.search} SÍ está utilizada dentro "
                    f"del grupo '{group_name}' (o sus subelementos/listas)."
                )
            else:
                print(
                    f"\n[RESULTADO NEGATIVO] La IP {args.search} NO se encuentra en el "
                    f"grupo '{group_name}'."
                )
            return 0

        if args.duplicates:
            check_duplicates_in_group(group_name, debug=args.debug)
            return 0

        # Modo interactivo por defecto
        run_interactive_menu(group_name, debug=args.debug)
        return 0

    except SMCConnectionError as conn_err:
        print(f"[ERROR de Conexión] No se pudo establecer conexión con el SMC: {conn_err}")
        return 1
    except KeyboardInterrupt:
        print("\n\nOperación cancelada por el usuario.")
        return 0
    except Exception as err:
        print(f"[ERROR Inesperado] {err}")
        return 1
    finally:
        client.logout()


if __name__ == "__main__":
    sys.exit(main())
