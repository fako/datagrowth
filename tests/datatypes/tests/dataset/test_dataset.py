from django.test import TestCase
from django.utils.timezone import now

from unittest.mock import patch

from datagrowth.exceptions import DGGrowthUnfinished
from datagrowth.datatypes.datasets.constants import GrowthState
from datagrowth.datatypes.storage import DataStorageFactory
from datagrowth.processors import SeedingProcessorFactory

from datatypes.models import Dataset, DatasetMock, DatasetVersion


class TestDatasetProtocol(TestCase):

    def setUp(self):
        super().setUp()
        self.input_configuration = {
            "setting0": "possible?!",
            "$setting2": "variable",
            "setting1": "const",
            "illegal": "please",
            "$setting4": "input"
        }

    def test_get_name(self):
        self.assertEqual(Dataset.get_name(), 'dataset')
        self.assertEqual(DatasetMock.get_name(), 'mock')
        with patch.object(Dataset, "NAME", "dataset_real"):
            self.assertEqual(Dataset.get_name(), 'dataset_real')

    def test_get_namespace(self):
        self.assertEqual(Dataset.get_namespace(), "datatypes")
        with patch.object(DatasetMock._meta, "app_label", "test_app"):
            self.assertEqual(DatasetMock.get_namespace(), "test-app")

    def test_cast_to_string(self):
        dataset = Dataset()
        dataset.signature = "test"
        dataset.id = 1
        self.assertEqual(str(dataset), "test (1)")

    def test_get_signature_from_input(self):
        dataset = Dataset()
        signature = dataset.get_signature_from_input("test", **self.input_configuration)
        self.assertEqual(signature, "$setting4=input&setting1=const&test")

        dataset_mock = DatasetMock()
        signature = dataset_mock.get_signature_from_input("test", **self.input_configuration)
        self.assertEqual(signature, "test")

    def test_filter_growth_configuration(self):
        dataset = Dataset()
        configuration = dataset.filter_growth_configuration(**self.input_configuration)
        self.assertIsInstance(configuration, dict)
        self.assertEqual(configuration["setting1"], "const")
        self.assertEqual(configuration["$setting4"], "input")
        self.assertNotIn("$setting2", configuration)
        self.assertNotIn("illegal", configuration)
        self.assertNotIn("setting0", configuration)

        dataset_mock = DatasetMock()
        configuration = dataset_mock.filter_growth_configuration(**self.input_configuration)
        self.assertIsInstance(configuration, dict)
        self.assertNotIn("setting1", configuration)
        self.assertNotIn("$setting2", configuration)
        self.assertNotIn("illegal", configuration)
        self.assertNotIn("setting0", configuration)
        self.assertNotIn("setting3", configuration)
        self.assertNotIn("$setting4", configuration)

    def test_filter_harvest_configuration(self):
        dataset = Dataset()
        configuration = dataset.filter_harvest_configuration(**self.input_configuration)
        self.assertIsInstance(configuration, dict)
        self.assertEqual(configuration["$setting2"], "variable")
        self.assertEqual(configuration["$setting4"], "input")
        self.assertNotIn("setting3", configuration)
        self.assertNotIn("setting1", configuration)
        self.assertNotIn("setting0", configuration)
        self.assertNotIn("illegal", configuration)

        dataset_mock = DatasetMock()
        configuration = dataset_mock.filter_harvest_configuration(**self.input_configuration)
        self.assertIsInstance(configuration, dict)
        self.assertNotIn("setting1", configuration)
        self.assertNotIn("$setting2", configuration)
        self.assertNotIn("illegal", configuration)
        self.assertNotIn("setting0", configuration)
        self.assertNotIn("setting3", configuration)
        self.assertNotIn("$setting4", configuration)

    def test_get_dataset_version_model(self):
        dataset_version_model = Dataset.get_dataset_version_model()
        self.assertEqual(dataset_version_model, DatasetVersion)
        with patch.object(Dataset, "DATASET_VERSION_MODEL", "DatasetVersionInvalid"):
            self.assertRaises(LookupError, Dataset.get_dataset_version_model)


