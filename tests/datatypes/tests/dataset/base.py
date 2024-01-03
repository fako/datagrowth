from django.test import TestCase

from datatypes.models import DatasetVersion, Collection, Document
from project.entities.constants import SEED_DEFAULTS


class BaseDatasetTestCase(TestCase):

    dataset_model = None
    signature = None
    entity_type = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dataset = cls.dataset_model.objects.create(signature=cls.signature)

    def assert_initial_containers(self, dataset_versions=0, collections=0):
        self.assertEqual(DatasetVersion.objects.count(), dataset_versions)
        for dataset_version in DatasetVersion.objects.all():
            self.assertIsNone(dataset_version.pending_at)
            self.assertIsNotNone(dataset_version.finished_at)
            self.assertEqual(dataset_version.task_results, {})
            self.assertEqual(dataset_version.derivatives, {})
            self.assertTrue(dataset_version.is_current)
        self.assertEqual(Collection.objects.count(), collections)
        for collection in Collection.objects.all():
            self.assertEqual(collection.name, self.dataset.signature)
            self.assertIsNone(collection.pending_at)
            self.assertIsNotNone(collection.finished_at)
            self.assertEqual(collection.task_results, {})
            self.assertEqual(collection.derivatives, {})

    def assert_initial_grow_success(self, dataset_versions=0, collections=0, documents=0):
        self.assert_initial_containers(dataset_versions, collections)
        self.assertEqual(Document.objects.count(), documents)
        for document in Document.objects.all():
            self.assertIsNone(document.pending_at)
            self.assertIsNotNone(document.finished_at)
            self.assertEqual(document.properties.keys(), SEED_DEFAULTS[self.entity_type].keys())
            self.assertEqual(document.task_results, {"check_doi": {"success": True}})
            self.assertEqual(document.derivatives, {
                "check_doi": {"check_doi": {"doi": "ok"}}
            })

    def assert_initial_grow_failure(self, dataset_versions=0, collections=0, documents=0, error_documents=0):
        self.assert_initial_containers(dataset_versions, collections)
        self.assertEqual(Document.objects.filter(task_results__check_doi__success=True).count(), documents)
        for success_document in Document.objects.filter(task_results__check_doi__success=True):
            self.assertIsNone(success_document.pending_at)
            self.assertIsNotNone(success_document.finished_at)
            self.assertEqual(success_document.properties.keys(), SEED_DEFAULTS[self.entity_type].keys())
            self.assertEqual(success_document.task_results, {"check_doi": {"success": True}})
            self.assertEqual(success_document.derivatives, {
                "check_doi": {"check_doi": {"doi": "ok"}}
            })
        self.assertEqual(Document.objects.filter(task_results__check_doi__success=False).count(), error_documents)
        for failure_document in Document.objects.filter(task_results__check_doi__success=False):
            self.assertIsNone(failure_document.pending_at)
            self.assertIsNotNone(failure_document.finished_at)
            self.assertEqual(failure_document.properties.keys(), SEED_DEFAULTS[self.entity_type].keys())
            self.assertEqual(failure_document.task_results, {"check_doi": {"success": False}})
            self.assertEqual(failure_document.derivatives, {
                "check_doi": {"check_doi": {"doi": "fail"}}
            })

    def assert_dataset_output(self, dataset, dataset_versions=0, collections=0, documents=0):
        dataset_version_set, collection_set, document_set = dataset.to_querysets()
        self.assertEqual(dataset_version_set.count(), dataset_versions)
        self.assertEqual(collection_set.count(), collections)
        self.assertEqual(document_set.count(), documents)
