from django.test import TestCase
from django.utils.timezone import now

from datatypes.models import Dataset, DatasetVersion, Collection, Document
from project.entities.constants import EntityStates


class HttpSeedingProcessorTestCase(TestCase):

    seed_defaults = {}
    current_time = None

    dataset = None
    dataset_version = None
    collection = None
    ignored_document = None
    preexisting_documents = set()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.current_time = now()
        cls.setup_dataset_data()

    @classmethod
    def setup_dataset_data(cls):
        cls.dataset = Dataset.objects.create()
        cls.dataset_version = DatasetVersion.objects.create(dataset=cls.dataset)
        cls.collection = Collection.objects.create(name="test", identifier="id", dataset_version=cls.dataset_version)
        cls.ignored_document = Document(
            collection=cls.collection,
            task_results={},
            properties={
                "state": "active"
            },
            pending_at=None,
            finished_at=cls.current_time
        )
        cls.ignored_document.clean()
        cls.ignored_document.save()
        # We reload the ignored_document here, because Django will cause very minor updates while reloading,
        # that we want to ignore for the tests
        cls.ignored_document = Document.objects.get(id=cls.ignored_document.id)
        cls.preexisting_documents.add(cls.ignored_document.id)

    def create_document(self, properties):
        document = Document(
            dataset_version=self.dataset_version,
            collection=self.collection,
            task_results={
                "check_doi": {
                    "success": True
                }
            },
            properties=properties,
            pending_at=None,
            finished_at=self.current_time
        )
        document.clean()
        document.save()
        return document

    def setup_delta_data(self):
        self.deleted_paper = self.create_document({
            "id": 0,
            "state": EntityStates.OPEN,
            "doi": "https://doi.org/10.0",
            "title": "Title for 0",
            "abstract": "Abstract for 0",
            "authors": [],
            "url": "https://science.org/0.pdf",
            "published_at": None,
            "modified_at": None
        })
        self.updated_paper = self.create_document({
            "id": 1,
            "state": EntityStates.OPEN,
            "doi": "https://doi.org/10.1",
            "title": "This is going to change",
            "abstract": "Abstract for 1",
            "authors": [],
            "url": "https://nature.org/1.pdf",
            "published_at": None,
            "modified_at": None
        })
        self.unchanged_paper = self.create_document({
            "id": 2,
            "state": EntityStates.OPEN,
            "doi": "https://doi.org/10.2",
            "title": "Title for 2",
            "abstract": "Abstract for 2",
            "authors": [],
            "url": "https://academic.oup.com/2.pdf",
            "published_at": None,
            "modified_at": None
        })
        self.undeleted_paper = self.create_document({
            "id": 4,
            "state": EntityStates.DELETED,
            "doi": "https://doi.org/10.4",
            "title": "Title for 4",
            "abstract": "Abstract for 4",
            "authors": [],
            "url": "https://academic.oup.com/4.pdf",
            "published_at": None,
            "modified_at": None
        })
        # These will get added multiple times to the class instance,
        # but that won't affect test results.
        self.preexisting_documents.add(self.deleted_paper.id)
        self.preexisting_documents.add(self.updated_paper.id)
        self.preexisting_documents.add(self.unchanged_paper.id)
        self.preexisting_documents.add(self.undeleted_paper.id)

    def assert_result_document(self, document, extra_properties):
        extra_properties = extra_properties or []
        self.assertIsInstance(document, Document)
        self.assertIsNotNone(document.id, "Expected a Document saved to the database")
        self.assertEqual(document.collection_id, self.collection.id, "Expected a Document as part of test Collection")
        self.assertEqual(document.dataset_version.id, self.dataset_version.id,
                         "Expected Document to specify the DatasetVersion")
        self.assertIsNotNone(document.identity, "Expected Collection to prescribe the identity for Document")
        expected_properties = sorted(list(self.seed_defaults.keys()) + extra_properties)
        self.assertEqual(sorted(document.properties.keys()), expected_properties)

    def assert_results(self, results, extra_properties=None):
        # Assert results
        for batch in results:
            self.assertIsInstance(batch, list)
            for result in batch:
                self.assert_result_document(result, extra_properties)
                if result.id not in self.preexisting_documents:
                    self.assertFalse(result.task_results, "Expected Document without further task processing")
                    self.assertFalse(result.derivatives, "Expected Document without processing results")
                    self.assertTrue(result.pending_at, "Expected new Document to be pending for processing")
                    self.assertIsNone(result.finished_at, "Expected new Documents to not be finished")

    def assert_documents(self, expected_documents=20):
        self.assertEqual(
            self.collection.documents.count(), expected_documents + 1,
            f"Expected {expected_documents} generated documents and one pre-existing unchanged document"
        )
        # Pre-existing documents that are not in the harvest data should be left alone
        ignored_document = Document.objects.get(id=self.ignored_document.id)
        self.assertEqual(ignored_document.identity, self.ignored_document.identity)
        self.assertEqual(ignored_document.task_results, self.ignored_document.task_results)
        self.assertEqual(ignored_document.properties, self.ignored_document.properties)
        self.assertEqual(ignored_document.derivatives, self.ignored_document.derivatives)
        self.assertIsNone(ignored_document.pending_at)
        self.assertIsNotNone(ignored_document.finished_at)
