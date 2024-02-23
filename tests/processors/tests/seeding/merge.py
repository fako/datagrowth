from copy import deepcopy
from unittest.mock import patch

from datagrowth.processors import HttpSeedingProcessor

from project.entities.constants import PAPER_DEFAULTS, EntityStates
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
            "objective": OBJECTIVE
        }
    }
]


EXCLUSIVE_DELETE_MERGE_PARAMETERS = {
    "size": 20,
    "page_size": 10,
    "deletes": -1  # deletes all seeds
}


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

    @patch.object(EntityIdListResource, "PARAMETERS", EXCLUSIVE_DELETE_MERGE_PARAMETERS)
    def test_exclusive_deletes(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")
        self.assert_results(results)
        self.assert_documents(expected_documents=0)

    def test_composition_to(self):
        seeding_phases = deepcopy(SEEDING_PHASES)
        seeding_phases[1]["contribute_data"]["composition_to"] = "details"
        processor = HttpSeedingProcessor(self.collection, {
            "phases": seeding_phases
        })
        results = processor("paper")

        expected_detail_properties = sorted(list(self.seed_defaults.keys()))
        for batch in results:
            self.assertIsInstance(batch, list)
            for result in batch:
                self.assertIn("id", result.properties)
                self.assertIn("details", result.properties)
                self.assertEqual(sorted(result.properties["details"].keys()), expected_detail_properties)
        self.assert_documents(expected_documents=10)

    def test_buffer_base_composition_to(self):
        seeding_phases = deepcopy(SEEDING_PHASES)
        seeding_phases[1]["contribute_data"]["composition_to"] = "source"
        seeding_phases[1]["contribute_data"]["merge_base"] = "buffer"
        processor = HttpSeedingProcessor(self.collection, {
            "phases": seeding_phases
        })
        results = processor("paper")

        for batch in results:
            self.assertIsInstance(batch, list)
            for result in batch:
                self.assertEqual(result.properties["source"], {"id": result.properties["id"]})
                self.assert_result_document(result, extra_properties=["source"])
        self.assert_documents(expected_documents=10)

    def test_invalid_base(self):
        seeding_phases = deepcopy(SEEDING_PHASES)
        seeding_phases[1]["contribute_data"]["composition_to"] = "source"
        seeding_phases[1]["contribute_data"]["merge_base"] = "invalid"
        processor = HttpSeedingProcessor(self.collection, {
            "phases": seeding_phases
        })
        self.assertRaises(ValueError, lambda inp: list(processor(inp)), "paper")

    def test_custom_merge_on(self):
        # Create custom Collection to play around with identifier value freely
        Collection = type(self.collection)
        custom_merge_on_collection = Collection.objects.create(
            name="custom_merge_on",
            dataset_version=self.dataset_version,
            identifier="url"  # setting identifier to something else than merge_to
        )
        custom_merge_on_collection.documents.add(self.ignored_document)
        # Setup the seeding phases
        seeding_phases = deepcopy(SEEDING_PHASES)
        seeding_phases[1]["contribute_data"]["composition_to"] = "source"
        seeding_phases[1]["contribute_data"]["merge_base"] = "buffer"
        seeding_phases[1]["contribute_data"]["merge_on"] = "id"
        processor = HttpSeedingProcessor(custom_merge_on_collection, {
            "phases": seeding_phases
        })
        results = processor("paper")

        for batch in results:
            self.assertIsInstance(batch, list)
            for result in batch:
                self.assertNotIn("id", result.properties,
                                 "Expected non-identifier merge_on value to be excluded from properties")
                self.assertIn("id", result.properties["source"],
                              "Expected non-identifier merge_on value to occur in composition data")
                result.properties["id"] = result.properties["source"]["id"]  # mocking value for assert_result_document
                self.assert_result_document(result, extra_properties=["source"], collection=custom_merge_on_collection)
        self.assert_documents(expected_documents=10, collection=custom_merge_on_collection)


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

    @patch.object(EntityIdListResource, "PARAMETERS", EXCLUSIVE_DELETE_MERGE_PARAMETERS)
    def test_exclusive_deletes(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("paper")

        # The id list endpoint will not return deleted ids.
        # So the metadata that's deleted will never be retrieved.
        # Therefor the "deleted" test Document will never actually be deleted.
        # It is up to the Dataset and its growth_strategy to handle or ignore deletes like this.
        self.assert_results(results)
        self.assert_documents(expected_documents=4)  # there are 4 pre-existing documents in delta data
        for doc in self.collection.documents.all():
            if doc.id != self.undeleted_paper.id:
                self.assertEqual(doc.properties["state"], EntityStates.OPEN)
            else:
                self.assertEqual(doc.properties["state"], EntityStates.DELETED)
