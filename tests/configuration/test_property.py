from unittest import TestCase

from datagrowth.configuration import ConfigurationType, ConfigurationProperty


class ConfigurationPropertyHolder:
    property: ConfigurationProperty = ConfigurationProperty(
        namespace="name",
        private=["_test3"],
        storage_attribute="storage"
    )


class TestConfigurationProperty(TestCase):
    property: ConfigurationProperty = ConfigurationProperty(
        namespace="name",
        private=["_test3"],
        storage_attribute="storage"
    )

    def setUp(self):
        super(TestConfigurationProperty, self).setUp()
        self.holder1 = ConfigurationPropertyHolder()
        self.holder2 = ConfigurationPropertyHolder()

    def test_getter(self):
        self.assertFalse(hasattr(self, "storage"))
        self.assertIsInstance(self.property, ConfigurationType)
        self.assertTrue(hasattr(self, "storage"))

    def test_setter(self):
        self.assertFalse(hasattr(self, "storage"))
        self.property = {}
        self.assertIsInstance(self.property, ConfigurationType)
        self.assertTrue(hasattr(self, "storage"))

    def test_doubles(self):
        self.holder1.property = {"test": "test"}
        self.assertNotEqual(self.holder1.property, self.holder2.property)  # instances should not share configurations

    def test_set_with_type(self):
        self.holder1.property = {"test": "test"}
        self.holder2.property = self.holder1.property
        self.assertEqual(self.holder2.property.test, "test")
        self.assertNotEqual(self.holder1.property, self.holder2.property)  # instances should not share configurations

    def test_setter_ignores_namespace_from_dict(self):
        self.property = {"_namespace": "global", "test": "test"}
        self.assertEqual(self.property._namespace, ["name"])
        self.assertEqual(self.property.test, "test")

    def test_setter_ignores_namespace_from_configuration_type(self):
        external = ConfigurationType(namespace="global")
        external.update({"test": "test"})
        self.property = external
        self.assertEqual(self.property._namespace, ["name"])
        self.assertEqual(self.property.test, "test")

    def test_setter_ignores_none_payload(self):
        self.property = {"test": "test"}
        self.property = None
        self.assertEqual(self.property._namespace, ["name"])
        self.assertEqual(self.property.test, "test")
