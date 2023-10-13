from unittest.mock import patch

from datagrowth.processors import HttpSeedingProcessor

from project.entities.constants import PAPER_DEFAULTS, EntityStates
from processors.tests.seeding.base import HttpSeedingProcessorTestCase
from datatypes.models import Document
from resources.models import EntityListResource


OBJECTIVE = {
    key: f"$.{key}"
    for key in PAPER_DEFAULTS.keys()
}
OBJECTIVE["@"] = "$.results"


SEEDING_PHASES = [
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
        },
        "contribute_data": {
            "objective": OBJECTIVE
        }
    }
]


class TestSimpleHttpSeedingProcessor(HttpSeedingProcessorTestCase):

    seed_defaults = PAPER_DEFAULTS

    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")

        self.assert_results(results)
        self.assert_documents()

        # Assert resources
        self.assertEqual(EntityListResource.objects.all().count(), 2, "Expected two requests to entity list endpoint")
        for resource in EntityListResource.objects.all():
            self.assertTrue(resource.success)
            self.assertEqual(resource.request["args"], ["paper"])


UPDATE_PARAMETERS = {
    "size": 20,
    "page_size": 10,
    "deletes": 3  # deletes the 1st seed and every 3rd seed after that
}


class TestSimpleDeltaHttpSeedingProcessor(HttpSeedingProcessorTestCase):

    seed_defaults = PAPER_DEFAULTS

    def setUp(self) -> None:
        super().setUp()
        self.setup_delta_data()

    @patch.object(EntityListResource, "PARAMETERS", UPDATE_PARAMETERS)
    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")

        self.assert_results(results)
        self.assert_documents()

        # Assert delete document
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