class TestDataset(TestCase):

    fixtures = ["test-dataset"]

    def setUp(self):
        super().setUp()
        self.instance = Dataset.objects.get(id=1)
        self.incomplete = Dataset.objects.get(id=2)
        self.complete = Dataset.objects.get(id=3)
        self.empty = Dataset.objects.get(id=4)
        self.seeds = [{"test": 1}, {"test": 2}, {"test": 3}]

    def raise_unfinished(self, result):
        raise DGGrowthUnfinished("Raised for test")

    def test_create_dataset_version(self):
        dataset_version = self.instance.create_dataset_version()
        self.assertIsInstance(dataset_version, DatasetVersion)
        self.assertIsNotNone(dataset_version.id)
        self.assertEqual(dataset_version.dataset, self.instance)
        self.assertEqual(dataset_version.growth_strategy, self.instance.GROWTH_STRATEGY)
        self.assertEqual(dataset_version.task_definitions, {
            "document": {
                "check_doi": {
                    "depends_on": [
                        "$.state",
                        "$.doi"
                    ],
                    "checks": [],
                    "resources": []
                }
            },
            "collection": {},
            "datasetversion": {}
        })
        self.assertEqual(dataset_version.tasks, {})
        self.assertIsNone(dataset_version.pending_at, "Expected DatasetVersion not to start processing immediately")
        self.assertIsNone(dataset_version.finished_at, "Expected DatasetVersion to not finish processing")
        self.assertEqual(dataset_version.collections.all().count(), 1)
        self.assertEqual(dataset_version.documents.all().count(), 0)
        collection = dataset_version.collections.last()
        self.assertEqual(collection.identifier, "id")
        self.assertIsNone(collection.referee)
        self.assertEqual(collection.tasks, {})
        self.assertIsNone(collection.pending_at, "Expected Collection not to start processing immediately")
        self.assertIsNone(collection.finished_at, "Expected Collection to not finish processing")
        self.assertEqual(collection.name, "setting1=const&test",
                         "Expected Dataset.signature to be the default Collection.name")
        # Test creating a document using the created dataset version
        document = collection.build_document({"id": 1})
        self.assertEqual(document.dataset_version, dataset_version)
        self.assertEqual(document.collection, collection)
        self.assertEqual(document.identity, 1)
        self.assertEqual(document.tasks, {
            "check_doi": {
                "depends_on": [
                    "$.state",
                    "$.doi"
                ],
                "checks": [],
                "resources": []
            }
        })
        self.assertIsNotNone(document.pending_at, "New Documents should be pending processing")
        self.assertIsNone(document.finished_at, "New Documents should not be finished with processing")

    def test_copy_dataset_version(self):
        source_dataset_version = self.complete.versions.first()
        source_collection_ids = set(source_dataset_version.collections.values_list("id", flat=True))
        source_document_ids = set(source_dataset_version.documents.values_list("id", flat=True))
        dataset_version = self.complete.copy_dataset_version(source_dataset_version)
        collection_ids = set(dataset_version.collections.values_list("id", flat=True))
        document_ids = set(dataset_version.documents.values_list("id", flat=True))
        self.assertNotEqual(dataset_version, source_dataset_version)
        self.assertNotEqual(dataset_version.id, source_dataset_version.id)
        self.assertEqual(dataset_version.collections.count(), source_dataset_version.collections.count())
        self.assertEqual(dataset_version.documents.count(), source_dataset_version.documents.count())
        self.assertFalse(collection_ids.intersection(source_collection_ids))
        self.assertFalse(document_ids.intersection(source_document_ids))

    def assert_document_preparation(self, document, current_time, should_reprocess=False):
        self.assertEqual(document.tasks, {
            "check_doi": {
                "depends_on": [
                    "$.state",
                    "$.doi"
                ],
                "checks": [],
                "resources": []
            }
        })
        if not should_reprocess:
            self.assertIsNone(document.pending_at,
                              "Completed documents should not become pending a second time")
            self.assertIsNotNone(document.finished_at, "Completed Documents should retain their finished_at value")
            self.assertEqual(document.derivatives, {
                "check_doi": {
                    "doi": "ok"
                }
            })
            self.assertEqual(document.task_results, {
                "check_doi": {
                    "success": True
                }
            })
        else:
            self.assertEqual(document.pending_at, current_time,
                             "Erroneous Documents should retry processing")
            self.assertIsNone(document.finished_at, "Erroneous Documents should retry processing")

    def assert_dataset_version_preparation(self, dataset_version, current_time, document_count=3):
        self.assertEqual(dataset_version.state, GrowthState.PENDING)
        self.assertEqual(dataset_version.pending_at, current_time)
        self.assertIsNone(dataset_version.finished_at)
        self.assertEqual(dataset_version.derivatives, {})
        self.assertEqual(dataset_version.task_results, {})
        self.assertEqual(dataset_version.tasks, {
            "dataset_version_task": {
                "depends_on": [],
                "checks": [],
                "resources": []
            }
        })
        self.assertEqual(dataset_version.collections.count(), 1)
        for collection in dataset_version.collections.all():
            self.assertIsNone(collection.pending_at,
                              "Collection should not become pending until all Documents are created")
            self.assertIsNone(collection.finished_at)
            self.assertEqual(collection.derivatives, {})
            self.assertEqual(collection.task_results, {})
            self.assertEqual(collection.tasks, {
                "collection_task": {
                    "depends_on": [],
                    "checks": [],
                    "resources": []
                }
            })
            self.assertEqual(collection.documents.all().count(), document_count)
        self.assertEqual(dataset_version.documents.all().count(), document_count)
        for document in dataset_version.documents.all():
            self.assert_document_preparation(document, current_time, should_reprocess=document.id in [2, 3])

    def test_prepare_dataset_version(self):
        current_time = now()
        complete_dataset_version = self.complete.versions.first()
        dataset_version = self.complete.prepare_dataset_version(complete_dataset_version, current_time)
        self.assert_dataset_version_preparation(dataset_version, current_time)

    def test_prepare_dataset_version_error(self):
        current_time = now()
        error_dataset_version = self.incomplete.versions.first()
        dataset_version = self.incomplete.prepare_dataset_version(error_dataset_version, current_time)
        self.assert_dataset_version_preparation(dataset_version, current_time)

    def test_prepare_dataset_version_weeding(self):
        current_time = now()
        complete_dataset_version = self.complete.versions.first()
        with patch.object(self.complete, "weed_document", lambda doc: doc.id % 2):
            dataset_version = self.complete.prepare_dataset_version(complete_dataset_version, current_time)
        self.assert_dataset_version_preparation(dataset_version, current_time, 2)
        self.assertEqual(list(dataset_version.documents.values_list("id", flat=True)), [4, 6],
                         "Expected weed_document to filter out Documents it returns True for")

    def test_prepare_dataset_version_empty(self):
        current_time = now()
        empty_dataset_version = self.empty.versions.first()
        dataset_version = self.empty.prepare_dataset_version(empty_dataset_version, current_time)
        self.assert_dataset_version_preparation(dataset_version, current_time, document_count=0)

    def test_get_collection_factories(self):
        collection_factories = self.instance.get_collection_factories()
        self.assertEqual(list(collection_factories.keys()), ["setting1=const&test"])
        self.assertIsInstance(collection_factories["setting1=const&test"], DataStorageFactory)
        self.assertEqual(collection_factories["setting1=const&test"].defaults["identifier"], "id")
        self.assertIsNone(collection_factories["setting1=const&test"].defaults["referee"])
        with patch.object(Dataset, "COLLECTION_IDENTIFIER", None):
            collection_factories = self.instance.get_collection_factories()
            self.assertEqual(list(collection_factories.keys()), ["setting1=const&test"])
            self.assertIsInstance(collection_factories["setting1=const&test"], DataStorageFactory)
            self.assertIsNone(collection_factories["setting1=const&test"].defaults["identifier"])
            self.assertIsNone(collection_factories["setting1=const&test"].defaults["referee"])
        with patch.object(Dataset, "COLLECTION_REFEREE", "referee"):
            collection_factories = self.instance.get_collection_factories()
            self.assertEqual(list(collection_factories.keys()), ["setting1=const&test"])
            self.assertIsInstance(collection_factories["setting1=const&test"], DataStorageFactory)
            self.assertEqual(collection_factories["setting1=const&test"].defaults["identifier"], "id")
            self.assertEqual(collection_factories["setting1=const&test"].defaults["referee"], "referee")

    def test_get_seeding_factories(self):
        seeding_phases = self.instance.get_seeding_factories()
        self.assertEqual(list(seeding_phases.keys()), ["setting1=const&test"],
                         "Expected default collection to get a name equal to the Dataset signature")
        self.assertIsInstance(seeding_phases["setting1=const&test"], SeedingProcessorFactory)
        self.assertEqual(seeding_phases["setting1=const&test"].defaults["phases"], [
            {
                "phase": "papers",
                "strategy": "initial",
                "batch_size": 5,
                "retrieve_data": {
                    "resource": "resources.EntityListResource",
                    "method": "get",
                    "args": [],
                    "kwargs": {},
                    "continuation_limit": 2,
                    "setting0": "private"

                },
                "contribute_data": {
                    "objective": {
                        "id": "$.id",
                        "state": "$.state",
                        "doi": "$.doi",
                        "title": "$.title",
                        "abstract": "$.abstract",
                        "authors": "$.authors",
                        "url": "$.url",
                        "published_at": "$.published_at",
                        "modified_at": "$.modified_at",
                        "@": "$.results"
                    },
                    "$setting1": "const",
                }
            }
        ], "Expected Dataset.SEEDING_PHASES to be the seeding phases for the default collection")

    def test_get_task_definitions(self):
        task_definitions = self.instance.get_task_definitions()
        self.assertEqual(task_definitions, {
            "document": {
                "check_doi": {
                    "depends_on": [
                        "$.state",
                        "$.doi"
                    ],
                    "checks": [],
                    "resources": []
                }
            },
            "collection": {},
            "datasetversion": {}
        })
        with patch.object(Dataset, "DOCUMENT_TASKS", {}):
            task_definitions = self.instance.get_task_definitions()
            self.assertEqual(task_definitions, {
                "document": {},
                "collection": {},
                "datasetversion": {}
            })
        with patch.object(Dataset, "COLLECTION_TASKS", {"test": "test"}):
            task_definitions = self.instance.get_task_definitions()
            self.assertEqual(task_definitions["collection"], {"test": "test"})
        with patch.object(Dataset, "DATASET_VERSION_TASKS", {"test": "test"}):
            task_definitions = self.instance.get_task_definitions()
            self.assertEqual(task_definitions["datasetversion"], {"test": "test"})
