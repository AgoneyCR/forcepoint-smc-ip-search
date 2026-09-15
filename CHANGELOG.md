# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

## [0.1.0] - 2026-09-15

### Añadido
- **Arquitectura modular** en `src/forcepoint_smc_ip_search/` dividida en submódulos especializados:
  - `smc_client.py`: Gestión de conexión y ciclo de vida de sesión SMC con soporte para context manager.
  - `ip_matcher.py`: Comprobación de pertenencia de IPs a elementos de red (`Host`, `Network`, `AddressRange`, `IPList`) y normalización canónica de entradas.
  - `search.py`: Búsqueda recursiva en profundidad de IPs dentro de grupos y subgrupos con control de ciclos.
  - `duplicates.py`: Detección recursiva de duplicados internos dentro de una misma lista y cruzados entre listas del grupo.
  - `cli.py`: Interfaz de línea de comandos unificada y menú interactivo con flag de depuración `--debug` (`-v` / `--verbose`).
- **Punto de entrada de consola** `smc-ip-tool` registrado en `pyproject.toml`.
- **Soporte de configuración y secretos**:
  - Carga de variables de entorno mediante `python-dotenv` (`SMC_URL`, `SMC_API_KEY`, `SMC_GROUP`, `SMC_SSL_VERIFY`).
  - Plantilla `.env.example` con placeholders genéricos y sanitizados.
- **Suite de pruebas unitarias**:
  - Mocks sintéticos para objetos Forcepoint SMC en `tests/conftest.py`.
  - Pruebas de comparación de IPs, rangos, CIDRs y tolerancia a formatos corruptos en `tests/test_ip_matcher.py`.
  - Pruebas de detección de duplicados internos y entre listas en `tests/test_duplicates.py`.
  - Pruebas de búsqueda recursiva y prevención de ciclos en `tests/test_search.py`.
  - Pruebas de CLI y propagación del flag `--debug` en `tests/test_cli.py`.
- **Integración Continua (CI)**:
  - Workflow de GitHub Actions en `.github/workflows/ci.yml` ejecutando linting (Ruff) y pruebas (Pytest) sobre Python 3.9 y 3.13.
- **Configuración de calidad y contribución**:
  - Archivos `.pre-commit-config.yaml`, plantillas de issues y Pull Request en `.github/`.
  - Documentación técnica completa en `README.md` y guía de desarrollo en `CONTRIBUTING.md`.
