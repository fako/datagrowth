from datetime import date, timedelta
from unittest.mock import Mock

from django.test import TestCase

from datagrowth.configuration import create_config


class ResourceTestMixin(TestCase):

    @staticmethod
    def get_test_instance():
        raise NotImplementedError()

    @staticmethod
    def fill_instance(instance):
        instance.uri = "uri"

    def test_retain(self):
        retainer = self.get_test_instance()
        retainer.uri = "retainer"
        retainer.save()
        instance = self.get_test_instance()
        instance.uri = "retainee"
        instance.retain(retainer)
        self.assertIsInstance(instance.retainer_id, int)
        self.assertEqual(instance.retainer_id, retainer.id)

    def test_close(self):
        # Test purge_immediately
        instance = self.get_test_instance()
        instance.uri = "uri"
        instance.config = {"purge_immediately": True}
        instance.id = 1000000
        instance.close()
        self.assertIsNone(instance.purge_at)
        instance.id = None
        instance.close()
        self.assertIsNotNone(instance.purge_at)
        # Test long uri
        original_uri = instance.uri
        original_length = len(original_uri)
        self.assertGreater(original_length, 1)
        instance.uri += "*" * 255
        instance.close()
        self.assertEqual(instance.uri, original_uri + "*" * (255 - original_length))
        # The promise is made in the docs that clean and save get called
        instance.clean = Mock()
        instance.save = Mock()
        instance.close()
        self.assertTrue(instance.clean.called)
        self.assertTrue(instance.save.called)

    def test_get_name(self):
        instance = self.get_test_instance()
        name = instance.get_name()
        self.assertIsInstance(name, str)
        self.assertEqual(name, instance.__class__._meta.model_name)

    def test_get_queue_name(self):
        instance = self.get_test_instance()
        name = instance.get_queue_name()
        self.assertEqual(name, "celery")

    def test_purge_after(self):
        instance = self.get_test_instance()
        instance.config = create_config("global", {
            "purge_after": {"days": 30}
        })
        instance.clean()
        self.assertIsNotNone(instance.purge_at)
        self.assertEqual(instance.purge_at.date() - date.today(), timedelta(days=30))
