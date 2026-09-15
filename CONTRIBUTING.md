# Guía de Contribución

¡Gracias por tu interés en contribuir a `forcepoint-smc-ip-search`!

---

## 1. Configuración del Entorno de Desarrollo

Requisitos mínimos:
- Python 3.9 o superior (probado en 3.9 y 3.13)
- `git`

### Pasos de inicialización

1. Clona el repositorio:
   ```bash
   git clone https://github.com/AgoneyCR/forcepoint-smc-ip-search.git
   cd forcepoint-smc-ip-search
   ```

2. Crea y activa un entorno virtual:
   ```bash
   # En Linux / macOS:
   python3 -m venv .venv
   source .venv/bin/activate

   # En Windows (PowerShell):
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

3. Instala el proyecto en modo editable junto con las dependencias de desarrollo:
   ```bash
   pip install --upgrade pip
   pip install -e .[dev]
   ```

4. Instala los hooks de pre-commit para formateo y chequeos automáticos:
   ```bash
   pre-commit install
   ```

---

## 2. Ejecución de Pruebas Unitarias

Las pruebas están completamente aisladas y mockean las llamadas al SDK de Forcepoint SMC, por lo que no se requiere acceso a un SMC real ni credenciales:

```bash
pytest tests/ -v
```

Para generar reporte de cobertura:
```bash
pytest --cov=forcepoint_smc_ip_search tests/
```

---

## 3. Calidad de Código y Estilo

Utilizamos [Ruff](https://astral.sh/ruff) para linting y formateo:

```bash
# Revisar problemas de código
ruff check .

# Aplicar correcciones automáticas
ruff check . --fix

# Verificar formateo
ruff format --check .

# Aplicar formateo
ruff format .
```

### Reglas de Estilo:
- **Type Hints**: Todas las funciones y métodos públicos deben incluir anotaciones de tipo completas.
- **Docstrings**: Formato Google o NumPy en todas las clases, funciones y módulos públicos.
- **Seguridad**: NUNCA commitees credenciales, API keys, URLs de servidores reales ni nombres de incidentes/grupos de producción. Utiliza siempre identificadores y direcciones IP genéricas (RFC 5737 / RFC 1918).

---

## 4. Flujo de Ramas y Pull Requests

1. Crea una rama descriptiva para tu cambio:
   ```bash
   git checkout -b feature/mi-nueva-mejora
   # o
   git checkout -b fix/correccion-error
   ```
2. Realiza tus commits con mensajes claros y convencionales (`feat: ...`, `fix: ...`, `docs: ...`).
3. Asegúrate de que las pruebas y los chequeos de ruff pasen localmente antes de enviar el PR.
4. Abre un Pull Request describiendo los cambios y el problema resuelto.
