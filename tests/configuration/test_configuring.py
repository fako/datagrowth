from unittest import TestCase

from datagrowth.configuration.defaults import DATAGROWTH_DEFAULT_CONFIGURATION
from datagrowth.configuration import ConfigurationType, create_config, register_defaults


class TestCreateConfig(TestCase):

    def test_create_config(self):
        test_config = create_config("name", {
            "test": "public",
            "_test2": "protected",
            "_test3": "protected 2"
        })
        self.assertIsNone(test_config._defaults)
        self.assertIsInstance(test_config, ConfigurationType)
        self.assertEqual(test_config.test, "public")
        self.assertEqual(test_config.test2, "protected")
        self.assertEqual(test_config.test3, "protected 2")
        self.assertEqual(test_config._test2, "protected")
        self.assertEqual(test_config._test3, "protected 2")

    def test_create_config_registered_defaults(self):
        register_defaults("name", {
            "test4": "namespaced default"
        })
        test_config = create_config("name", {
            "test": "public",
            "_test2": "protected",
            "_test3": "protected 2"
        })
        self.assertIsNone(test_config._defaults)
        self.assertIsInstance(test_config, ConfigurationType)
        self.assertEqual(test_config._namespace, ["name"])
        self.assertEqual(test_config.test4, "namespaced default")
        self.assertEqual(test_config._defaults, DATAGROWTH_DEFAULT_CONFIGURATION)


class TestRegisterConfigDefaults(TestCase):

    def test_register_defaults(self):
        # Overriding existing defaults
        self.assertFalse(DATAGROWTH_DEFAULT_CONFIGURATION["global_purge_immediately"])
        register_defaults("global", {
            "purge_immediately": True
        })
        self.assertTrue(DATAGROWTH_DEFAULT_CONFIGURATION["global_purge_immediately"])
        DATAGROWTH_DEFAULT_CONFIGURATION["global_purge_immediately"] = False
        # Creating new defaults
        self.assertNotIn("mock_test", DATAGROWTH_DEFAULT_CONFIGURATION)
        register_defaults("mock", {
            "test": "create"
        })
        self.assertEqual(DATAGROWTH_DEFAULT_CONFIGURATION["mock_test"], "create")
