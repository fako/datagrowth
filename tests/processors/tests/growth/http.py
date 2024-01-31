import logging
from unittest.mock import patch

from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from datagrowth.configuration import register_defaults
from datagrowth.processors import HttpGrowthProcessor

from datatypes.models import Collection, Batch, ProcessResult


class TestHttpGrowthProcessor(TestCase):

    fixtures = ["test-http-growth"]

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        register_defaults("global", {
            "cache_only": True,
            "resource_exception_log_level": logging.WARNING
        })

    @classmethod
    def tearDownClass(cls):
        register_defaults("global", {
            "cache_only": False,
            "resource_exception_log_level": logging.DEBUG
        })
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.collection = Collection.objects.get(id=3)

    def assert_batch_and_process_results(self, batch_count=2):
        self.assertEqual(Batch.objects.count(), batch_count)
        for batch in Batch.objects.all():
            self.assertEqual(batch.documents.count(), 0, "Expected all batch instances to have zero documents")
        self.assertEqual(
            ProcessResult.objects.count(), 0,
            "Expected all ProcessResults to be cleared after successful processing to release Document locks"
        )

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
        self.assert_batch_and_process_results()

    def test_synchronous_to_property(self):
        processor = HttpGrowthProcessor({
            "growth_phase": "test",
            "datatypes_app_label": "datatypes",
            "batch_size": 2,
            "asynchronous": False,
            "to_property": "properties/results",
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
            self.assertEqual(document.properties["results"], {"extra": f"test {ix}"})
        self.assert_batch_and_process_results()

    def test_synchronous_depends_on(self):
        # Setting the dependency on documents
        success, failure, unknown = list(self.collection.documents.all())
        success.task_results = {"dependency": {"success": True}}
        success.save()
        failure.task_results = {"dependency": {"success": False}}
        failure.save()
        # Calling processor with depends_on set
        processor = HttpGrowthProcessor({
            "growth_phase": "test",
            "datatypes_app_label": "datatypes",
            "batch_size": 2,
            "asynchronous": False,
            "depends_on": "dependency",
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
        # Asserting results
        self.assertEqual(self.collection.documents.count(), 3)
        for ix, document in enumerate(self.collection.documents.all()):
            if document.id == success.id:
                self.assertEqual(document.derivatives, {"test": {"extra": f"test {ix}"}})
            else:
                self.assertEqual(document.derivatives, {})
        self.assert_batch_and_process_results(batch_count=1)

    def test_synchronous_apply_resource_to(self):
        processor = HttpGrowthProcessor({
            "growth_phase": "test",
            "datatypes_app_label": "datatypes",
            "batch_size": 2,
            "asynchronous": False,
            "apply_resource_to": ["reference"],
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
            self.assertEqual(document.reference, "200", "Expected Documents to take on Resource status as a reference")

    def test_synchronous_document_lock(self):
        # Setting a lock on a single document
        result_type = ContentType.objects.get_by_natural_key("resources", "httpresourcemock")
        locked, free, _ = list(self.collection.documents.all())
        batch = Batch.objects.create()
        locked_process_result = ProcessResult.objects.create(batch=batch, document=locked, result_type=result_type)
        free_process_result = ProcessResult.objects.create(batch=batch, document=free)
        # Calling processor like normal
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
        # Release the test locks to assert Batch and ProcessResult
        locked_process_result.delete()
        free_process_result.delete()
        # Asserting results
        self.assertEqual(self.collection.documents.count(), 3)
        for ix, document in enumerate(self.collection.documents.all()):
            if document.id == locked.id:
                self.assertEqual(document.derivatives, {})
            else:
                self.assertEqual(document.derivatives, {"test": {"extra": f"test {ix}"}})
        self.assert_batch_and_process_results()

    def test_synchronous_pass_resource_through(self):
        processor = HttpGrowthProcessor({
            "growth_phase": "test",
            "datatypes_app_label": "datatypes",
            "batch_size": 2,
            "asynchronous": False,
            "extractor": "ExtractProcessor.pass_resource_through",
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
            expected_data = {"test": {"extra": f"test {ix}", "value": f"nested value {ix}"}}
            if ix == 2:  # one resource specifies a next request and here we take that into account
                expected_data["test"]["next"] = 1
            self.assertEqual(document.derivatives, expected_data)
        self.assert_batch_and_process_results()

    def test_synchronous_multi_contributions(self):

        def reduce_contributions(obj, contributions):
            result = ""
            for contribution in contributions:
                result += contribution["extra"] + " & "
            result = result.strip(" &")
            return {
                "extra": result
            }

        with patch.object(HttpGrowthProcessor, "reduce_contributions", reduce_contributions):
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
                    "continuation_limit": 2,
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
            expected_data = {"test": {"extra": f"test {ix}"}}
            if ix == 2:
                # This resource specifies a next request and resource values get concatenated by the reduce method.
                # So we reflect that here in the expectation.
                expected_data["test"]["extra"] += " & test 3"
            self.assertEqual(document.derivatives, expected_data)
        self.assert_batch_and_process_results()
