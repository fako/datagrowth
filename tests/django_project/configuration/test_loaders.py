import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from datagrowth.configuration.loaders import InvalidConfigurationError, build_default_configuration


class TestConfigurationLoaders(TestCase):

    PROJECT_LOCATION = Path(__file__).resolve().parents[1]

    def test_hierarchy_and_implicit_global_mapping(self) -> None:
        django_settings = SimpleNamespace(
            configured=True,
            DATAGROWTH_ASYNCHRONOUS=False,
            DATAGROWTH_SHELL_RESOURCE_BIN_DIR="/django/proper/bin",
            DATAGROWTH_BIN_DIR="/django/plain/bin",
        )

        with patch.dict(os.environ, {"DATAGROWTH_ASYNCHRONOUS": "true"}, clear=True):
            configuration = build_default_configuration(
                project_location=self.PROJECT_LOCATION,
                django_settings=django_settings,
            )

        self.assertTrue(configuration["global_asynchronous"])
        self.assertEqual(configuration["shell_resource_bin_dir"], "/project/bin")

    def test_plain_settings_have_lower_precedence_than_proper_namespaced_settings(self) -> None:
        django_settings = SimpleNamespace(
            configured=True,
            DATAGROWTH_BIN_DIR="/django/plain/bin",
            DATAGROWTH_SHELL_RESOURCE_BIN_DIR="/django/proper/bin",
        )

        with patch.dict(os.environ, {}, clear=True):
            configuration = build_default_configuration(
                project_location=None,
                django_settings=django_settings,
            )

        self.assertEqual(configuration["shell_resource_bin_dir"], "/django/proper/bin")

    def test_unknown_keys_are_ignored_and_warned(self) -> None:
        django_settings = SimpleNamespace(
            configured=True,
            DATAGROWTH_UNKNOWN="django-unknown",
        )

        with TemporaryDirectory() as temporary_directory:
            project_file = Path(temporary_directory) / "datagrowth.yml"
            project_file.write_text(
                "\n".join([
                    "unknown_namespace:",
                    "  value: 1",
                    "",
                ]),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"DATAGROWTH_UNKNOWN": "env-unknown"}, clear=True):
                with self.assertLogs("datagrowth", level="WARNING") as warnings:
                    configuration = build_default_configuration(
                        project_location=Path(temporary_directory),
                        django_settings=django_settings,
                    )

        self.assertNotIn("global_unknown", configuration)
        warning_text = "\n".join(warnings.output)
        self.assertIn("invoke project", warning_text)
        self.assertIn("invoke env", warning_text)
        self.assertIn("django settings", warning_text)

    def test_missing_default_key_disables_proper_and_plain_overrides(self) -> None:
        django_settings = SimpleNamespace(
            configured=True,
            DATAGROWTH_SHELL_RESOURCE_BIN_DIR="/django/proper/bin",
            DATAGROWTH_BIN_DIR="/django/plain/bin",
            DATAGROWTH_ASYNCHRONOUS=False,
        )
        nested_defaults_without_shell_bin = {
            "global": {
                "asynchronous": True,
            },
            "http_resource": {
                "user_agent": None,
            },
            "shell_resource": {
                "interval_duration": 0,
            },
        }

        with patch.dict(os.environ, {}, clear=True):
            with self.assertLogs("datagrowth", level="WARNING") as warnings:
                configuration = build_default_configuration(
                    project_location=None,
                    django_settings=django_settings,
                    package_defaults=nested_defaults_without_shell_bin
                )

        self.assertNotIn("shell_resource_bin_dir", configuration)
        self.assertFalse(configuration["global_asynchronous"])
        warning_text = "\n".join(warnings.output)
        self.assertIn("DATAGROWTH_SHELL_RESOURCE_BIN_DIR", warning_text)
        self.assertIn("DATAGROWTH_BIN_DIR", warning_text)

    def test_django_default_configuration_setting_is_rejected(self) -> None:
        django_settings = SimpleNamespace(
            configured=True,
            DATAGROWTH_DEFAULT_CONFIGURATION={"global_asynchronous": False},
        )
        with self.assertRaises(InvalidConfigurationError):
            build_default_configuration(
                project_location=None,
                django_settings=django_settings,
            )
