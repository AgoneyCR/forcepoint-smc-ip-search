"""Pruebas unitarias para el módulo cli y su punto de entrada."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from smc.api.exceptions import ElementNotFound, SMCConnectionError

from forcepoint_smc_ip_search.cli import build_parser, main


class TestCliParser:
    """Pruebas del analizador de argumentos de línea de comandos."""

    def test_default_parser_values(self):
        parser = build_parser()
        args = parser.parse_args([])

        assert args.debug is False
        assert args.verify_ssl is False
        assert args.url is None
        assert args.api_key is None
        assert args.group is None
        assert args.search is None
        assert args.duplicates is False

    def test_debug_flag_aliases(self):
        parser = build_parser()

        assert parser.parse_args(["--debug"]).debug is True
        assert parser.parse_args(["-v"]).debug is True
        assert parser.parse_args(["--verbose"]).debug is True

    def test_direct_actions_parsing(self):
        parser = build_parser()

        args_search = parser.parse_args(["--search", "192.0.2.5"])
        assert args_search.search == "192.0.2.5"

        args_dups = parser.parse_args(["--duplicates"])
        assert args_dups.duplicates is True


class TestCliMainExecution:
    """Pruebas de la función principal main()."""

    @patch("forcepoint_smc_ip_search.cli.search_in_group")
    @patch("forcepoint_smc_ip_search.cli.SMCClient")
    def test_main_direct_search_propagates_debug(self, mock_client_cls, mock_search):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_search.return_value = True

        exit_code = main(
            [
                "--url",
                "https://smc.example.com:8082",
                "--api-key",
                "dummy_token_123",
                "--group",
                "Mi_Grupo_Ejemplo",
                "--search",
                "192.0.2.50",
                "--debug",
            ]
        )

        assert exit_code == 0
        mock_client.login.assert_called_once()
        mock_client.validate_group.assert_called_once_with("Mi_Grupo_Ejemplo")
        mock_search.assert_called_once_with("Mi_Grupo_Ejemplo", "192.0.2.50", debug=True)
        mock_client.logout.assert_called_once()

    @patch("forcepoint_smc_ip_search.cli.check_duplicates_in_group")
    @patch("forcepoint_smc_ip_search.cli.SMCClient")
    def test_main_direct_duplicates_without_debug(self, mock_client_cls, mock_dups):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_dups.return_value = {"has_findings": False}

        exit_code = main(
            [
                "--url",
                "https://smc.example.com:8082",
                "--api-key",
                "dummy_token_123",
                "--group",
                "Mi_Grupo_Ejemplo",
                "--duplicates",
            ]
        )

        assert exit_code == 0
        mock_dups.assert_called_once_with("Mi_Grupo_Ejemplo", debug=False)
        mock_client.logout.assert_called_once()

    @patch.dict(
        os.environ,
        {
            "SMC_URL": "https://smc.example.com:8082",
            "SMC_API_KEY": "env_api_key",
            "SMC_GROUP": "Grupo_Desde_Env",
        },
    )
    @patch("forcepoint_smc_ip_search.cli.search_in_group")
    @patch("forcepoint_smc_ip_search.cli.SMCClient")
    def test_main_reads_env_variables(self, mock_client_cls, mock_search):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_search.return_value = True

        exit_code = main(["--search", "192.0.2.1"])

        assert exit_code == 0
        mock_client_cls.assert_called_once_with(
            url="https://smc.example.com:8082",
            api_key="env_api_key",
            verify_ssl=False,
        )
        mock_client.validate_group.assert_called_once_with("Grupo_Desde_Env")

    @patch("forcepoint_smc_ip_search.cli.SMCClient")
    def test_main_group_not_found(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.validate_group.side_effect = ElementNotFound("No existe grupo")

        exit_code = main(
            [
                "--url",
                "https://smc.example.com:8082",
                "--api-key",
                "dummy_token_123",
                "--group",
                "Grupo_Inexistente",
                "--search",
                "192.0.2.1",
            ]
        )

        assert exit_code == 1
        mock_client.logout.assert_called_once()

    @patch("forcepoint_smc_ip_search.cli.SMCClient")
    def test_main_connection_error(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.login.side_effect = SMCConnectionError("Error de red")

        exit_code = main(
            [
                "--url",
                "https://smc.example.com:8082",
                "--api-key",
                "dummy_token_123",
                "--group",
                "Mi_Grupo_Ejemplo",
                "--search",
                "192.0.2.1",
            ]
        )

        assert exit_code == 1
        mock_client.logout.assert_called_once()

    @patch("forcepoint_smc_ip_search.cli.SMCClient")
    def test_main_keyboard_interrupt(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.login.side_effect = KeyboardInterrupt()

        exit_code = main(
            [
                "--url",
                "https://smc.example.com:8082",
                "--api-key",
                "dummy_token_123",
                "--group",
                "Mi_Grupo_Ejemplo",
                "--search",
                "192.0.2.1",
            ]
        )

        assert exit_code == 0
        mock_client.logout.assert_called_once()
