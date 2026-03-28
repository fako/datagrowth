from unittest.mock import patch

from django.test import TestCase

from datatypes.models import DatasetVersion, Collection, Document


class DataStorageTestCase(TestCase):

    instance = None

    def test_get_document_model(self):
        model = self.instance.get_document_model()
        self.assertEqual(model, Document)
        with patch.object(self.instance.__class__, "DOCUMENT_MODEL", "DocumentInvalid"):
            self.assertRaises(LookupError, self.instance.get_document_model)

    def test_get_collection_model(self):
        model = self.instance.get_collection_model()
        self.assertEqual(model, Collection)
        with patch.object(self.instance.__class__, "COLLECTION_MODEL", "CollectionInvalid"):
            self.assertRaises(LookupError, self.instance.get_collection_model)

    def test_get_dataset_version_model(self):
        model = self.instance.get_dataset_version_model()
        self.assertEqual(model, DatasetVersion)
        with patch.object(self.instance.__class__, "DATASET_VERSION_MODEL", "DatasetVersionInvalid"):
            self.assertRaises(LookupError, self.instance.get_dataset_version_model)

    def test_get_pending_tasks(self):
        self.skipTest("to be tested")

    def test_get_property_dependencies(self):
        self.skipTest("to be tested")

    def test_invalidate_tasks(self):
        self.skipTest("to be tested")

    def test_clear_task_result(self):
        self.skipTest("to be tested")

    def test_prepare_processing(self):
        self.skipTest("to be tested")

    def test_finish_processing(self):
        self.skipTest("to be tested")
