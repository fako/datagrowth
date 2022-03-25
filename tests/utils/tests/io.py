import os
from unittest.mock import Mock, patch
import json
from tqdm import tqdm
from collections.abc import Iterator

from django.test import TestCase
from django.core.serializers import serialize, deserialize

from datagrowth import settings as datagrowth_settings
from datagrowth.utils import (get_model_path, get_media_path, get_dumps_path,
                              queryset_to_disk, object_to_disk, objects_from_disk)
from resources.models import HttpResourceMock


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
        instance = HttpResourceMock()
        instance.get_name = Mock(return_value="name")
        path = get_dumps_path(instance)
        self.assertEqual(path, os.path.join(datagrowth_settings.DATAGROWTH_DATA_DIR, "resources", "dumps", "name"))
        self.assertTrue(instance.get_name.called)


class TestDumpLoadDjangoModels(TestCase):

    fixtures = ["test-http-resource-mock"]

    def get_file_path(self, mode):
        dump_path = get_dumps_path(HttpResourceMock)
        file_name = "{}-dump-test.json".format(mode)
        return os.path.join(dump_path, file_name)

    def create_test_dump_file(self):
        obj = HttpResourceMock.objects.get(id=1)
        queryset = HttpResourceMock.objects.filter(id__in=[2, 3, 4, 5, 6])
        dump_path = get_dumps_path(obj)
        with open(os.path.join(dump_path, "read-dump-test.json"), "w") as fd:
            object_to_disk(obj, fd)
            queryset_to_disk(queryset, fd, batch_size=2)

    @patch("datagrowth.utils.io.serialize", wraps=serialize)
    def test_queryset_to_disk(self, serialize_mock):
        queryset = HttpResourceMock.objects.filter(id__in=[1, 2, 3, 4, 5, 6])
        fd = open(self.get_file_path("write"), "w")
        fd.writelines = Mock()
        queryset_to_disk(queryset, fd, batch_size=2, progress_bar=False)
        self.assertEquals(fd.writelines.call_count, 3)
        self.assertEquals(serialize_mock.call_count, 3)
        current_id = 1
        for call in fd.writelines.call_args_list:
            args, kwargs = call
            lines = args[0]
            self.assertEquals(len(lines), 1)
            line = lines[0]
            self.assertTrue(line.endswith("\n"))
            models = json.loads(line)
            self.assertEquals(len(models), 2)
            for model in models:
                self.assertEquals(model["pk"], current_id)
                current_id += 1

    @patch("datagrowth.utils.io.serialize", wraps=serialize)
    def test_object_to_disk(self, serialize_mock):
        obj = HttpResourceMock.objects.get(id=1)
        fd = open(self.get_file_path("write"), "w")
        fd.write = Mock()
        object_to_disk(obj, fd)
        self.assertEquals(fd.write.call_count, 1)
        self.assertEquals(serialize_mock.call_count, 1)
        call = fd.write.call_args_list[0]
        args, kwargs = call
        line = args[0]
        self.assertTrue(line.endswith("\n"))
        models = json.loads(line)
        self.assertEquals(len(models), 1)
        model = models[0]
        self.assertEquals(model["pk"], 1)

    @patch("datagrowth.utils.io.tqdm", wraps=tqdm)
    @patch("datagrowth.utils.io.deserialize", wraps=deserialize)
    def test_objects_from_disk(self, deserialize_mock, tqdm_mock):
        with open(self.get_file_path("read"), "r") as fd:
            iterator = objects_from_disk(fd, progress_bar=False)
            self.assertIsInstance(iterator, Iterator)
            data = list(iterator)
        self.assertEquals(deserialize_mock.call_count, 4)
        tqdm_mock.assert_called_once_with(fd, total=4, disable=True)
        self.assertEquals(len(data[0]), 1)
        self.assertEquals(len(data[1]), 2)
        self.assertEquals(len(data[2]), 2)
        self.assertEquals(len(data[3]), 1)
        model = data[0][0]
        self.assertIsInstance(model, HttpResourceMock)
        self.assertEquals(model.id, 1)
