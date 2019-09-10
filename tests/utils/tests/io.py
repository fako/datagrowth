import os
from unittest import TestCase

from datagrowth import settings as datagrowth_settings
from datagrowth.utils import (get_model_path, get_media_path, get_dumps_path,
                              queryset_to_disk, object_to_disk, objects_from_disk)


class TestInputOutputPaths(TestCase):

    def test_get_model_path(self):
        path = get_model_path("community")
        self.assertEqual(path, os.path.join(datagrowth_settings.DATAGROWTH_DATA_DIR, "community"))
        path = get_model_path("community", "classifiers")
        self.assertEqual(path, os.path.join(datagrowth_settings.DATAGROWTH_DATA_DIR, "community", "classifiers"))

    def test_get_media_path(self):
        path = get_media_path("community")
        self.assertEqual(path, os.path.join(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, "community"))
        path = get_media_path("community", "videos")
        self.assertEqual(path, os.path.join(datagrowth_settings.DATAGROWTH_MEDIA_ROOT, "community", "videos"))
        path = get_media_path("community", absolute=False)
        self.assertEqual(path, os.path.join("community"))
        path = get_media_path("community", "videos", absolute=False)
        self.assertEqual(path, os.path.join("community", "videos"))

    def test_get_dumps_path(self):
        self.skipTest("not tested until release of Dataset (Django model wrapping data storage)")


class TestDumpLoadDjangoModels(TestCase):

    def test_queryset_to_disk(self):
        self.skipTest("not tested until release of Dataset (Django model wrapping data storage)")

    def test_object_to_disk(self):
        self.skipTest("not tested until release of Dataset (Django model wrapping data storage)")

    def test_objects_from_disk(self):
        self.skipTest("not tested until release of Dataset (Django model wrapping data storage)")
