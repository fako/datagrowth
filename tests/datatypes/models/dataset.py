from collections import OrderedDict

from datagrowth.datatypes import DatasetBase, DatasetVersionBase
from datagrowth.processors import QuerySetProcessor, ProcessorFactory

from project.entities.constants import PAPER_DEFAULTS
from datatypes.models import Document
from processors.processors import MockNumberProcessor, MockFilterProcessor


class StubHarvestProcessor(QuerySetProcessor):
    pass


class DatasetVersion(DatasetVersionBase):
    pass


PAPER_OBJECTIVE = {
    key: f"$.{key}"
    for key in PAPER_DEFAULTS.keys()
}
PAPER_OBJECTIVE["@"] = "$.results"


class Dataset(DatasetBase):

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
                "setting0": "private",
            },
            "contribute_data": {
                "objective": PAPER_OBJECTIVE,
                "$setting1": "const"
            }
        }
    ]
    DOCUMENT_TASKS = {
        "check_doi": {
            "depends_on": ["$.state", "$.doi"],
            "checks": [],
            "resources": []
        }
    }
    HARVEST_PHASES = [
        ProcessorFactory(MockNumberProcessor, method="number_documents"),
        ProcessorFactory("MockFilterProcessor.filter_documents", defaults={
            "$setting2": "variable",
            "$include_even": False
        }),
    ]

    COMMUNITY_SPIRIT = OrderedDict([
        ("phase1", {
            "process": "HttpResourceProcessor.fetch",
            "input": None,
            "contribute": "Append:ExtractProcessor.extract_from_resource",
            "errors": {
                502: "unreachable",
                404: "not_found"
            },
            "schema": {
                "additionalProperties": False,
                "required": ["context", "value"],
                "type": "object",
                "properties": {
                    "context": {"type": "string"},
                    "value": {"type": "string"}
                }
            },
            "output": "Collective#value",
        }),
        ("phase2", {
            "process": "HttpResourceProcessor.fetch_mass",
            "input": "@phase1",
            "contribute": "Append:ExtractProcessor.extract_from_resource",
            "errors": {},
            "schema": {
                "additionalProperties": False,
                "required": ["context", "value"],
                "type": "object",
                "properties": {
                    "context": {"type": "string"},
                    "value": {"type": "string"}
                }
            },
            "output": "&input"
        }),
        ("phase3", {
            "process": "HttpResourceProcessor.fetch_mass",
            "input": "@phase2",
            "contribute": None,
            "errors": {},
            "output": "Individual",
            "schema": {}
        })
    ])

    COMMUNITY_BODY = [
        {
            "process": "MockNumberProcessor.number_individuals",
            "config": {}
        },
        {
            "name": "filter_individuals",
            "process": "MockFilterProcessor.filter_individuals"
        },
    ]

    CONFIG = {
        "setting3": "const",
        "$setting4": "variable",
        "document": "datatypes.Document"
    }

    @property
    def version(self):
        return "0.0.2"

    # @property
    # def pipelines(self):
    #     return {
    #         "seeder": None,
    #         "growth": [
    #             (DataProcessor, {
    #                 "_args": ["$.test"],
    #                 "_kwargs": {},
    #                 "_resource": "HttpResourceMock",
    #                 "_objective": {
    #                     "@": "$.dict.list",
    #                     "value": "$",
    #                     "#context": "$.dict.test"
    #                 },
    #                 "setting0": "private",
    #                 "$setting1": "const"
    #             }),
    #             (DataProcessor, {
    #                 "_args": ["$.value"],
    #                 "_kwargs": {},
    #                 "_resource": "HttpResourceMock",
    #                 "_objective": {
    #                     "@": "$.dict.list",
    #                     "value": "$",
    #                     "#context": "$.dict.test"
    #                 }
    #             }),
    #             (DataProcessor, {
    #                 "_args": ["$.value"],
    #                 "_kwargs": {},
    #                 "_resource": "HttpResourceMock",
    #             })
    #         ],
    #         "harvest": [
    #             (DataProcessor, {}),
    #             (DataProcessor, {
    #                 "$setting2": "variable",
    #                 "$include_even": False
    #             })
    #         ]
    #     }

    def gather_seeds(self, *args):
        return [
            Document.objects.create(properties={"test": "test", "input": args})
        ]

    def begin_phase1(self, inp):
        return

    def finish_phase2(self, out, err):
        return

    def error_phase1_unreachable(self, err, out):
        return True  # continue if there are results

    def error_phase1_not_found(self, err, out):
        return False  # abort community

    def before_filter_individuals_manifestation(self, part):
        return

    def set_kernel(self):
        self.kernel = self.growth_set.filter(type="phase3").last().output
        super(CommunityMock, self).set_kernel()


class DatasetMock(DatasetBase):

    SEEDING_PHASES = [
        {
            "phase": "mock",
            "strategy": "initial",
            "batch_size": 5,
        }
    ]
