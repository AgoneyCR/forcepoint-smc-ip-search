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
  target_ip = input("Introduce la dirección IP que deseas buscar: ").strip()
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

    # 4. Búsqueda dentro del grupo y sus listas/elementos anidados
    print(f"\nIniciando búsqueda de la IP '{target_ip}' dentro de '{group_name}'...")
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
