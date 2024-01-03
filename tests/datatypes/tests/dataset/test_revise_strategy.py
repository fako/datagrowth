from django.test import override_settings

from datatypes.tests.dataset import base as test_cases
from datatypes.models import Dataset, DatasetVersion
from resources.models import EntityListResource


class TestInitialDatasetReviseStrategy(test_cases.BaseDatasetTestCase):

    dataset_model = Dataset
    signature = "setting1=const&test"
    entity_type = "paper"

    def test_growth_success(self):
        self.dataset.grow(self.entity_type, asynchronous=False)
        self.assert_initial_grow_success(dataset_versions=1, collections=1, documents=20)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=20)

    def test_growth_limit(self):
        # This test sets the limit to 3.
        # However the batch_size is 5 and therefor we expect to grow 5 Documents.
        self.dataset.grow(self.entity_type, asynchronous=False, limit=3)
        self.assert_initial_grow_success(dataset_versions=1, collections=1, documents=5)
        self.assert_dataset_output(self.dataset, dataset_versions=1, collections=1, documents=5)

    def test_seeding_error(self):
        self.dataset.grow("does_not_exist", asynchronous=False)
        self.assert_initial_grow_success(dataset_versions=1, collections=1, documents=0)
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


class TestContinuationDatasetReviseStrategy(test_cases.BaseDatasetTestCase):

    dataset_model = Dataset
    signature = "setting1=const&test"
    entity_type = "paper"

    def test_growth_success(self):
        self.skipTest("not implemented")

    def test_growth_limit(self):
        self.skipTest("not implemented")

    def test_seeding_error(self):
        self.skipTest("not implemented")

    def test_growth_retry(self):
        self.skipTest("not implemented")

    def test_growth_reset(self):
        self.skipTest("not implemented")
