from datatypes.tests import data_storage
from datatypes.models import Dataset, DatasetVersion, Collection, Document


class TestDatasetVersion(data_storage.DataStorageTestCase):

    fixtures = ["test-data-storage"]

    def setUp(self) -> None:
        super().setUp()
        self.instance = DatasetVersion.objects.get(id=1)

    def test_build(self):
        dataset = Dataset()
        dataset_version = DatasetVersion.build(dataset)
        self.assertEqual(dataset_version.dataset, dataset)
        self.assertEqual(dataset_version.growth_strategy, dataset.GROWTH_STRATEGY)
        self.assertEqual(dataset_version.task_definitions, dataset.get_task_definitions())
        self.assertIsNotNone(dataset_version.pending_at)
        self.assertIsNone(dataset_version.finished_at)

    def test_copy_collection(self):
        collection = Collection.objects.get(id=2)
        self.assertIsNone(collection.dataset_version, "Expected test collection to not be connected to DatasetVersion")
        copied_collection = self.instance.copy_collection(collection)
        self.assertNotEqual(copied_collection, collection)
        self.assertNotEqual(copied_collection.id, 2, "Expected copied collection to get a new id")
        self.assertEqual(copied_collection.dataset_version, self.instance)
        self.assertTrue(copied_collection.documents.count() > 0)
        self.assertEqual(copied_collection.documents.count(), collection.documents.count())
        document = collection.documents.first()
        copied_document = copied_collection.documents.first()
        self.assertEqual(document.properties, copied_document.properties)

    def test_influence_collection(self):
        collection = Collection.objects.get(id=2)
        self.assertIsNone(collection.dataset_version, "Expected test collection to not be connected to DatasetVersion")
        self.instance.influence(collection)
        self.assertEqual(collection.dataset_version, self.instance)
        self.assertEqual(collection.tasks, self.instance.task_definitions["collection"])

    def test_influence_document(self):
        document = Document.objects.get(id=4)
        self.assertIsNone(document.dataset_version, "Expected test document to not be connected to DatasetVersion")
        self.instance.influence(document)
        self.assertEqual(document.dataset_version, self.instance)
        self.assertEqual(document.tasks, self.instance.task_definitions["document"])

    def test_indirect_document_influence(self):
        collection = Collection.objects.get(id=1)
        self.assertIsNotNone(collection.dataset_version,
                             "Expected test collection to be connected to DatasetVersion")
        document = Document.objects.get(id=4)
        self.assertIsNone(document.dataset_version, "Expected test document to not be connected to DatasetVersion")
        collection.influence(document)
        self.assertEqual(document.dataset_version, self.instance)
        self.assertEqual(document.tasks, self.instance.task_definitions["document"])
