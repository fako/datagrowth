from unittest.mock import patch

from datagrowth.processors import HttpSeedingProcessor

from project.entities.constants import PAPER_DEFAULTS
from processors.tests.seeding.base import HttpSeedingProcessorTestCase
from resources.models import EntityIdListResource, EntityDetailResource


OBJECTIVE = {
    key: f"$.{key}"
    for key in PAPER_DEFAULTS.keys()
}
OBJECTIVE["@"] = "$"


SEEDING_PHASES = [
    {
        "phase": "ids",
        "strategy": "initial",
        "batch_size": 5,
        "retrieve_data": {
            "resource": "resources.EntityIdListResource",
            "method": "get",
            "args": [],
            "kwargs": {},
        },
        "contribute_data": {
            "objective": {
                "@": "$",
                "id": "$.id"
            }
        }
    },
    {
        "phase": "details",
        "strategy": "merge",
        "batch_size": None,
        "retrieve_data": {
            "resource": "resources.EntityDetailResource",
            "method": "get",
            "args": [
                "#.args.0",  # will resolve to the first argument of the call to the processor
                "$.id"
            ],
            "kwargs": {},
        },
        "contribute_data": {
            "merge_on": "id",
            "objective": OBJECTIVE
        }
    }
]


class TestMergeHttpSeedingProcessor(HttpSeedingProcessorTestCase):

    seed_defaults = PAPER_DEFAULTS

    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")

        self.assert_results(results)
        self.assert_documents(expected_documents=10)

        # Assert list resource
        self.assertEqual(
            EntityIdListResource.objects.all().count(), 1,
            "Expected one requests to list mock data endpoints"
        )
        list_resource = EntityIdListResource.objects.first()
        self.assertTrue(list_resource.success)
        self.assertEqual(list_resource.request["args"], ["paper"])
        # Assert detail resources
        self.assertEqual(
            EntityDetailResource.objects.all().count(), 10,
            "Expected one request to detail mock data endpoints for each element in list data response"
        )
        for ix, resource in enumerate(EntityDetailResource.objects.all()):
            self.assertTrue(resource.success)
            self.assertEqual(resource.request["args"], ["paper", ix])


DELTA_PARAMETERS = {
    "size": 20,
    "page_size": 10,
    "deletes": 3  # deletes the 1st seed and every 3rd seed after that
}


class TestMergeDeltaHttpSeedingProcessor(HttpSeedingProcessorTestCase):
    """
    The setup of this test will use a generator that creates deleted documents.
    When running the seeder this should un-delete almost all seeds and
    shouldn't update the metadata from generated documents, unless real updates came through the seeder.
    """

    seed_defaults = PAPER_DEFAULTS

    def setUp(self) -> None:
        super().setUp()
        self.setup_delta_data()

    @patch.object(EntityIdListResource, "PARAMETERS", DELTA_PARAMETERS)
    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")

        # The id list endpoint will not return deleted ids.
        # So the metadata that's deleted will never be retrieved.
        # Therefor the "deleted" test Document will never actually be deleted.
        # It is up to the Dataset and its growth_strategy to handle or ignore deletes like this.
        expected_documents = 14
        self.assert_results(results)
        self.assert_documents(expected_documents=expected_documents)
        self.assert_delta_documents(assert_deleted=False)
