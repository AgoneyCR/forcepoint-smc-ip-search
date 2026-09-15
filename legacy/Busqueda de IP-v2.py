#!/usr/bin/env python3

import getpass
import ipaddress
import logging

import urllib3
from smc import session
from smc.api.exceptions import ElementNotFound, SMCConnectionError
from smc.elements.group import Group
from smc.elements.network import AddressRange, Host, IPList, Network

# Configuración de modo debug temporal
DEBUG = False

# Configuración de logging y desactivación de advertencias SSL
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def check_ip_in_element(target_ip, element, ip_entries=None):
  """Valida si una IP pertenece o coincide con un elemento de red específico."""
  try:
    target_obj = ipaddress.ip_address(target_ip)
  except ValueError:
    return False

  try:
    if isinstance(element, Host):
      addr = ipaddress.ip_address(element.address)
      return addr == target_obj
    elif isinstance(element, Network):
      net = ipaddress.ip_network(element.network_value, strict=False)
      return target_obj in net
    elif isinstance(element, AddressRange):
      parts = getattr(element, "address_range", "").split("-")
      if len(parts) == 2:
        start = ipaddress.ip_address(parts[0].strip())
        end = ipaddress.ip_address(parts[1].strip())
        return start <= target_obj <= end
    elif isinstance(element, IPList) or type(element).__name__ == "IPList":
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
          line = line.get("value") or list(line.values())[0]
        line = str(line).strip()

        if not line or line.startswith("#"):
          continue
        if "-" in line:
          subparts = line.split("-")
          if len(subparts) == 2:
            start = ipaddress.ip_address(subparts[0].strip())
            end = ipaddress.ip_address(subparts[1].strip())
            if start <= target_obj <= end:
              return True
        elif "/" in line:
          net = ipaddress.ip_network(line, strict=False)
          if target_obj in net:
            return True
        else:
          addr = ipaddress.ip_address(line)
          if addr == target_obj:
            return True
  except (ValueError, TypeError):
    # Captura errores de formato o mezcla de IPv4/IPv6 (TypeError)
    return False

  return False


def search_in_group(group_name, target_ip, visited=None):
  """Busca recursivamente la IP dentro de un grupo, subgrupos y elementos."""
  if visited is None:
    visited = set()

  if group_name in visited:
    return False
  visited.add(group_name)

  try:
    group = Group.get(group_name)
  except ElementNotFound:
    return False

  print(f"[*] Inspeccionando grupo: {group_name}")
  members = group.obtain_members()

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

    if DEBUG:
      member_name = getattr(member, "name", "Desconocido")
      print(
          f"    [DEBUG] Miembro: {member_name} | Tipo real:"
          f" {type(member).__name__}"
      )
      if is_iplist:
        print(f"    [DEBUG] IPList con {len(ip_entries)} entradas:")
        for entry in ip_entries:
          print(f"      - {repr(entry)}")

    if isinstance(member, Group):
      # Búsqueda recursiva en subgrupos
      if search_in_group(member.name, target_ip, visited):
        print(f"  -> Encontrado en subgrupo anidado: {member.name}")
        return True
    else:
      if check_ip_in_element(target_ip, member, ip_entries=ip_entries):
        print(
            f"  -> Coincidencia en elemento:"
            f" {getattr(member, 'name', 'Desconocido')} [Tipo:"
            f" {type(member).__name__}]"
        )
        return True

  return False


