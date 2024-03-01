from unittest.mock import patch

from django.test import override_settings

from datatypes.tests.dataset import base as test_cases
from datatypes.models import Dataset, DatasetVersion, Document
from resources.models import EntityListResource


class TestInitialDatasetReviseStrategy(test_cases.BaseDatasetTestCase):

    dataset_model = Dataset
    signature = "setting1=const&test"
    entity_type = "paper"

    def test_growth_success(self):
        self.dataset.grow(self.entity_type, asynchronous=False)
        self.assert_grow_success(dataset_versions=1, collections=1, documents=20)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=20)
        self.assert_dataset_finish()

    def test_growth_limit(self):
        # This test sets the limit to 3.
        # However the batch_size is 5 and therefor we expect to grow 5 Documents.
        self.dataset.grow(self.entity_type, asynchronous=False, limit=3)
        self.assert_grow_success(dataset_versions=1, collections=1, documents=5)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=5)
        self.assert_dataset_finish()

    def test_seeding_error(self):
        self.dataset.grow("does_not_exist", asynchronous=False)
        self.assert_grow_success(dataset_versions=1, collections=1, documents=0)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=0)
        entity_list_resource = EntityListResource.objects.last()
        dataset_version = DatasetVersion.objects.first()
        self.assertEqual(dataset_version.errors, {
            "tasks":  {
                "check_doi": {
                    "fail": 0,
                    "skipped": 0,
                    "success": 0
                }
            },
            "seeding": {
                "resources.entitylistresource": {
                    "id": entity_list_resource.id,
                    "ids": [entity_list_resource.id],
                    "success": False,
                    "resource": "resources.entitylistresource"
                }
            }
        })
        self.assert_dataset_finish()

    def test_task_error(self):
        with override_settings(TEST_CHECK_DOI_FAILURE_IDENTITIES=["1"]):
            self.dataset.grow(self.entity_type, asynchronous=False)
        self.assert_initial_grow_failure(dataset_versions=1, collections=1, documents=19, error_documents=1)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=20)
        dataset_version = DatasetVersion.objects.first()
        self.assertEqual(dataset_version.errors, {
            "tasks": {
                "check_doi": {
                    "fail": 1,
                    "skipped": 0,
                    "success": 19
                }
            },
            "seeding": {}
        })
        self.assert_dataset_finish()


class TestContinuationDatasetReviseStrategy(test_cases.BaseDatasetTestCase):

    dataset_model = Dataset
    signature = "setting1=const&test"
    entity_type = "paper"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.create_historic_dataset_version()

    @patch.object(EntityListResource, "PARAMETERS", {"size": 3, "page_size": 10})
    def test_growth_success(self):
        # Prepare test data
        disappearing_title = "This title should disappear. It is overwritten by new entities"
        remaining_title = "This title should remain. It is copied from old entities"
        self.prepare_documents(properties={
            "2": {
                "title": disappearing_title
            },
            "4": {
                "title": remaining_title
            }
        })
        # Execute growth
        self.dataset.grow(self.entity_type, asynchronous=False)
        # Standard assertions
        self.assert_grow_success(dataset_versions=2, collections=2, documents=40)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=20)
        self.assert_dataset_finish()
        # Check if expected updates have taken place
        self.assertEqual(
            Document.objects.filter(properties__title=disappearing_title).count(), 1,
            "Expected disappearing title to be preserved in old data, but overwritten in new data."
        )
        self.assertEqual(
            Document.objects.filter(properties__title=remaining_title).count(), 2,
            "Expected remaining title to be present in old and new data."
        )

    def test_growth_limit(self):
        self.skipTest("not implemented")

    def test_seeding_error(self):
        self.skipTest("not implemented")

    def test_growth_retry(self):
        self.skipTest("not implemented")

    def test_growth_reset(self):
        self.skipTest("not implemented")

    def test_new_task_definition(self):
        self.skipTest("not implemented")
