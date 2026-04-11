from unittest import TestCase

from datagrowth.configuration import ConfigurationType, load_config


class TestLoadConfigDecorator(TestCase):

    def setUp(self):
        super().setUp()
        self.config = ConfigurationType(namespace="name", private=["_test3"])
        self.config.update({
            "test": "public",
            "_test2": "protected",
            "_test3": "private"
        })

    @staticmethod
    @load_config()
    def decorated(config, *args, **kwargs):
        return config, args, kwargs

    def test_decorator(self):
        # Standard call
        test_config, test_args, test_kwargs = self.decorated(
            "test",
            test="test",
            config=self.config.to_dict(protected=True, private=True)
        )
        self.assertIsInstance(test_config, ConfigurationType)
        self.assertIsNone(
            test_config._defaults,
            "Expected load_config to initialize without default. "
            "Use register_defaults to set defaults for load_config decorator."
        )
        self.assertEqual(test_config._namespace, ["name"])
        self.assertIn("_test3", test_config._private)
        self.assertEqual(self.config.test, "public")
        self.assertEqual(self.config.test2, "protected")
        self.assertEqual(self.config.test3, "private")
        self.assertEqual(self.config._test2, "protected")
        self.assertEqual(self.config._test3, "private")
        self.assertEqual(test_args, ("test",))
        self.assertEqual(test_kwargs, {"test": "test"})
        # Call with config set to a ConfigurationType
        test_config, test_args, test_kwargs = self.decorated(
            "test",
            test="test",
            config=self.config
        )
        self.assertEqual(test_config, self.config)
        self.assertEqual(test_args, ("test",))
        self.assertEqual(test_kwargs, {"test": "test"})
        # Wrong invocation
        try:
            test_config, test_args, test_kwargs = self.decorated(
                "test",
                test="test",
            )
            self.fail("load_config did not throw an exception when no config kwarg was set.")
        except TypeError:
            pass
