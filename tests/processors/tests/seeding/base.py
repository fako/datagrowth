from django.test import TestCase
from django.utils.timezone import now

from datatypes.models import Dataset, Document
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
    def create_document(cls, properties):
        document = Document(
            dataset_version=cls.dataset_version,
            collection=cls.collection,
            task_results={
                "check_doi": {
                    "success": True
                }
            },
            properties=properties,
            pending_at=None,
            finished_at=cls.current_time
        )
        document.clean()
        document.save()
        return document

    @classmethod
    def setup_dataset_data(cls):
        cls.dataset = Dataset.objects.create()
        cls.dataset_version = cls.dataset.create_dataset_version()
        cls.collection = cls.dataset_version.collections.first()
        cls.ignored_document = cls.create_document({
            "state": "active"
        })
        # We reload the ignored_document here, because Django will cause very minor updates while reloading,
        # that we want to ignore for the tests
        cls.ignored_document = Document.objects.get(id=cls.ignored_document.id)
        cls.preexisting_documents.add(cls.ignored_document.id)

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

    def assert_delta_documents(self, assert_deleted=True):
        # Assert delete document
        if assert_deleted:
            deleted_paper = Document.objects.get(id=self.deleted_paper.id)
            self.assertEqual(deleted_paper.properties["state"], EntityStates.DELETED)

        # Assert update document
        updated_paper = Document.objects.get(id=self.updated_paper.id)
        self.assertEqual(updated_paper.properties["title"], "Title for 1", "Expected the title to get updated")
        self.assertIsNone(updated_paper.pending_at, "Did not expect title change to set Document as pending")
        self.assertIn(
            "check_doi", updated_paper.task_results,
            "Expected pre-existing document without relevant update to keep any task_results state"
        )
        self.assertEqual(
            updated_paper.finished_at, self.current_time,
            "Expected title change not to change finished_at value"
        )

        # Assert unchanged document
        unchanged_paper = Document.objects.get(id=self.unchanged_paper.id)
        self.assertEqual(unchanged_paper.properties["title"], "Title for 2", "Expected the title to remain as-is")
        self.assertIsNone(
            unchanged_paper.pending_at,
            "Expected pre-existing document without update to not become pending for tasks"
        )
        self.assertEqual(
            unchanged_paper.finished_at, self.current_time,
            "Expected unchanged document to keep finished_at same as at start of test"
        )
        self.assertIn(
            "check_doi", unchanged_paper.task_results,
            "Expected pre-existing document without update to keep any task_results state"
        )

        # Assert undeleted document
        undeleted_paper = Document.objects.get(id=self.undeleted_paper.id)
        self.assertEqual(undeleted_paper.properties["state"], EntityStates.OPEN, "Expected state to become open")
        self.assertEqual(undeleted_paper.properties["title"], "Title for 4", "Expected the title to remain as-is")
        self.assertIsNotNone(undeleted_paper.pending_at, "Expect state change to set Document as pending")
        self.assertEqual(undeleted_paper.task_results, {}, "Expected state change to reset task_results")
        self.assertIsNone(undeleted_paper.finished_at, "Expected state change to mark Document as unfinished")
