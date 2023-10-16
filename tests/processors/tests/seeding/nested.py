from typing import Iterator
from unittest.mock import patch

from datagrowth.processors import HttpSeedingProcessor

from project.entities.constants import PAPER_DEFAULTS, EntityStates
from datatypes.models import Collection
from processors.tests.seeding.base import HttpSeedingProcessorTestCase
from resources.models import EntityListResource


def get_nested_seeds(journal_data: dict) -> Iterator[dict]:
    for journal_seed in journal_data["results"]:
        if not journal_seed["papers"] and journal_seed["state"] == EntityStates.DELETED:
            yield {
                "journal_id": journal_seed["id"],
                "state": journal_seed["state"]
            }
        for paper_seed in journal_seed["papers"]:
            paper_seed["journal_id"] = journal_seed["id"],
            paper_seed["state"] = journal_seed["state"]
            yield paper_seed


def back_fill_deletes(seed: dict, collection: Collection) -> Iterator[dict]:
    if not seed["state"] == "deleted":
        yield seed
        return
    for doc in collection.documents.filter(properties__journal_id=seed["journal_id"]):
        doc.properties["state"] = EntityStates.DELETED
        yield doc.properties


OBJECTIVE = {
    key: f"$.{key}"
    for key in PAPER_DEFAULTS.keys()
}
OBJECTIVE["journal_id"] = "$.journal_id"
OBJECTIVE["@"] = get_nested_seeds


SEEDING_PHASES = [
    {
        "phase": "testing",
        "strategy": "initial",
        "batch_size": 5,
        "retrieve_data": {
            "resource": "resources.EntityListResource",
            "method": "get",
            "args": ["journal"],
            "kwargs": {},
            "continuation_limit": 2,
        },
        "contribute_data": {
            "objective": OBJECTIVE
        }
    },
    {
        "phase": "deletes",
        "strategy": "back_fill",
        "batch_size": 5,
        "contribute_data": {
            "callback": back_fill_deletes
        }
    }
]


NESTING_PARAMETERS = {
    "size": 20,
    "page_size": 10,
    "nested": "paper"
}


class TestNestedHttpSeedingProcessor(HttpSeedingProcessorTestCase):

    seed_defaults = PAPER_DEFAULTS

    @patch.object(EntityListResource, "PARAMETERS", NESTING_PARAMETERS)
    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("journal")

        self.assert_results(results, extra_properties=["journal_id"])  # extraction method adds this key to defaults
        self.assert_documents(expected_documents=19)  # due to the way generated nested seeds get divided we loose one

        # Assert resources
        self.assertEqual(EntityListResource.objects.all().count(), 2, "Expected two requests to entity list endpoints")
        for resource in EntityListResource.objects.all():
            self.assertTrue(resource.success)
            self.assertEqual(resource.request["args"], ["journal"])


NESTED_DELETE_PARAMETERS = {
    "size": 20,
    "page_size": 10,
    "nested": "paper",
    "deletes": 4  # deletes the 1st seed and every 4th seed after that
}


class TestNestedDeltaHttpSeedingProcessor(HttpSeedingProcessorTestCase):

    seed_defaults = PAPER_DEFAULTS

    def setUp(self) -> None:
        super().setUp()
        self.setup_delta_data()

    def setup_delta_data(self):
        self.deleted_paper = self.create_document({
            "id": 99,
            "journal_id": 0,  # this journal gets deleted and this paper should follow
            "state": EntityStates.OPEN,
            "doi": "https://doi.org/10.99",
            "title": "Title for 99",
            "abstract": "Abstract for 99",
            "authors": [],
            "url": "https://science.org/99.pdf",
            "published_at": None,
            "modified_at": None
        })
        self.updated_paper = self.create_document({
            "id": 1,
            "journal_id": 2,
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
            "journal_id": 2,
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
            "journal_id": 5,
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

    @patch.object(EntityListResource, "PARAMETERS", NESTED_DELETE_PARAMETERS)
    def test_seeding(self):
        processor = HttpSeedingProcessor(self.collection, {
            "phases": SEEDING_PHASES
        })
        results = processor("journal")

        self.assert_results(results, extra_properties=["journal_id"])
        self.assert_documents(expected_documents=16)
        self.assert_delta_documents()
