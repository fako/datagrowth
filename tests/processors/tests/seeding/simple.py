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


DELTA_PARAMETERS = {
    "size": 20,
    "page_size": 10,
    "deletes": 3  # deletes the 1st seed and every 3rd seed after that
}


class TestSimpleDeltaHttpSeedingProcessor(HttpSeedingProcessorTestCase):

    seed_defaults = PAPER_DEFAULTS

    def setUp(self) -> None:
        super().setUp()
        self.setup_delta_data()

    @patch.object(EntityListResource, "PARAMETERS", DELTA_PARAMETERS)
    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")

        self.assert_results(results)
        self.assert_documents()
        self.assert_delta_documents()
