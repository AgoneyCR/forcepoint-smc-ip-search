# Forcepoint SMC IP Search & Duplicate Detector

[![CI](https://github.com/AgoneyCR/forcepoint-smc-ip-search/actions/workflows/ci.yml/badge.svg)](https://github.com/AgoneyCR/forcepoint-smc-ip-search/actions)
[![Python Versions](https://img.shields.io/badge/python-3.9%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

Herramienta profesional de consola y librería en Python para la **búsqueda recursiva de direcciones IP** y la **detección de duplicados** en grupos y listas de elementos en **Forcepoint SMC** (Stonesoft Management Center), desarrollada sobre el SDK oficial `fp-NGFW-SMC-python`.

---

## Características Principales

1. **Búsqueda Recursiva de IPs (`search`)**:
   - Comprueba si una dirección IP específica (IPv4 o IPv6) está contenida dentro de un grupo principal y cualquiera de sus subgrupos anidados.
   - Evalúa múltiples tipos de elementos nativos de Forcepoint SMC:
     - `Host`: Coincidencia exacta de dirección IP.
     - `Network`: Pertenencia dentro del bloque de red CIDR.
     - `AddressRange`: Pertenencia en rangos cerrados de IPs (`inicio - fin`).
     - `IPList`: Inspección sobre entradas individuales, subredes, rangos o diccionarios.
   - Algoritmo con detección y control de referencias cíclicas entre grupos.

2. **Detección Avanzada de Duplicados (`duplicates`)**:
   - **Duplicados Internos**: Identifica entradas repetidas dentro de una misma lista de IPs (`IPList`), soportando normalización canónica de IPs, subredes CIDR y rangos.
   - **Duplicados Cruzados**: Detecta IPs o bloques que aparecen duplicados en dos o más listas distintas pertenecientes al grupo o sus subgrupos.
   - Resumen estructurado y formateado en terminal.

3. **Modo CLI Híbrido**:
   - Menú interactivo guiado por consola para operadores y administradores.
   - Parámetros directos de línea de comandos (`--search`, `--duplicates`) para integración con scripts y automatizaciones.
   - Flag explícito de depuración `--debug` (`-v` / `--verbose`) para trazabilidad granular.

4. **Gestión Segura de Secretos**:
   - Soporte para variables de entorno y archivo `.env` (vía `python-dotenv`).
   - Fallback interactivo seguro con `getpass` para la API Key si no está configurada en el entorno.

---

## ⚠️ Nota Crítica sobre el SDK Oficial

> [!IMPORTANT]
> Este proyecto requiere y utiliza obligatoriamente el paquete **`fp-NGFW-SMC-python`**, mantenido activamente por Forcepoint.
>
> **NO instales el paquete legacy `smc-python`**. Aunque ambos paquetes comparten el mismo espacio de nombres de importación (`from smc import session`), la versión antigua `smc-python` no implementa la propiedad `.iplist` en los elementos de tipo `IPList` y provocará errores de ejecución (`AttributeError`).

---

## Requisitos

- **Python 3.9+** (validado en Python 3.9 y Python 3.13).
- Conectividad de red hacia el servidor **Forcepoint SMC** (habitualmente por puerto HTTPS 8082).
- Una **API Key** generada en el SMC con permisos de lectura sobre elementos de red y grupos.

---

## Instalación

1. Clona el repositorio:
   ```bash
   git clone https://github.com/AgoneyCR/forcepoint-smc-ip-search.git
   cd forcepoint-smc-ip-search
   ```

2. Crea y activa un entorno virtual:
   ```bash
   # Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate

   # Windows (PowerShell):
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Instala el paquete en modo editable:
   ```bash
   pip install --upgrade pip
   ```

   Para instalar las dependencias de desarrollo y tests:
   ```bash
   pip install -e ".[dev]"
   ```

---

## Configuración

Copia la plantilla `.env.example` para crear tu archivo `.env`:

```bash
cp .env.example .env
```

Edita `.env` con tus datos de conexión (utiliza siempre placeholders en ejemplos):

```env
# URL o IP del Forcepoint SMC
SMC_URL=https://smc.example.com:8082

# API Key generada en el SMC
SMC_API_KEY=tu_api_key_aqui

# Nombre del grupo principal en el SMC
SMC_GROUP=Mi_Grupo_Ejemplo

# Verificación de certificados SSL (true/false)
SMC_SSL_VERIFY=false
```

---

## Uso

Una vez instalado, dispones del comando de consola `smc-ip-tool`:

### 1. Modo Interactivo (Recomendado)

Ejecuta sin argumentos adicionales para abrir el menú principal:

```bash
smc-ip-tool
```

Ejemplo de flujo:
```text
Conectando a https://smc.example.com:8082...
[OK] Sesión iniciada correctamente. Conectado como: API_Client_User
[OK] El grupo 'Mi_Grupo_Ejemplo' ha sido validado correctamente en el SMC.

================== MENÚ PRINCIPAL ==================
1. Buscar una dirección IP específica dentro del grupo
2. Revisar IPs duplicadas dentro de las listas de IP del grupo
3. Salir
Selecciona una opción (1-3): 1
Introduce la dirección IP que deseas buscar: 192.0.2.45

Iniciando búsqueda de la IP '192.0.2.45' dentro de 'Mi_Grupo_Ejemplo'...
[*] Inspeccionando grupo: Mi_Grupo_Ejemplo
  -> Coincidencia en elemento: Lista_Bloqueo_01 [Tipo: IPList]

[RESULTADO POSITIVO] La IP 192.0.2.45 SÍ está utilizada dentro del grupo 'Mi_Grupo_Ejemplo'.
```

### 2. Modo Directo por Línea de Comandos

Búsqueda directa de una IP:
```bash
smc-ip-tool --search 192.0.2.45
```

Revisión directa de duplicados:
```bash
smc-ip-tool --duplicates
```

### 3. Modo Depuración (`--debug` o `-v`)

Para visualizar la traza completa de cada elemento, subgrupo y contenido de las listas inspeccionadas:

```bash
smc-ip-tool --search 192.0.2.45 --debug
```

---

## Seguridad

> [!WARNING]
> **Advertencia de Seguridad**:
> - **NUNCA subas tu archivo `.env` ni expongas tu API Key** en repositorios públicos o compartidos. El archivo `.env` está expresamente excluido en el `.gitignore`.
> - Las API Keys otorgan acceso directo a la configuración de seguridad de tu firewall. Limita los permisos de la API Key en el SMC al rol mínimo necesario (solo lectura).

> [!NOTE]
> **Certificados SSL (`verify=False`)**:
> En la mayoría de implementaciones corporativas e internas, el Forcepoint SMC utiliza certificados SSL autofirmados o emitidos por PKI internas no reconocidas por el almacén público de confianza del sistema operativo. Por esta razón, el valor predeterminado de `verify_ssl` es `False`, suprimiendo las advertencias de `urllib3.InsecureRequestWarning`. Si tu SMC cuenta con un certificado SSL emitido por una CA corporativa de confianza en tu almacén local, puedes activar la validación pasando `--verify-ssl` o estableciendo `SMC_SSL_VERIFY=true` en tu archivo `.env`.

---

## Estructura del Repositorio

```text
forcepoint-smc-ip-search/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── workflows/
│   │   └── ci.yml             # Integración Continua (Python 3.9 y 3.13)
│   └── PULL_REQUEST_TEMPLATE.md
├── src/
│   └── forcepoint_smc_ip_search/
│       ├── __init__.py        # Exportación de API pública y versión 0.1.0
│       ├── cli.py             # Entrada de consola, flag --debug y menú
│       ├── duplicates.py      # Detección de duplicados internos y cruzados
│       ├── ip_matcher.py      # Comprobación de pertenencia (Host, Network, Range, IPList)
│       ├── search.py          # Búsqueda recursiva con prevención de ciclos
│       └── smc_client.py      # Conexión, gestión de sesión y context manager
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Mocks sintéticos para el SDK de SMC
│   ├── test_cli.py            # Tests de CLI y propagación de --debug
│   ├── test_duplicates.py     # Tests de duplicados con datos genéricos
│   ├── test_ip_matcher.py     # Tests de comparación de IPs, CIDR y rangos
│   └── test_search.py         # Tests de búsqueda recursiva y ciclos
├── legacy/                    # Preservación de scripts originales (auditados)
│   ├── Busqueda de IP.py
│   └── Busqueda de IP-v2.py
├── .env.example               # Plantilla de variables de entorno sanitizada
├── .gitignore                 # Exclusión de .env, venv, caches, logs
├── .pre-commit-config.yaml    # Hooks de ruff y formato
├── CHANGELOG.md               # Registro de cambios (Keep a Changelog)
├── CONTRIBUTING.md            # Guía de contribución y entorno de desarrollo
├── LICENSE                    # Licencia MIT (2026)
├── pyproject.toml             # Empaquetado y metadatos estándar
└── README.md                  # Documentación del proyecto
```

---

## Ejecución de Pruebas

Ejecuta la suite de pruebas unitarias sintéticas con `pytest` (sin requerir conexión ni SMC real):

```bash
pytest tests/ -v
```

---

## Licencia

Este proyecto se distribuye bajo la licencia [MIT](LICENSE).
