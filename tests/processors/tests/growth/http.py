from django.test import TestCase

from datagrowth.configuration import register_defaults
from datagrowth.processors import HttpGrowthProcessor

from datatypes.models import Collection, Batch, ProcessResult


class TestHttpGrowthProcessor(TestCase):

    fixtures = ["test-http-growth"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        register_defaults("global", {
            "cache_only": True
        })

    @classmethod
    def tearDownClass(cls):
        register_defaults("global", {
            "cache_only": False
        })
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.collection = Collection.objects.get(id=3)

    def test_synchronous_update(self):
        processor = HttpGrowthProcessor({
            "growth_phase": "test",
            "datatypes_app_label": "datatypes",
            "batch_size": 2,
            "asynchronous": False,
            "retrieve_data": {
                "resource": "resources.httpresourcemock",
                "method": "get",
                "args": ["$.resource"],
                "kwargs": {},
            },
            "contribute_data": {
                "objective": {
                    "@": "$.0",
                    "extra": "$.extra"
                }
            }
        })
        processor(self.collection.documents)
        self.assertEqual(self.collection.documents.count(), 3)
        for ix, document in enumerate(self.collection.documents.all()):
            self.assertEqual(document.derivatives, {"test": {"extra": f"test {ix}"}})
        self.assertEqual(Batch.objects.count(), 2)
        for batch in Batch.objects.all():
            self.assertEqual(batch.documents.count(), 0, "Expected all batch instances to have zero documents")
        self.assertEqual(
            ProcessResult.objects.count(), 0,
            "Expected all ProcessResults to be cleared after successful processing to release Document locks"
        )

    def test_asynchronous_update(self):
        self.skipTest("Redis should get enabled")
        processor = HttpGrowthProcessor({
            "datatypes_app_label": "datatypes",
            "batch_size": 2
        })
        processor(self.collection.documents)
        self.assertEqual(self.collection.documents.count(), 3)
        self.assertEqual(Batch.objects.count(), 2)
        self.assertEqual(ProcessResult.objects.count(), 3)