def collect_duplicates_recursive(
    group_name, visited=None, global_ip_map=None, internal_dups_summary=None
):
  """Recorre recursivamente el grupo, recopila duplicados internos por lista

  acumulándolos en un diccionario y alimenta global_ip_map para cruces.
  """
  if visited is None:
    visited = set()
  if global_ip_map is None:
    global_ip_map = {}
  if internal_dups_summary is None:
    internal_dups_summary = {}

  if group_name in visited:
    return global_ip_map, internal_dups_summary
  visited.add(group_name)

  try:
    group = Group.get(group_name)
  except ElementNotFound:
    print(f"[ERROR] El grupo '{group_name}' no existe.")
    return global_ip_map, internal_dups_summary

  print(f"[*] Analizando grupo: {group_name}")
  members = group.obtain_members()

  for member in members:
    if isinstance(member, Group):
      collect_duplicates_recursive(
          member.name, visited, global_ip_map, internal_dups_summary
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

      seen_in_this_list = set()
      internal_dups = set()

      for line in ip_entries:
        if not line:
          continue
        if isinstance(line, dict):
          line = line.get("value") or list(line.values())[0]
        line_str = str(line).strip()

        if not line_str or line_str.startswith("#"):
          continue

        normalized_entry = None
        try:
          if "-" in line_str:
            parts = line_str.split("-")
            if len(parts) == 2:
              start = ipaddress.ip_address(parts[0].strip())
              end = ipaddress.ip_address(parts[1].strip())
              normalized_entry = f"{start}-{end}"
          elif "/" in line_str:
            net = ipaddress.ip_network(line_str, strict=False)
            normalized_entry = str(net)
          else:
            addr = ipaddress.ip_address(line_str)
            normalized_entry = str(addr)
        except (ValueError, TypeError):
          continue

        if normalized_entry:
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
        if DEBUG:
          print(
              f"    [DEBUG] IPList '{member_name}': Detectados"
              f" {len(internal_dups)} duplicados internos acumulados."
          )
      else:
        if DEBUG:
          print(f"    [DEBUG] IPList '{member_name}': Sin duplicados internos.")

  return global_ip_map, internal_dups_summary


def check_duplicates_in_group(group_name):
  """Función principal de análisis de duplicados que muestra un único resumen final."""
  print(f"\nIniciando revisión de IPs duplicadas en el grupo '{group_name}'...")
  global_ip_map, internal_dups_summary = collect_duplicates_recursive(group_name)

  # Filtrar aquellas entradas que aparecen en más de una lista distinta
  cross_dups = {
      ip: lists for ip, lists in global_ip_map.items() if len(lists) > 1
  }

  print("\n================== RESUMEN FINAL DE DUPLICADOS ==================")

  has_findings = False

  if internal_dups_summary:
    has_findings = True
    print(
        "[!] Se han encontrado elementos duplicados internos dentro de"
        " listas individuales:"
    )
    for list_name, dups in internal_dups_summary.items():
      print(f"  - Lista '{list_name}':")
      for dup in sorted(dups):
        print(f"      * {dup}")

  if cross_dups:
    if has_findings:
      print("")
    has_findings = True
    print(
        "[!] Se han encontrado IPs/bloques repetidos entre distintas listas de"
        " IP:"
    )
    for ip, lists in cross_dups.items():
      lists_str = ", ".join(sorted(lists))
      print(f"  - Elemento '{ip}' aparece en {len(lists)} listas: [{lists_str}]")

  if not has_findings:
    print("[RESULTADO] No se han encontrado IPs duplicadas ni internas ni entre listas distintas.")

  print("=================================================================")


def main():
  # 1. Petición de datos de conexión al SMC
  raw_url = input(
      "Introduce la IP o URL del SMC (ej: 192.168.201.121 o https://...:8082): "
  ).strip()
  if not raw_url.startswith("http://") and not raw_url.startswith("https://"):
    smc_url = f"https://{raw_url}:8082"
  else:
    smc_url = raw_url

  api_key = getpass.getpass("Introduce la API Key del SMC: ").strip()
  group_name = input("Introduce el nombre del grupo principal en el SMC: ").strip()

  try:
    print(f"\nConectando a {smc_url}...")
    session.login(url=smc_url, api_key=api_key, verify=False)
    print(f"[OK] Sesión iniciada correctamente. Conectado como: {session.name}")

    # 3. Validar que existe el grupo principal
    try:
      Group.get(group_name)
      print(f"[OK] El grupo '{group_name}' ha sido validado correctamente en el SMC.")
    except ElementNotFound:
      print(f"[ERROR] El grupo '{group_name}' NO existe en el SMC.")
      return

    while True:
      print("\n================== MENÚ PRINCIPAL ==================")
      print("1. Buscar una dirección IP específica dentro del grupo")
      print("2. Revisar IPs duplicadas dentro de las listas de IP del grupo")
      print("3. Salir")
      opcion = input("Selecciona una opción (1-3): ").strip()

      if opcion == "1":
        target_ip = input("Introduce la dirección IP que deseas buscar: ").strip()
        print(
            f"\nIniciando búsqueda de la IP '{target_ip}' dentro de"
            f" '{group_name}'..."
        )
        found = search_in_group(group_name, target_ip)

        if found:
          print(
              f"\n[RESULTADO POSITIVO] La IP {target_ip} SÍ está utilizada dentro"
              f" del grupo '{group_name}' (o sus subelementos/listas)."
          )
        else:
          print(
              f"\n[RESULTADO NEGATIVO] La IP {target_ip} NO se encuentra en el"
              f" grupo '{group_name}'."
          )

      elif opcion == "2":
        check_duplicates_in_group(group_name)

      elif opcion == "3":
        print("Saliendo del programa...")
        break
      else:
        print("[ERROR] Opción no válida. Por favor, selecciona 1, 2 o 3.")

  except SMCConnectionError as conn_err:
    print(f"[ERROR de Conexión] No se pudo establecer conexión con el SMC: {conn_err}")
  except Exception as e:
    print(f"[ERROR Inesperado] {e}")
  finally:
    if session.is_active:
      session.logout()
      print("Sesión de SMC cerrada.")


if __name__ == "__main__":
    main()
