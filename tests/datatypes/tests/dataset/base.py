from typing import Optional
from datetime import datetime, timedelta

from django.test import TestCase
from django.utils.timezone import now

from datagrowth.datatypes.datasets.constants import GrowthState

from datatypes.models import DatasetVersion, Collection, Document
from project.entities.constants import SEED_DEFAULTS
from project.entities.generators import document_generator


class BaseDatasetTestCase(TestCase):

    dataset_model = None
    signature = None
    entity_type = None

    dataset = None
    historic_dataset_version = None
    use_current_version = True

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dataset = cls.dataset_model.objects.create(signature=cls.signature)

    ###########################
    # Test data
    ###########################

    @classmethod
    def create_historic_dataset_version(cls, documents_per_collection: int = 20,
                                        finished_at: Optional[datetime] = None):
        finished_at = finished_at or (now() - timedelta(days=1))
        cls.historic_dataset_version = cls.dataset.create_dataset_version()
        cls.historic_dataset_version.finish_processing(current_time=finished_at)
        for collection in cls.historic_dataset_version.collections.all():
            collection.finish_processing(current_time=finished_at)
            for batch in document_generator(cls.entity_type, documents_per_collection, 20, collection):
                for doc in batch:
                    doc.task_results = {"check_doi": {"success": True}}
                    doc.derivatives = {"check_doi": {"check_doi": {"doi": "ok"}}}
                    doc.finish_processing(current_time=finished_at, commit=False)
                Document.objects.bulk_update(batch, ["task_results", "derivatives", "pending_at", "finished_at"])

    @staticmethod
    def prepare_documents(**kwargs):
        for field, updates in kwargs.items():
            documents = {
                doc.identity: doc
                for doc in Document.objects.filter(identity__in=updates.keys())
            }
            for identity, update in updates.items():
                doc = documents[identity]
                value = getattr(doc, field)
                value.update(update)
            Document.objects.bulk_update(documents.values(), [field])

    ###########################
    # Assertions
    ###########################

    def assert_dataset_finish(self, use_current_dataset_version=True, expected_state=GrowthState.COMPLETE,
                              expected_strategy=None):
        expected_strategy = expected_strategy or self.dataset.GROWTH_STRATEGY
        dataset_version = self.dataset.versions.filter(is_current=use_current_dataset_version).last()
        self.assertEqual(dataset_version.version, self.dataset.version)
        self.assertEqual(dataset_version.state, expected_state)
        self.assertEqual(dataset_version.growth_strategy, expected_strategy)

    def assert_datastorage_containers(self, dataset_versions=0, collections=0):
        self.assertEqual(DatasetVersion.objects.count(), dataset_versions)
        expected_current_version_count = 1 if self.use_current_version else 0
        self.assertEqual(DatasetVersion.objects.filter(is_current=True).count(), expected_current_version_count)
        for dataset_version in DatasetVersion.objects.all():
            self.assertIsNone(dataset_version.pending_at)
            self.assertIsNotNone(dataset_version.finished_at)
            self.assertEqual(dataset_version.task_results, {})
            self.assertEqual(dataset_version.derivatives, {})
        self.assertEqual(Collection.objects.count(), collections)
        for collection in Collection.objects.all():
            self.assertEqual(collection.name, self.dataset.signature)
            self.assertIsNone(collection.pending_at)
            self.assertIsNotNone(collection.finished_at)
            self.assertEqual(collection.task_results, {})
            self.assertEqual(collection.derivatives, {})
        dataset_version = self.dataset.get_current_dataset_version()
        return dataset_version.documents.all()

    def assert_grow_success(self, dataset_versions=0, collections=0, documents=0, no_tasks=False):
        documents_queryset = self.assert_datastorage_containers(dataset_versions, collections)
        self.assertEqual(Document.objects.count(), documents)
        for document in documents_queryset:
            self.assertIsNone(document.pending_at)
            self.assertIsNotNone(document.finished_at)
            self.assertEqual(document.properties.keys(), SEED_DEFAULTS[self.entity_type].keys())
            if no_tasks:
                self.assertEqual(document.task_results, {})
                self.assertEqual(document.derivatives, {})
            else:
                self.assertEqual(document.task_results, {"check_doi": {"success": True}})
                self.assertEqual(document.derivatives, {
                    "check_doi": {"check_doi": {"doi": "ok"}}
                })

    def assert_grow_failure(self, dataset_versions=0, collections=0, documents=0, error_documents=0):
        documents_queryset = self.assert_datastorage_containers(dataset_versions, collections)
        self.assertEqual(Document.objects.filter(task_results__check_doi__success=True).count(), documents)
        for success_document in documents_queryset.filter(task_results__check_doi__success=True):
            self.assertIsNone(success_document.pending_at)
            self.assertIsNotNone(success_document.finished_at)
            self.assertEqual(success_document.properties.keys(), SEED_DEFAULTS[self.entity_type].keys())
            self.assertEqual(success_document.task_results, {"check_doi": {"success": True}})
            self.assertEqual(success_document.derivatives, {
                "check_doi": {"check_doi": {"doi": "ok"}}
            })
        self.assertEqual(Document.objects.filter(task_results__check_doi__success=False).count(), error_documents)
        for failure_document in documents_queryset.filter(task_results__check_doi__success=False):
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

    def assert_document_dispatch(self, data_storage_dispatch_mock, expected_identities):
        self.assertTrue(data_storage_dispatch_mock.call_count, "Expected Document tasks to get dispatched")
        identities = []
        for call in data_storage_dispatch_mock.call_args_list:
            args, kwargs = call
            self.assertEqual(args[0], "datatypes.document", "Expected datastorage dispatch to be for Documents.")
            identities += [doc.identity for doc in args[1:]]
        self.assertEqual(identities, expected_identities, "Some expected Document identities were not dispatched.")
