"""Módulo de conexión y gestión de sesión para Forcepoint SMC.

Proporciona la clase `SMCClient` para gestionar el ciclo de vida de la conexión,
el inicio y cierre de sesión, y la validación de elementos en Forcepoint SMC
utilizando la biblioteca `fp-NGFW-SMC-python`.
"""

from __future__ import annotations

import logging
from typing import Any

import urllib3
from smc import session
from smc.api.exceptions import ElementNotFound, SMCConnectionError
from smc.elements.group import Group

logger = logging.getLogger(__name__)


def normalize_smc_url(raw_url: str) -> str:
    """Normaliza la dirección URL del SMC asegurando protocolo y puerto por defecto.

    Args:
        raw_url: Cadena introducida con la IP o URL del SMC
            (por ejemplo '192.0.2.10' o 'https://smc.example.com:8082').

    Returns:
        URL debidamente formateada con esquema https y puerto 8082 si no fueron
        especificados.

    Examples:
        >>> normalize_smc_url("192.0.2.10")
        'https://192.0.2.10:8082'
        >>> normalize_smc_url("https://smc.example.com:8082")
        'https://smc.example.com:8082'
    """
    clean_url = raw_url.strip()
    if not clean_url.startswith("http://") and not clean_url.startswith("https://"):
        return f"https://{clean_url}:8082"
    return clean_url


class SMCClient:
    """Gestiona la sesión y operaciones de conexión con Forcepoint SMC.

    Permite ser utilizada como manejador de contexto (`with SMCClient(...) as client:`)
    para garantizar el cierre ordenado de la sesión al finalizar las operaciones.

    Attributes:
        url: URL normalizada del Forcepoint Management Center.
        api_key: Clave de autenticación API para el SMC.
        verify_ssl: Si se debe verificar la validez del certificado SSL.
        timeout: Tiempo de espera en segundos para la conexión HTTP.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        verify_ssl: bool = False,
        timeout: int | None = None,
    ) -> None:
        """Inicializa los parámetros de conexión de SMCClient.

        Args:
            url: Dirección IP o URL del SMC.
            api_key: Clave de API de Forcepoint SMC.
            verify_ssl: Si es False, desactiva la validación de certificados SSL
                y silencia las advertencias de urllib3. Por defecto es False.
            timeout: Tiempo límite en segundos para peticiones API.
        """
        self.url: str = normalize_smc_url(url)
        self.api_key: str = api_key.strip()
        self.verify_ssl: bool = verify_ssl
        self.timeout: int | None = timeout

        if not self.verify_ssl:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def login(self) -> None:
        """Inicia sesión en Forcepoint SMC mediante la API REST.

        Raises:
            SMCConnectionError: Si se produce un error de red o autenticación.
            Exception: Para otros errores inesperados durante la negociación.
        """
        logger.debug("Intentando conectar con SMC en %s (SSL verify=%s)", self.url, self.verify_ssl)
        try:
            login_kwargs: dict[str, Any] = {
                "url": self.url,
                "api_key": self.api_key,
                "verify": self.verify_ssl,
            }
            if self.timeout is not None:
                login_kwargs["timeout"] = self.timeout

            session.login(**login_kwargs)
            logger.info(
                "Sesión iniciada correctamente en SMC como: %s",
                getattr(session, "name", "Desconocido"),
            )
        except SMCConnectionError as err:
            logger.error("Error de conexión al SMC (%s): %s", self.url, err)
            raise
        except Exception as err:
            logger.error("Error inesperado al iniciar sesión en SMC: %s", err)
            raise

    def logout(self) -> None:
        """Cierra la sesión activa en el SMC si existe una conexión establecida."""
        try:
            if getattr(session, "is_active", False):
                session.logout()
                logger.info("Sesión de SMC cerrada correctamente.")
        except Exception as err:
            logger.warning("Error al cerrar la sesión de SMC: %s", err)

    @property
    def is_active(self) -> bool:
        """Indica si la sesión actual con el SMC se encuentra activa."""
        return bool(getattr(session, "is_active", False))

    def validate_group(self, group_name: str) -> Group:
        """Valida que un grupo existe en el SMC y lo retorna.

        Args:
            group_name: Nombre del grupo en Forcepoint SMC.

        Returns:
            Instancia de `Group` recuperada del SMC.

        Raises:
            ElementNotFound: Si el grupo especificado no existe en el SMC.
        """
        clean_name = group_name.strip()
        logger.debug("Validando existencia del grupo '%s' en el SMC...", clean_name)
        try:
            group = Group.get(clean_name)
            logger.info("El grupo '%s' ha sido validado correctamente.", clean_name)
            return group
        except ElementNotFound:
            logger.error("El grupo '%s' NO existe en el SMC.", clean_name)
            raise

    def __enter__(self) -> SMCClient:
        """Entrada del gestor de contexto: conecta automáticamente."""
        self.login()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any | None,
    ) -> None:
        """Salida del gestor de contexto: desconecta la sesión."""
        self.logout()
